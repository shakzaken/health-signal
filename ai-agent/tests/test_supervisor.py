"""Tests for the Supervisor agent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.supervisor import Supervisor
from rag.query_chain import QueryChain


def make_rag_mock(answer: str = "RAG answer") -> MagicMock:
    rag = MagicMock(spec=QueryChain)
    rag.answer = AsyncMock(return_value={"answer": answer, "sources": []})
    return rag


def make_llm_mock(route: str = "rag", answer: str = "LLM answer") -> MagicMock:
    from agents.supervisor import RouteDecision

    llm = MagicMock()

    classify_chain = MagicMock()
    classify_chain.ainvoke = AsyncMock(return_value=RouteDecision(route=route))
    llm.with_structured_output.return_value = classify_chain

    bound = MagicMock()
    bound.ainvoke = AsyncMock(return_value=MagicMock(content=answer, tool_calls=[]))
    llm.bind_tools.return_value = bound

    llm.ainvoke = AsyncMock(return_value=MagicMock(content=answer))
    return llm


def patch_httpx():
    """Patch httpx.AsyncClient for agents that call the backend."""
    mock_client = AsyncMock()
    mock_client.get.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value=[]),
        raise_for_status=MagicMock(),
    )
    mock_client.post.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value={"answer": "search result", "sources": []}),
        raise_for_status=MagicMock(),
    )
    return mock_client


@pytest.mark.asyncio
async def test_supervisor_routes_lab_question_to_lab_agent():
    llm = make_llm_mock(route="lab_analysis", answer="Your hemoglobin is normal.")
    rag = make_rag_mock()

    with patch("agents.lab_analysis.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value = patch_httpx()
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
async def test_supervisor_routes_pattern_question_to_pattern_agent():
    llm = make_llm_mock(route="pattern_detection", answer="Fatigue correlates with low Vitamin D.")
    rag = make_rag_mock()

    with patch("agents.pattern_detection.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value = patch_httpx()
        supervisor = Supervisor(llm=llm, rag_chain=rag, backend_url="http://localhost:8000")
        result = await supervisor.run("Did my fatigue correlate with low Vitamin D?")

    assert "answer" in result
    rag.answer.assert_not_called()


@pytest.mark.asyncio
async def test_supervisor_routes_timeline_question_to_timeline_agent():
    llm = make_llm_mock(route="timeline", answer="In the last 6 months you had 2 blood tests.")
    rag = make_rag_mock()

    with patch("agents.timeline.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value = patch_httpx()
        supervisor = Supervisor(llm=llm, rag_chain=rag, backend_url="http://localhost:8000")
        result = await supervisor.run("What happened to my health in the last 6 months?")

    assert "answer" in result
    rag.answer.assert_not_called()


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
