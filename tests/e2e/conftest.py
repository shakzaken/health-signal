"""
Shared fixtures for end-to-end integration tests.

Both services must be running before the suite is executed:
  - Backend:  http://localhost:8000  (or BACKEND_URL env var)
  - AI agent: http://localhost:8001  (or AI_AGENT_URL env var)

Each test session registers a fresh randomly-named user so tests are
fully isolated from any existing data in the database.
"""

import os
import time
import uuid

import httpx
import pytest

BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")
AI_AGENT = os.getenv("AI_AGENT_URL", "http://localhost:8001")

# A tiny text file embedded in the fixture — no external file needed.
SMALL_DOC_CONTENT = b"""Health Note - Test Document

Date: 2024-06-01

Patient is maintaining a balanced diet and regular exercise routine.
Vitamin D supplement started in March. Follow-up blood test scheduled for September.
No new symptoms reported. Energy levels stable.
"""
SMALL_DOC_NAME = "e2e_test_note.txt"


@pytest.fixture(scope="session")
def backend_url() -> str:
    return BACKEND


@pytest.fixture(scope="session")
def ai_agent_url() -> str:
    return AI_AGENT


@pytest.fixture(scope="session")
def test_credentials() -> dict:
    """Generate unique credentials so the session never collides with existing users."""
    uid = uuid.uuid4().hex[:8]
    return {
        "email": f"e2e_{uid}@test.healthsignal",
        "password": "E2eTestPass123!",
    }


@pytest.fixture(scope="session")
def auth_token(test_credentials: dict) -> str:
    """Register a test user and return the JWT."""
    resp = httpx.post(
        f"{BACKEND}/auth/register",
        json=test_credentials,
        timeout=15.0,
    )
    assert resp.status_code == 201, f"Registration failed: {resp.status_code} {resp.text}"
    token = resp.json().get("access_token")
    assert token, "No access_token in registration response"
    return token


@pytest.fixture(scope="session")
def uploaded_doc_id(auth_token: str) -> str:
    """
    Upload a small test document and wait for it to be fully processed.
    Returns the document_id once status == 'completed'.
    """
    resp = httpx.post(
        f"{BACKEND}/documents/upload",
        files={"file": (SMALL_DOC_NAME, SMALL_DOC_CONTENT, "text/plain")},
        data={"source_date": "2024-06-01"},
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=30.0,
    )
    assert resp.status_code == 202, f"Upload failed: {resp.status_code} {resp.text}"
    doc_id = resp.json()["id"]

    # Poll until completed (max 90 seconds)
    deadline = time.time() + 90
    while time.time() < deadline:
        status_resp = httpx.get(
            f"{BACKEND}/documents/{doc_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10.0,
        )
        status_resp.raise_for_status()
        status = status_resp.json().get("processing_status")
        if status == "completed":
            return doc_id
        if status == "failed":
            pytest.fail(f"Document processing failed for doc_id={doc_id}")
        time.sleep(5)

    pytest.fail(f"Timed out waiting for document {doc_id} to complete processing")
