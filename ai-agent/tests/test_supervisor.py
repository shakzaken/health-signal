"""Tests for the Supervisor agent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.supervisor import Supervisor
from rag.query_chain import QueryChain


def make_rag_mock(answer: str = "RAG answer") -> MagicMock:
    rag = MagicMock(spec=QueryChain)
    # answer() accepts an optional config kwarg
    rag.answer = AsyncMock(return_value={"answer": answer, "sources": []})
    return rag


def make_llm_mock(route: str = "rag", answer: str = "LLM answer") -> MagicMock:
    from agents.supervisor import RouteDecision

    llm = MagicMock()

    # with_structured_output returns a chain — ainvoke returns a real RouteDecision
    classify_chain = MagicMock()
    classify_chain.ainvoke = AsyncMock(return_value=RouteDecision(route=route))
    llm.with_structured_output.return_value = classify_chain

    # bind_tools returns a runnable — ainvoke returns a response with no tool_calls (final answer)
    bound = MagicMock()
    bound.ainvoke = AsyncMock(return_value=MagicMock(content=answer, tool_calls=[]))
    llm.bind_tools.return_value = bound

    # ainvoke used directly (e.g. in RAG chain)
    llm.ainvoke = AsyncMock(return_value=MagicMock(content=answer))
    return llm


@pytest.mark.asyncio
async def test_supervisor_routes_lab_question_to_lab_agent():
    llm = make_llm_mock(route="lab_analysis", answer="Your hemoglobin is normal.")
    rag = make_rag_mock()

    with patch("agents.lab_analysis.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value=[]),
            raise_for_status=MagicMock(),
        )

        supervisor = Supervisor(llm=llm, rag_chain=rag, backend_url="http://localhost:8000")
        result = await supervisor.run("What is my hemoglobin?")

    assert "answer" in result
    rag.answer.assert_not_called()


@pytest.mark.asyncio
async def test_supervisor_routes_general_question_to_rag():
    llm = make_llm_mock(route="rag")
    rag = make_rag_mock(answer="RAG answer about diet")

    supervisor = Supervisor(llm=llm, rag_chain=rag, backend_url="http://localhost:8000")
    result = await supervisor.run("What does my doctor say about diet?")

    assert result["answer"] == "RAG answer about diet"
    rag.answer.assert_called_once()


@pytest.mark.asyncio
async def test_supervisor_falls_back_to_rag_on_classify_error():
    llm = MagicMock()
    classify_chain = MagicMock()
    classify_chain.ainvoke = AsyncMock(side_effect=Exception("classify failed"))
    llm.with_structured_output.return_value = classify_chain
    llm.ainvoke = AsyncMock(return_value=MagicMock(content="answer"))

    rag = make_rag_mock(answer="fallback RAG answer")
    supervisor = Supervisor(llm=llm, rag_chain=rag, backend_url="http://localhost:8000")
    result = await supervisor.run("Some question")

    assert result["answer"] == "fallback RAG answer"


@pytest.mark.asyncio
async def test_supervisor_returns_answer_and_sources():
    llm = make_llm_mock(route="rag")
    rag = MagicMock(spec=QueryChain)
    rag.answer = AsyncMock(return_value={
        "answer": "Cholesterol is 210",
        "sources": [{"text": "chunk", "document_id": "1", "document_type": "lab_report",
                     "source_date": None, "filename": "labs.pdf", "score": 0.9}],
    })

    supervisor = Supervisor(llm=llm, rag_chain=rag, backend_url="http://localhost:8000")
    result = await supervisor.run("What is my cholesterol?")

    assert result["answer"] == "Cholesterol is 210"
    assert len(result["sources"]) == 1
