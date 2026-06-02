"""Tests for the LabExtractor tool."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from tools.lab_extractor import ExtractedLabResult, ExtractedMarker, LabExtractor


def make_mock_llm(result: ExtractedLabResult) -> MagicMock:
    chain = MagicMock()
    chain.ainvoke = AsyncMock(return_value=result)
    llm = MagicMock()
    llm.with_structured_output.return_value = chain
    return llm


@pytest.mark.asyncio
async def test_extract_returns_markers():
    expected = ExtractedLabResult(
        test_date="2024-03-15",
        lab_name="General Hospital",
        markers=[
            ExtractedMarker(name="Hemoglobin", value=14.2, unit="g/dL", reference_low=12.0, reference_high=16.0, status="normal"),
            ExtractedMarker(name="Cholesterol", value=210.0, unit="mg/dL", reference_low=None, reference_high=200.0, status="high"),
        ],
    )
    extractor = LabExtractor(llm=make_mock_llm(expected))
    result = await extractor.extract("some lab text")

    assert len(result.markers) == 2
    assert result.markers[0].name == "Hemoglobin"
    assert result.markers[0].value == 14.2
    assert result.test_date == "2024-03-15"


@pytest.mark.asyncio
async def test_extract_returns_empty_on_failure():
    llm = MagicMock()
    chain = MagicMock()
    chain.ainvoke = AsyncMock(side_effect=Exception("LLM error"))
    llm.with_structured_output.return_value = chain

    extractor = LabExtractor(llm=llm)
    result = await extractor.extract("some text")

    assert result.markers == []
    assert result.test_date is None


@pytest.mark.asyncio
async def test_extract_marker_fields():
    marker = ExtractedMarker(
        name="Glucose",
        value=95.0,
        unit="mg/dL",
        reference_low=70.0,
        reference_high=100.0,
        status="normal",
    )
    expected = ExtractedLabResult(markers=[marker])
    extractor = LabExtractor(llm=make_mock_llm(expected))

    result = await extractor.extract("Glucose: 95 mg/dL (70-100)")
    m = result.markers[0]
    assert m.name == "Glucose"
    assert m.unit == "mg/dL"
    assert m.reference_low == 70.0
    assert m.reference_high == 100.0
    assert m.status == "normal"
