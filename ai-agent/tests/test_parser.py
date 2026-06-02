"""Tests for the DocumentParser class."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock

from ingestion.parser import DocumentParser


PDF_PATH = str(Path(__file__).parents[2] / "test-data" / "04efd_myTests.pdf")


def test_is_meaningful_text_with_good_text():
    text = "Patient hemoglobin levels were within normal range. " * 5
    assert DocumentParser.is_meaningful_text(text) is True


def test_is_meaningful_text_too_short():
    assert DocumentParser.is_meaningful_text("short") is False


def test_is_meaningful_text_too_few_words():
    assert DocumentParser.is_meaningful_text("a " * 10 + "b" * 90) is False


def test_is_meaningful_text_low_alpha_ratio():
    # Numbers/symbols dominate — not real prose
    garbage = "1234 5678 9012 3456 7890 " * 20
    assert DocumentParser.is_meaningful_text(garbage) is False


@pytest.mark.asyncio
async def test_parse_real_pdf_extracts_text():
    """Parse the real lab PDF — should return meaningful text."""
    parser = DocumentParser()
    text = await parser.parse(PDF_PATH)
    assert len(text) > 100
    assert DocumentParser.is_meaningful_text(text)


@pytest.mark.asyncio
async def test_parse_real_pdf_contains_expected_values():
    """The real PDF should contain lab values we know are in it."""
    parser = DocumentParser()
    text = await parser.parse(PDF_PATH)
    # These values are visible in the PDF
    assert "CHOLESTEROL" in text.upper() or "cholesterol" in text.lower()


@pytest.mark.asyncio
async def test_parse_text_file(tmp_path):
    """Plain text files should be read directly."""
    txt = tmp_path / "note.txt"
    txt.write_text("Patient reports fatigue and headaches since last week.")
    parser = DocumentParser()
    text = await parser.parse(str(txt))
    assert "fatigue" in text


@pytest.mark.asyncio
async def test_parse_falls_back_to_vision_when_pdf_text_is_garbage(tmp_path, mocker):
    """
    When PyMuPDF returns non-meaningful text, the parser should call
    the vision extractor. We mock the vision extractor so we don't hit the API.
    """
    mock_vision = AsyncMock()
    mock_vision.extract.return_value = "Extracted via OCR: Hemoglobin 14.2 g/dL"

    parser = DocumentParser(vision_extractor=mock_vision)

    # Mock _extract_pdf_text to return garbage
    mocker.patch.object(DocumentParser, "_extract_pdf_text", return_value="!@#$ 1234 !@#$")
    mocker.patch.object(DocumentParser, "_render_pdf_to_images", return_value=[b"fake_image"])

    result = await parser.parse(PDF_PATH)
    mock_vision.extract.assert_called_once()
    assert "Hemoglobin" in result
