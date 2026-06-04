from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables.config import RunnableConfig
from pydantic import BaseModel

EXTRACTION_PROMPT = """You are a medical data extraction assistant.

Extract all symptom entries from the text below. For each symptom extract:
- symptom_name: the name of the symptom in English (translate if needed)
- severity: one of "mild", "moderate", "severe" — infer from context if not stated explicitly, or leave null
- occurred_at: the date the symptom occurred in ISO format (YYYY-MM-DD). If only a month/year is given, use the first day of that month. If no date is found, leave null.
- notes: any additional context about the symptom (triggers, duration, related events), or null

Extract every distinct symptom occurrence. If the same symptom appears on multiple dates, create a separate entry for each.
Skip entries where you cannot extract at least a symptom name.
If the document is in Hebrew, translate symptom names to English.
"""


class ExtractedSymptomEntry(BaseModel):
    symptom_name: str
    severity: Optional[str] = None
    occurred_at: Optional[str] = None
    notes: Optional[str] = None


class ExtractedSymptoms(BaseModel):
    entries: list[ExtractedSymptomEntry] = []


class SymptomExtractor:
    """
    Extracts structured symptom entries from raw document text using LLM structured output.
    Works with symptom notes, journals, and doctor summaries.
    """

    def __init__(self, llm: BaseChatModel) -> None:
        self._chain = llm.with_structured_output(ExtractedSymptoms)

    async def extract(
        self,
        raw_text: str,
        config: RunnableConfig | None = None,
    ) -> ExtractedSymptoms:
        """
        Parse raw text and return structured symptom entries.
        Returns an empty result if extraction fails.
        """
        try:
            result = await self._chain.ainvoke(
                f"{EXTRACTION_PROMPT}\n\nDocument text:\n{raw_text}",
                config=config,
            )
            return result
        except Exception:
            return ExtractedSymptoms()
