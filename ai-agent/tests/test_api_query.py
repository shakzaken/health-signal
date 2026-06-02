"""
Tests for the POST /query endpoint.
The Supervisor is mocked via FastAPI dependency override.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from agents.supervisor import Supervisor
from api.deps import get_supervisor
from main import app


def make_supervisor_mock(answer: str = "Your results look normal.", sources: int = 3) -> MagicMock:
    supervisor = MagicMock(spec=Supervisor)
    supervisor.run = AsyncMock(return_value={
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
    return supervisor


@pytest.fixture
def client_with_mock_supervisor():
    mock = make_supervisor_mock()
    app.dependency_overrides[get_supervisor] = lambda: mock
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c, mock
    app.dependency_overrides.clear()


def test_query_returns_200_with_answer_and_sources(client_with_mock_supervisor):
    client, _ = client_with_mock_supervisor
    resp = client.post("/query", json={"question": "What are my lab results?"})
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "sources" in data
    assert data["answer"] == "Your results look normal."
    assert len(data["sources"]) == 3


def test_query_calls_supervisor_with_question(client_with_mock_supervisor):
    client, mock_supervisor = client_with_mock_supervisor
    client.post("/query", json={"question": "What is my cholesterol?"})
    mock_supervisor.run.assert_called_once()
    assert "cholesterol" in mock_supervisor.run.call_args.kwargs["question"].lower()


def test_query_passes_document_type_filter(client_with_mock_supervisor):
    client, mock_supervisor = client_with_mock_supervisor
    client.post("/query", json={
        "question": "Any lab results?",
        "document_type": "blood_test",
    })
    kwargs = mock_supervisor.run.call_args.kwargs
    assert kwargs.get("document_type") == "blood_test"


def test_query_document_type_is_optional(client_with_mock_supervisor):
    client, _ = client_with_mock_supervisor
    resp = client.post("/query", json={"question": "Any results?"})
    assert resp.status_code == 200


def test_query_validates_missing_question():
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post("/query", json={})
    assert resp.status_code == 422


def test_query_source_schema_matches_expected_fields(client_with_mock_supervisor):
    client, _ = client_with_mock_supervisor
    resp = client.post("/query", json={"question": "Results?"})
    source = resp.json()["sources"][0]
    assert "text" in source
    assert "document_id" in source
    assert "score" in source
    assert "filename" in source
