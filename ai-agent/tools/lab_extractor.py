from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel

EXTRACTION_PROMPT = """You are a medical data extraction assistant.

Extract all lab test markers from the text below. For each marker extract:
- name: the marker name in English (translate if needed)
- value: the numeric value as a float
- unit: the unit of measurement
- reference_low: the lower bound of the normal range (if present)
- reference_high: the upper bound of the normal range (if present)
- status: one of "normal", "low", "high", "borderline_low", "borderline_high" — infer from value vs reference range if not stated explicitly

Also extract:
- test_date: the date of the test in ISO format (YYYY-MM-DD) if present, else null
- lab_name: the name of the laboratory if present, else null

Return only markers that have a clear numeric value. Skip headers, notes, and non-numeric entries.
If the document is in Hebrew, translate marker names to English.
"""


class ExtractedMarker(BaseModel):
    name: str
    value: float
    unit: str
    reference_low: Optional[float] = None
    reference_high: Optional[float] = None
    status: Optional[str] = None


class ExtractedLabResult(BaseModel):
    test_date: Optional[str] = None
    lab_name: Optional[str] = None
    markers: list[ExtractedMarker] = []


class LabExtractor:
    """
    Extracts structured lab markers from raw document text using LLM structured output.
    Works with both Hebrew and English documents — marker names are always returned in English.
    """

    def __init__(self, llm: BaseChatModel) -> None:
        self._chain = llm.with_structured_output(ExtractedLabResult)

    async def extract(self, raw_text: str) -> ExtractedLabResult:
        """
        Parse raw text from a lab document and return structured markers.
        Returns an empty result if extraction fails.
        """
        try:
            result = await self._chain.ainvoke(
                f"{EXTRACTION_PROMPT}\n\nDocument text:\n{raw_text}"
            )
            return result
        except Exception:
            return ExtractedLabResult()
