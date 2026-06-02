"""
Shared pytest fixtures for the ai-agent test suite.
"""

import pytest
from fastapi.testclient import TestClient

from ingestion.chunker import Chunker
from ingestion.embedder import Embedder


@pytest.fixture(scope="session")
def chunker() -> Chunker:
    return Chunker()


@pytest.fixture(scope="session")
def embedder() -> Embedder:
    """Real embedder — model is loaded once for the whole test session."""
    return Embedder()


@pytest.fixture
def sample_health_text() -> str:
    return (
        "Patient: John Doe\n"
        "Date: 2024-01-15\n\n"
        "Lab Results:\n"
        "Hemoglobin: 14.2 g/dL (reference: 13.5-17.5)\n"
        "White Blood Cells: 7.2 K/uL (reference: 4.5-11.0)\n"
        "Platelets: 220 K/uL (reference: 150-400)\n"
        "Glucose: 95 mg/dL (reference: 70-100)\n"
        "Cholesterol Total: 195 mg/dL (reference: <200)\n\n"
        "All values within normal range. Follow up in 12 months."
    )
