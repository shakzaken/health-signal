"""
Tests for the QueryChain class.

The LLM and Retriever are mocked so tests are fast and don't cost API calls.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

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
async def test_answer_calls_retriever_with_question(chain, mock_retriever):
    await chain.answer("What is my cholesterol?")
    mock_retriever.retrieve.assert_called_once()
    call_args = mock_retriever.retrieve.call_args
    assert "cholesterol" in call_args.args[0].lower()


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
    retriever = MagicMock(spec=Retriever)
    retriever.retrieve.return_value = []  # nothing in Qdrant
    chain = QueryChain(retriever=retriever, llm=mock_llm)

    result = await chain.answer("What are my results?")
    assert result["sources"] == []
    assert "couldn't find" in result["answer"].lower()
    mock_llm.ainvoke.assert_not_called()  # LLM should NOT be called when no context


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
    # The human message should contain the chunk text as context
    human_message = next(m for m in messages if m.__class__.__name__ == "HumanMessage")
    assert "Hemoglobin" in human_message.content
