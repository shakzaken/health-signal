"""
Tests for the POST /ingest endpoint.
The IngestionPipeline is mocked via FastAPI dependency override.
"""

from unittest.mock import AsyncMock, MagicMock
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.deps import get_ingestion_pipeline
from ingestion.pipeline import IngestionPipeline
from main import app

PDF_PATH = str(Path(__file__).parents[2] / "test-data" / "04efd_myTests.pdf")


def make_pipeline_mock(success: bool = True, chunks: int = 5) -> MagicMock:
    pipeline = MagicMock(spec=IngestionPipeline)
    pipeline.run = AsyncMock(return_value={
        "success": success,
        "document_id": "doc-test",
        "chunks_stored": chunks if success else 0,
        "error": None if success else "Something went wrong",
    })
    return pipeline


@pytest.fixture
def client_with_mock_pipeline():
    mock = make_pipeline_mock(success=True, chunks=4)
    app.dependency_overrides[get_ingestion_pipeline] = lambda: mock
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c, mock
    app.dependency_overrides.clear()


def test_ingest_returns_200_on_success(client_with_mock_pipeline):
    client, _ = client_with_mock_pipeline
    resp = client.post("/api/ingest", json={
        "document_id": "doc-abc",
        "file_path": PDF_PATH,
        "document_type": "lab_report",
        "filename": "labs.pdf",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["chunks_stored"] == 4


def test_ingest_calls_pipeline_with_correct_args(client_with_mock_pipeline):
    client, mock_pipeline = client_with_mock_pipeline
    client.post("/api/ingest", json={
        "document_id": "doc-xyz",
        "file_path": "/some/path.pdf",
        "document_type": "blood_test",
        "source_date": "2024-06-01",
        "filename": "blood.pdf",
    })
    mock_pipeline.run.assert_called_once()
    kwargs = mock_pipeline.run.call_args.kwargs
    assert kwargs["document_id"] == "doc-xyz"
    assert kwargs["document_type"] == "blood_test"
    assert kwargs["source_date"] == "2024-06-01"


def test_ingest_returns_error_field_on_failure():
    mock = make_pipeline_mock(success=False)
    app.dependency_overrides[get_ingestion_pipeline] = lambda: mock
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post("/api/ingest", json={
            "document_id": "doc-fail",
            "file_path": "/bad/path.pdf",
            "document_type": "lab_report",
            "filename": "bad.pdf",
        })
    app.dependency_overrides.clear()
    assert resp.status_code == 200  # pipeline errors are returned, not raised
    data = resp.json()
    assert data["success"] is False
    assert data["error"] == "Something went wrong"


def test_ingest_uses_filename_from_path_when_not_provided():
    mock = make_pipeline_mock()
    app.dependency_overrides[get_ingestion_pipeline] = lambda: mock
    with TestClient(app, raise_server_exceptions=False) as client:
        client.post("/api/ingest", json={
            "document_id": "doc-noname",
            "file_path": "/uploads/myfile.pdf",
            "document_type": "lab_report",
        })
    app.dependency_overrides.clear()
    kwargs = mock.run.call_args.kwargs
    assert kwargs["filename"] == "myfile.pdf"


def test_ingest_validates_required_fields():
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post("/api/ingest", json={"document_id": "only-id"})
    assert resp.status_code == 422
