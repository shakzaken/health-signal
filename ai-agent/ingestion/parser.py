from pathlib import Path

import fitz  # PyMuPDF

from ingestion.vision_extractor import extract_text_with_vision


def is_meaningful_text(text: str) -> bool:
    """
    Heuristic check to determine if extracted text is real content.
    No LLM call needed — pure string analysis.
    """
    text = text.strip()

    if len(text) < 100:
        return False

    if len(text.split()) < 20:
        return False

    alpha_ratio = sum(c.isalpha() for c in text) / len(text)
    if alpha_ratio < 0.6:
        return False

    return True


def _extract_pdf_text(file_path: str) -> str:
    """Extract text from a text-based PDF using PyMuPDF."""
    doc = fitz.open(file_path)
    return "\n".join(page.get_text() for page in doc)


def _render_pdf_to_images(file_path: str) -> list[bytes]:
    """Render each PDF page to a PNG image (for OCR fallback)."""
    doc = fitz.open(file_path)
    images = []
    for page in doc:
        pix = page.get_pixmap(dpi=200)
        images.append(pix.tobytes("png"))
    return images


async def parse_document(file_path: str) -> str:
    """
    Parse a document and return its full text.

    Flow:
    1. If PDF — try PyMuPDF text extraction.
    2. If extracted text fails the heuristic check — fall back to GPT-4o mini vision OCR.
    3. If plain text file — read directly.
    """
    path = Path(file_path)

    if path.suffix.lower() == ".pdf":
        text = _extract_pdf_text(file_path)

        if is_meaningful_text(text):
            return text

        # OCR fallback: render pages as images, send to GPT-4o mini
        images = _render_pdf_to_images(file_path)
        return await extract_text_with_vision(images)

    # Plain text fallback
    return path.read_text(encoding="utf-8", errors="ignore")
