from typing import Literal

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel

from core.logger import get_logger

logger = get_logger(__name__)

CLASSIFICATION_PROMPT = """You are a medical document classifier.

Read the document text below and return the single most appropriate type.

Types:
- blood_test      — lab results from a blood draw (CBC, metabolic panel, vitamins, etc.)
- lab_report      — other laboratory reports (urine, pathology, imaging, microbiology)
- symptom_note    — a clinical note describing patient symptoms written by a doctor or nurse
- supplement_list — a list or log of supplements / vitamins / medications the patient takes
- diet_note       — a food diary, nutritional log, or diet plan
- doctor_summary  — a physician's visit summary, discharge letter, or referral
- journal         — a personal health journal or diary written by the patient themselves

Return only the type field. Do not explain."""


class ClassificationResult(BaseModel):
    document_type: Literal[
        "blood_test",
        "lab_report",
        "symptom_note",
        "supplement_list",
        "diet_note",
        "doctor_summary",
        "journal",
    ]


class DocumentClassifier:
    def __init__(self, llm: BaseChatModel) -> None:
        self._chain = llm.with_structured_output(ClassificationResult)

    async def classify(self, raw_text: str, config=None) -> str:
        prompt = f"{CLASSIFICATION_PROMPT}\n\nDocument text:\n{raw_text[:3000]}"
        try:
            result: ClassificationResult = await self._chain.ainvoke(prompt, config=config)
            logger.info(f"Document classified as: {result.document_type}")
            return result.document_type
        except Exception as e:
            logger.error(f"Document classification failed: {e}")
            return "journal"  # safe fallback — still ingests to Qdrant
