"""
E2E tests — Feature 1: Authentication

Tests registration, login, invalid credentials, and protected route enforcement
on both the backend and the AI agent.
"""

import uuid

import httpx
import pytest

from conftest import BACKEND, AI_AGENT


def test_register_new_user():
    """POST /auth/register with fresh credentials returns 201 and a JWT."""
    uid = uuid.uuid4().hex[:8]
    resp = httpx.post(
        f"{BACKEND}/auth/register",
        json={"email": f"new_{uid}@test.hs", "password": "Password123!"},
        timeout=10.0,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    token = data["access_token"]
    # JWT has 3 dot-separated parts
    assert len(token.split(".")) == 3


def test_register_duplicate_email(auth_token: str, test_credentials: dict):
    """Registering with an already-used email returns 409."""
    # auth_token fixture ensures the user has already been registered
    resp = httpx.post(
        f"{BACKEND}/auth/register",
        json=test_credentials,
        timeout=10.0,
    )
    assert resp.status_code == 409


def test_register_invalid_email():
    """Registering with a malformed email returns 422."""
    resp = httpx.post(
        f"{BACKEND}/auth/register",
        json={"email": "not-an-email", "password": "Password123!"},
        timeout=10.0,
    )
    assert resp.status_code == 422


def test_login_correct_credentials(test_credentials: dict):
    """POST /auth/login with correct credentials returns 200 and a JWT."""
    resp = httpx.post(
        f"{BACKEND}/auth/login",
        json=test_credentials,
        timeout=10.0,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert len(data["access_token"].split(".")) == 3


def test_login_wrong_password(test_credentials: dict):
    """Wrong password returns 401 with a generic error (no user enumeration)."""
    resp = httpx.post(
        f"{BACKEND}/auth/login",
        json={"email": test_credentials["email"], "password": "WrongPass999!"},
        timeout=10.0,
    )
    assert resp.status_code == 401
    # Message should NOT reveal whether the email exists
    body = resp.text.lower()
    assert "invalid" in body or "incorrect" in body or "unauthorized" in body


def test_login_unknown_email():
    """Unknown email returns 401 (same as wrong password — no enumeration)."""
    resp = httpx.post(
        f"{BACKEND}/auth/login",
        json={"email": "nobody@nowhere.com", "password": "Whatever1!"},
        timeout=10.0,
    )
    assert resp.status_code == 401


def test_protected_route_no_token():
    """GET /documents without a token returns 401."""
    resp = httpx.get(f"{BACKEND}/documents", timeout=10.0)
    assert resp.status_code == 401


def test_protected_route_with_valid_token(auth_token: str):
    """GET /documents with a valid token returns 200."""
    resp = httpx.get(
        f"{BACKEND}/documents",
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=10.0,
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_protected_route_tampered_token():
    """A tampered JWT is rejected with 401."""
    fake_token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJmYWtlIn0.invalidsig"
    resp = httpx.get(
        f"{BACKEND}/documents",
        headers={"Authorization": f"Bearer {fake_token}"},
        timeout=10.0,
    )
    assert resp.status_code == 401


def test_ai_agent_protected_no_token():
    """AI agent /query endpoint returns 401 without a token."""
    resp = httpx.post(
        f"{AI_AGENT}/query",
        json={"question": "hello", "session_id": str(uuid.uuid4())},
        timeout=10.0,
    )
    assert resp.status_code == 401


def test_ai_agent_accepts_backend_token(auth_token: str):
    """AI agent accepts a token issued by the backend (shared secret)."""
    import uuid
    resp = httpx.post(
        f"{AI_AGENT}/query",
        json={"question": "hello", "session_id": str(uuid.uuid4())},
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=30.0,
    )
    # 200 means the token was accepted (answer content doesn't matter here)
    assert resp.status_code == 200
    assert "answer" in resp.json()
