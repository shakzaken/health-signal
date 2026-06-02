"""
Tests for the POST /query endpoint.
The QueryChain is mocked via FastAPI dependency override.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from api.deps import get_query_chain
from rag.query_chain import QueryChain
from main import app


def make_chain_mock(answer: str = "Your results look normal.", sources: int = 3) -> MagicMock:
    chain = MagicMock(spec=QueryChain)
    chain.answer = AsyncMock(return_value={
        "answer": answer,
        "sources": [
            {
                "text": f"Lab value chunk {i}",
                "document_id": f"doc-{i}",
                "document_type": "lab_report",
                "source_date": "2024-01-01",
                "filename": "labs.pdf",
                "chunk_index": i,
                "score": 0.9 - i * 0.05,
            }
            for i in range(sources)
        ],
    })
    return chain


@pytest.fixture
def client_with_mock_chain():
    mock = make_chain_mock()
    app.dependency_overrides[get_query_chain] = lambda: mock
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c, mock
    app.dependency_overrides.clear()


def test_query_returns_200_with_answer_and_sources(client_with_mock_chain):
    client, _ = client_with_mock_chain
    resp = client.post("/query", json={"question": "What are my lab results?"})
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "sources" in data
    assert data["answer"] == "Your results look normal."
    assert len(data["sources"]) == 3


def test_query_calls_chain_with_question(client_with_mock_chain):
    client, mock_chain = client_with_mock_chain
    client.post("/query", json={"question": "What is my cholesterol?"})
    mock_chain.answer.assert_called_once()
    assert "cholesterol" in mock_chain.answer.call_args.kwargs["question"].lower()


def test_query_passes_document_type_filter(client_with_mock_chain):
    client, mock_chain = client_with_mock_chain
    client.post("/query", json={
        "question": "Any lab results?",
        "document_type": "blood_test",
    })
    kwargs = mock_chain.answer.call_args.kwargs
    assert kwargs.get("document_type") == "blood_test"


def test_query_document_type_is_optional(client_with_mock_chain):
    client, _ = client_with_mock_chain
    resp = client.post("/query", json={"question": "Any results?"})
    assert resp.status_code == 200


def test_query_validates_missing_question():
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post("/query", json={})
    assert resp.status_code == 422


def test_query_source_schema_matches_expected_fields(client_with_mock_chain):
    client, _ = client_with_mock_chain
    resp = client.post("/query", json={"question": "Results?"})
    source = resp.json()["sources"][0]
    assert "text" in source
    assert "document_id" in source
    assert "score" in source
    assert "filename" in source
