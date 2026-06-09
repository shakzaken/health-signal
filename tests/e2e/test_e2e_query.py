"""
E2E tests — Non-streaming query endpoint (/query)

Tests that the AI agent answers questions correctly, enforces auth,
and validates input.
"""

import uuid

import httpx
import pytest

from conftest import AI_AGENT


def test_query_returns_answer(auth_token: str, uploaded_doc_id: str):
    """
    POST /query with a valid token and a question about the uploaded document
    returns 200 with a non-empty answer string.
    """
    resp = httpx.post(
        f"{AI_AGENT}/query",
        json={
            "question": "What health information is in my uploaded documents?",
            "session_id": str(uuid.uuid4()),
            "document_type": None,
        },
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=60.0,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert isinstance(data["answer"], str)
    assert len(data["answer"]) > 20, "Answer is suspiciously short"


def test_query_includes_sources_field(auth_token: str, uploaded_doc_id: str):
    """Response includes a 'sources' list (may be empty if no relevant chunks found)."""
    resp = httpx.post(
        f"{AI_AGENT}/query",
        json={
            "question": "Do I have any lab results?",
            "session_id": str(uuid.uuid4()),
        },
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=60.0,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "sources" in data
    assert isinstance(data["sources"], list)


def test_query_session_continuity(auth_token: str, uploaded_doc_id: str):
    """
    Two questions in the same session: the second question can reference the first.
    This confirms session memory is working end-to-end.
    """
    session_id = str(uuid.uuid4())
    headers = {"Authorization": f"Bearer {auth_token}"}

    # First turn
    resp1 = httpx.post(
        f"{AI_AGENT}/query",
        json={"question": "My name is Test User and I'm tracking my health.", "session_id": session_id},
        headers=headers,
        timeout=60.0,
    )
    assert resp1.status_code == 200

    # Second turn — references the first
    resp2 = httpx.post(
        f"{AI_AGENT}/query",
        json={"question": "What did I just tell you my name was?", "session_id": session_id},
        headers=headers,
        timeout=60.0,
    )
    assert resp2.status_code == 200
    answer = resp2.json()["answer"].lower()
    # The agent should recall "Test User" from the same session
    assert "test user" in answer or "test" in answer


def test_query_without_token():
    """POST /query without a token returns 401."""
    resp = httpx.post(
        f"{AI_AGENT}/query",
        json={"question": "hello", "session_id": str(uuid.uuid4())},
        timeout=10.0,
    )
    assert resp.status_code == 401


def test_query_empty_question(auth_token: str):
    """POST /query with an empty question string returns 422."""
    resp = httpx.post(
        f"{AI_AGENT}/query",
        json={"question": "", "session_id": str(uuid.uuid4())},
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=10.0,
    )
    assert resp.status_code == 422
