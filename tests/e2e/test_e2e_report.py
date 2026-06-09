"""
E2E tests — Doctor report generation (/report/generate)

Tests that the report endpoint returns a structured non-empty report,
enforces auth, and handles different period lengths.
"""

import httpx
import pytest

from conftest import AI_AGENT


def test_report_generates_successfully(auth_token: str, uploaded_doc_id: str):
    """
    POST /report/generate returns 200 with a non-empty 'report' string.
    Uses a 365-day window so the test document (dated 2024-06-01) is in scope.
    """
    resp = httpx.post(
        f"{AI_AGENT}/report/generate",
        json={"period_days": 365},
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=90.0,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "report" in data
    report = data["report"]
    assert isinstance(report, str)
    assert len(report) > 100, "Report is suspiciously short"


def test_report_contains_expected_sections(auth_token: str, uploaded_doc_id: str):
    """
    The report should contain at least some of the standard section headers
    the doctor report agent is prompted to produce.
    """
    resp = httpx.post(
        f"{AI_AGENT}/report/generate",
        json={"period_days": 365},
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=90.0,
    )
    assert resp.status_code == 200
    report = resp.json()["report"].upper()

    # At least one of the expected section markers should appear
    section_markers = ["LAB", "SYMPTOM", "SUPPLEMENT", "QUESTION", "DOCTOR"]
    found = [m for m in section_markers if m in report]
    assert len(found) >= 2, f"Report missing expected sections. Found: {found}"


def test_report_default_period(auth_token: str, uploaded_doc_id: str):
    """POST /report/generate without period_days uses the default and still succeeds."""
    resp = httpx.post(
        f"{AI_AGENT}/report/generate",
        json={},
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=90.0,
    )
    assert resp.status_code == 200
    assert len(resp.json()["report"]) > 50


def test_report_without_token():
    """POST /report/generate without a token returns 401."""
    resp = httpx.post(
        f"{AI_AGENT}/report/generate",
        json={"period_days": 90},
        timeout=10.0,
    )
    assert resp.status_code == 401
