"""
Tests for the backend document API endpoints.

The ai-agent HTTP call (ingestion trigger) is mocked via pytest-mock
so tests don't depend on the ai-agent being running.
"""

import io
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

PDF_PATH = Path(__file__).parents[2] / "test-data" / "04efd_myTests.pdf"

# ── Helpers ──────────────────────────────────────────────────────────────────

def upload_pdf(client, filename: str = "labs.pdf", document_type: str = "lab_report"):
    """Helper to POST a file to /documents/upload."""
    content = PDF_PATH.read_bytes() if PDF_PATH.exists() else b"%PDF-fake content for testing"
    return client.post(
        "/documents/upload",
        files={"file": (filename, io.BytesIO(content), "application/pdf")},
        data={"document_type": document_type},
    )


def mock_ingestion_success(mocker):
    """Patch httpx so the ai-agent call always returns success."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = '{"success":true,"document_id":"x","chunks_stored":4,"error":null}'
    # httpx Response.json() is synchronous — use MagicMock, not AsyncMock
    mock_response.json = MagicMock(return_value={
        "success": True, "document_id": "x", "chunks_stored": 4, "error": None
    })

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_response)

    return mocker.patch("services.document_service.httpx.AsyncClient", return_value=mock_client)


# ── Health ────────────────────────────────────────────────────────────────────

def test_health_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ── Upload ────────────────────────────────────────────────────────────────────

def test_upload_returns_document_with_id(client, mocker):
    mock_ingestion_success(mocker)
    resp = upload_pdf(client)
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["filename"] == "labs.pdf"
    assert data["document_type"] == "lab_report"


def test_upload_status_is_completed_after_successful_ingestion(client, mocker):
    mock_ingestion_success(mocker)
    resp = upload_pdf(client)
    assert resp.json()["processing_status"] == "completed"


def test_upload_status_is_failed_when_ingestion_fails(client, mocker):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = '{"success":false,"chunks_stored":0,"error":"parse error"}'
    mock_response.json = MagicMock(return_value={
        "success": False, "chunks_stored": 0, "error": "parse error"
    })
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_response)
    mocker.patch("services.document_service.httpx.AsyncClient", return_value=mock_client)

    resp = upload_pdf(client)
    assert resp.json()["processing_status"] == "failed"


def test_upload_requires_document_type(client):
    content = b"%PDF-test"
    resp = client.post(
        "/documents/upload",
        files={"file": ("test.pdf", io.BytesIO(content), "application/pdf")},
    )
    assert resp.status_code == 422


def test_upload_accepts_optional_source_date(client, mocker):
    mock_ingestion_success(mocker)
    content = b"%PDF-test"
    resp = client.post(
        "/documents/upload",
        files={"file": ("test.pdf", io.BytesIO(content), "application/pdf")},
        data={"document_type": "lab_report", "source_date": "2024-06-01"},
    )
    assert resp.status_code == 200
    assert resp.json()["source_date"] == "2024-06-01"


# ── Get document by ID ────────────────────────────────────────────────────────

def test_get_document_by_id_returns_document(client, mocker):
    mock_ingestion_success(mocker)
    upload_resp = upload_pdf(client)
    doc_id = upload_resp.json()["id"]

    resp = client.get(f"/documents/{doc_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == doc_id


def test_get_document_by_id_returns_404_for_unknown_id(client):
    fake_id = str(uuid.uuid4())
    resp = client.get(f"/documents/{fake_id}")
    assert resp.status_code == 404


def test_get_document_returns_processing_status(client, mocker):
    mock_ingestion_success(mocker)
    doc_id = upload_pdf(client).json()["id"]
    resp = client.get(f"/documents/{doc_id}")
    assert resp.json()["processing_status"] in ("pending", "processing", "completed", "failed")


# ── List documents ────────────────────────────────────────────────────────────

def test_list_documents_returns_empty_list_initially(client):
    resp = client.get("/documents")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_documents_returns_uploaded_documents(client, mocker):
    mock_ingestion_success(mocker)
    upload_pdf(client, filename="a.pdf")
    upload_pdf(client, filename="b.pdf")

    resp = client.get("/documents")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_list_documents_newest_first(client, mocker):
    mock_ingestion_success(mocker)
    upload_pdf(client, filename="first.pdf")
    upload_pdf(client, filename="second.pdf")

    docs = client.get("/documents").json()
    assert docs[0]["filename"] == "second.pdf"


# ── Other endpoints ───────────────────────────────────────────────────────────

def test_list_lab_results_returns_empty_list(client):
    resp = client.get("/lab-results")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_timeline_returns_empty_list(client):
    resp = client.get("/timeline")
    assert resp.status_code == 200
    assert resp.json() == []
