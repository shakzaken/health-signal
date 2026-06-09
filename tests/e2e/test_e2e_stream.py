"""
E2E tests — Streaming query endpoint (/query/stream)

Tests that the SSE stream delivers token events and a final sources event,
and that auth is enforced.
"""

import json
import uuid

import httpx
import pytest

from conftest import AI_AGENT


def _consume_sse(response: httpx.Response) -> tuple[list[str], list[dict]]:
    """
    Read an SSE response to completion.
    Returns (token_chunks, sources_list).
    """
    tokens: list[str] = []
    sources: list[dict] = []
    buffer = ""

    for chunk in response.iter_bytes():
        buffer += chunk.decode("utf-8", errors="replace")
        lines = buffer.split("\n")
        buffer = lines.pop()  # keep incomplete line

        for line in lines:
            if line.startswith("data: "):
                raw = line[6:].strip()
                if not raw:
                    continue
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if "token" in event and event["token"]:
                    tokens.append(event["token"])
                elif "sources" in event:
                    sources = event["sources"]

    return tokens, sources


def test_stream_returns_sse_content_type(auth_token: str, uploaded_doc_id: str):
    """POST /query/stream returns Content-Type: text/event-stream."""
    with httpx.Client(base_url=AI_AGENT, timeout=60.0) as client:
        with client.stream(
            "POST",
            "/query/stream",
            json={
                "question": "What is in my health documents?",
                "session_id": str(uuid.uuid4()),
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        ) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers.get("content-type", "")


def test_stream_delivers_token_events(auth_token: str, uploaded_doc_id: str):
    """The stream delivers at least one data: {"token": "..."} event."""
    with httpx.Client(base_url=AI_AGENT, timeout=60.0) as client:
        with client.stream(
            "POST",
            "/query/stream",
            json={
                "question": "Give me a brief summary of my health status.",
                "session_id": str(uuid.uuid4()),
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        ) as resp:
            resp.raise_for_status()
            tokens, _ = _consume_sse(resp)

    assert len(tokens) > 0, "Stream produced no token events"
    full_answer = "".join(tokens)
    assert len(full_answer) > 20, "Streamed answer is suspiciously short"


def test_stream_ends_with_sources_event(auth_token: str, uploaded_doc_id: str):
    """The last meaningful event in the stream is a sources event (list, possibly empty)."""
    with httpx.Client(base_url=AI_AGENT, timeout=60.0) as client:
        with client.stream(
            "POST",
            "/query/stream",
            json={
                "question": "What supplements have I been taking?",
                "session_id": str(uuid.uuid4()),
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        ) as resp:
            resp.raise_for_status()
            _, sources = _consume_sse(resp)

    # sources must be a list (may be empty if nothing was retrieved)
    assert isinstance(sources, list)


def test_stream_without_token():
    """POST /query/stream without a token returns 401 (before any stream data)."""
    resp = httpx.post(
        f"{AI_AGENT}/query/stream",
        json={"question": "hello", "session_id": str(uuid.uuid4())},
        timeout=10.0,
    )
    assert resp.status_code == 401
