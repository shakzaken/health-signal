"""
E2E tests — Document upload

Tests upload, duplicate detection, polling for completion, and document listing.
"""

import time

import httpx
import pytest

from conftest import BACKEND, SMALL_DOC_CONTENT, SMALL_DOC_NAME


def test_upload_document(auth_token: str):
    """Uploading a new document returns 202 with a document id and pending/processing status."""
    # Use a slightly different content so it's not flagged as duplicate of the session fixture's doc
    content = SMALL_DOC_CONTENT + b"\n# unique upload test"
    resp = httpx.post(
        f"{BACKEND}/documents/upload",
        files={"file": ("upload_test.txt", content, "text/plain")},
        data={"source_date": "2024-03-01"},
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=30.0,
    )
    assert resp.status_code == 202
    data = resp.json()
    assert "id" in data
    assert data.get("processing_status") in ("pending", "processing", "completed")


def test_upload_without_token():
    """Uploading without a token returns 401."""
    resp = httpx.post(
        f"{BACKEND}/documents/upload",
        files={"file": (SMALL_DOC_NAME, SMALL_DOC_CONTENT, "text/plain")},
        timeout=10.0,
    )
    assert resp.status_code == 401


def test_document_reaches_completed_status(auth_token: str):
    """A successfully uploaded document eventually reaches 'completed' status."""
    content = SMALL_DOC_CONTENT + b"\n# completion poll test"
    resp = httpx.post(
        f"{BACKEND}/documents/upload",
        files={"file": ("poll_test.txt", content, "text/plain")},
        data={"source_date": "2024-04-01"},
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=30.0,
    )
    assert resp.status_code == 202
    doc_id = resp.json()["id"]

    # Poll for up to 90 seconds
    deadline = time.time() + 90
    final_status = None
    while time.time() < deadline:
        status_resp = httpx.get(
            f"{BACKEND}/documents/{doc_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10.0,
        )
        status_resp.raise_for_status()
        final_status = status_resp.json().get("processing_status")
        if final_status in ("completed", "failed"):
            break
        time.sleep(5)

    assert final_status == "completed", f"Document did not complete — final status: {final_status}"


def test_duplicate_document_rejected(auth_token: str, uploaded_doc_id: str):
    """
    Uploading the exact same file content a second time returns 409
    with an existing_document_id in the response body.
    """
    resp = httpx.post(
        f"{BACKEND}/documents/upload",
        files={"file": (SMALL_DOC_NAME, SMALL_DOC_CONTENT, "text/plain")},
        data={"source_date": "2024-06-01"},
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=30.0,
    )
    assert resp.status_code == 409
    data = resp.json()
    # The backend wraps the error body under "detail"
    detail = data.get("detail", data)
    assert "existing_document_id" in detail
    assert detail["existing_document_id"] == uploaded_doc_id


def test_documents_list_contains_upload(auth_token: str, uploaded_doc_id: str):
    """GET /documents returns a list that includes the session's uploaded document."""
    resp = httpx.get(
        f"{BACKEND}/documents",
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=10.0,
    )
    assert resp.status_code == 200
    docs = resp.json()
    assert isinstance(docs, list)
    ids = [d["id"] for d in docs]
    assert uploaded_doc_id in ids


def test_documents_list_without_token():
    """GET /documents without a token returns 401."""
    resp = httpx.get(f"{BACKEND}/documents", timeout=10.0)
    assert resp.status_code == 401
