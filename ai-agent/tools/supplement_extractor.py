from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables.config import RunnableConfig
from pydantic import BaseModel

EXTRACTION_PROMPT = """You are a medical data extraction assistant.

Extract all supplement entries from the text below. For each supplement extract:
- name: the supplement name in English (translate if needed)
- dosage: the dosage amount and unit (e.g. "1000 mg", "2000 IU", "1 capsule")
- frequency: how often taken (e.g. "once daily", "twice daily", "weekly")
- started_at: the date the supplement was started in ISO format (YYYY-MM-DD), or null if unknown
- stopped_at: the date the supplement was stopped in ISO format (YYYY-MM-DD), or null if still active
- notes: any additional notes (reason for taking, side effects, brand), or null

Extract every distinct supplement. If the document lists multiple supplements, create a separate entry for each.
Skip entries where you cannot extract at least a name and dosage.
If the document is in Hebrew, translate supplement names to English.
"""


class ExtractedSupplementEntry(BaseModel):
    name: str
    dosage: str
    frequency: str
    started_at: Optional[str] = None
    stopped_at: Optional[str] = None
    notes: Optional[str] = None


class ExtractedSupplements(BaseModel):
    entries: list[ExtractedSupplementEntry] = []


class SupplementExtractor:
    """
    Extracts structured supplement entries from raw document text using LLM structured output.
    Works with supplement lists, doctor notes, and health journals.
    """

    def __init__(self, llm: BaseChatModel) -> None:
        self._chain = llm.with_structured_output(ExtractedSupplements)

    async def extract(
        self,
        raw_text: str,
        config: RunnableConfig | None = None,
    ) -> ExtractedSupplements:
        """
        Parse raw text and return structured supplement entries.
        Returns an empty result if extraction fails.
        """
        try:
            result = await self._chain.ainvoke(
                f"{EXTRACTION_PROMPT}\n\nDocument text:\n{raw_text}",
                config=config,
            )
            return result
        except Exception:
            return ExtractedSupplements()
