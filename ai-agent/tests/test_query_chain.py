"""
Tests for the QueryChain class.

The LLM and Retriever are mocked so tests are fast and don't cost API calls.

Language-detection behaviour:
  - English queries  → single retrieval (no translation LLM call)
  - Non-English queries → dual retrieval: primary (original) + secondary (English translation)
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from rag.query_chain import QueryChain
from rag.retriever import Retriever


def make_mock_chunks(n: int = 2) -> list[dict]:
    return [
        {
            "text": f"Hemoglobin: 14.{i} g/dL — within normal range.",
            "document_id": f"doc-{i}",
            "document_type": "lab_report",
            "source_date": "2024-01-15",
            "filename": "labs.pdf",
            "chunk_index": i,
            "score": 0.9 - i * 0.1,
        }
        for i in range(n)
    ]


@pytest.fixture
def mock_retriever() -> MagicMock:
    retriever = MagicMock(spec=Retriever)
    retriever.retrieve.return_value = make_mock_chunks()
    return retriever


@pytest.fixture
def mock_llm() -> AsyncMock:
    llm = AsyncMock()
    llm.ainvoke.return_value = MagicMock(content="Your hemoglobin is within the normal range.")
    return llm


@pytest.fixture
def chain(mock_retriever, mock_llm) -> QueryChain:
    return QueryChain(retriever=mock_retriever, llm=mock_llm)


@pytest.mark.asyncio
async def test_answer_returns_answer_and_sources(chain):
    result = await chain.answer("What is my hemoglobin level?")
    assert "answer" in result
    assert "sources" in result
    assert isinstance(result["answer"], str)
    assert len(result["sources"]) > 0


@pytest.mark.asyncio
async def test_answer_calls_retriever_with_hebrew_question(mock_retriever, mock_llm):
    """Hebrew query triggers dual retrieval: primary (Hebrew) + secondary (English translation)."""
    english_translation = "What is my hemoglobin level?"
    mock_llm.ainvoke.side_effect = [
        MagicMock(content=english_translation),           # translation call
        MagicMock(content="Your hemoglobin is fine."),    # answer call
    ]
    chain = QueryChain(retriever=mock_retriever, llm=mock_llm)

    await chain.answer("מה רמת ההמוגלובין שלי?")

    # Retriever is called twice: once with the original Hebrew, once with the English translation
    assert mock_retriever.retrieve.call_count == 2
    first_query = mock_retriever.retrieve.call_args_list[0].args[0]
    second_query = mock_retriever.retrieve.call_args_list[1].args[0]
    assert "המוגלובין" in first_query
    assert second_query == english_translation


@pytest.mark.asyncio
async def test_hebrew_question_triggers_dual_retrieval(mock_retriever, mock_llm):
    """Hebrew question → translation to English → secondary retrieval uses the English translation."""
    english_translation = "What is my cholesterol level?"
    mock_llm.ainvoke.side_effect = [
        MagicMock(content=english_translation),                   # translation call
        MagicMock(content="Your cholesterol is within range."),   # answer call
    ]
    chain = QueryChain(retriever=mock_retriever, llm=mock_llm)

    await chain.answer("מה רמת הכולסטרול שלי?")

    assert mock_retriever.retrieve.call_count == 2
    # Second retrieval call uses the English translation
    second_call_query = mock_retriever.retrieve.call_args_list[1].args[0]
    assert second_call_query == english_translation


@pytest.mark.asyncio
async def test_english_question_uses_single_retrieval(mock_retriever, mock_llm):
    """English questions go directly to retrieval — no translation LLM call."""
    mock_llm.ainvoke.return_value = MagicMock(content="Here are your results.")
    chain = QueryChain(retriever=mock_retriever, llm=mock_llm)

    await chain.answer("What are my lab results?")

    # Only one LLM call — the final answer; no translation call
    assert mock_llm.ainvoke.call_count == 1
    # Retriever called exactly once with the original English question
    assert mock_retriever.retrieve.call_count == 1
    retrieval_query = mock_retriever.retrieve.call_args.args[0]
    assert "lab results" in retrieval_query.lower()


@pytest.mark.asyncio
async def test_answer_passes_document_type_filter_to_retriever(chain, mock_retriever):
    await chain.answer("What are my lab results?", document_type="blood_test")
    call_kwargs = mock_retriever.retrieve.call_args.kwargs
    assert call_kwargs.get("document_type") == "blood_test"


@pytest.mark.asyncio
async def test_answer_passes_user_id_to_retriever(chain, mock_retriever):
    await chain.answer("Any results?", user_id="user-42")
    call_kwargs = mock_retriever.retrieve.call_args.kwargs
    assert call_kwargs.get("user_id") == "user-42"


@pytest.mark.asyncio
async def test_answer_returns_no_data_message_when_no_chunks(mock_llm):
    """English question with empty retriever → no LLM call, returns the no-data message."""
    retriever = MagicMock(spec=Retriever)
    retriever.retrieve.return_value = []  # nothing in Qdrant
    chain = QueryChain(retriever=retriever, llm=mock_llm)

    result = await chain.answer("What are my results?")
    assert result["sources"] == []
    assert "couldn't find" in result["answer"].lower()
    # English query → no translation call; no chunks → no answer call either
    assert mock_llm.ainvoke.call_count == 0


@pytest.mark.asyncio
async def test_answer_sources_match_retrieved_chunks(chain):
    result = await chain.answer("Any health data?")
    assert len(result["sources"]) == 2
    assert result["sources"][0]["document_type"] == "lab_report"


@pytest.mark.asyncio
async def test_answer_llm_receives_context_from_chunks(chain, mock_llm):
    await chain.answer("Summarize my results.")
    llm_call = mock_llm.ainvoke.call_args
    messages = llm_call.args[0]
    # Context is injected as a SystemMessage, not in the HumanMessage
    system_messages = [m for m in messages if isinstance(m, SystemMessage)]
    context_message = next(
        (m for m in system_messages if "Hemoglobin" in m.content), None
    )
    assert context_message is not None, "Expected chunk context in a SystemMessage"
