from pathlib import Path

import fitz  # PyMuPDF
from langchain_core.runnables.config import RunnableConfig

from ingestion.vision_extractor import VisionExtractor


class DocumentParser:
    """
    Parses uploaded documents into plain text.

    Flow for PDFs:
    1. Try PyMuPDF text extraction (fast, free).
    2. If the result fails the meaningful-text heuristic, fall back to
       GPT-4o mini vision OCR (covers scanned / image-based PDFs).

    Plain text files are read directly.
    """

    def __init__(self, vision_extractor: VisionExtractor | None = None) -> None:
        self._vision = vision_extractor or VisionExtractor()

    @staticmethod
    def is_meaningful_text(text: str) -> bool:
        """
        Heuristic to decide whether PyMuPDF extracted real content.
        No LLM call — pure string analysis.
        """
        text = text.strip()
        if len(text) < 100:
            return False
        if len(text.split()) < 20:
            return False
        alpha_ratio = sum(c.isalpha() for c in text) / len(text)
        return alpha_ratio >= 0.6

    @staticmethod
    def _extract_pdf_text(file_path: str) -> str:
        doc = fitz.open(file_path)
        return "\n".join(page.get_text() for page in doc)

    @staticmethod
    def _render_pdf_to_images(file_path: str) -> list[bytes]:
        doc = fitz.open(file_path)
        return [page.get_pixmap(dpi=200).tobytes("png") for page in doc]

    async def parse(
        self,
        file_path: str,
        config: RunnableConfig | None = None,
    ) -> str:
        """Parse a document and return its full text."""
        path = Path(file_path)

        if path.suffix.lower() == ".pdf":
            text = self._extract_pdf_text(file_path)
            if self.is_meaningful_text(text):
                return text
            # OCR fallback: render pages as images and send to GPT-4o mini
            images = self._render_pdf_to_images(file_path)
            return await self._vision.extract(images, config=config)

        # Plain text fallback
        return path.read_text(encoding="utf-8", errors="ignore")
