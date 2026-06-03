import base64

from langchain_core.messages import HumanMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_openai import ChatOpenAI

from core.config import settings

_EXTRACT_PROMPT = (
    "Extract all text from this medical document exactly as it appears. "
    "Preserve structure including labels, values, and units. "
    "Return only the extracted text, no commentary."
)


class VisionExtractor:
    """
    OCR fallback using GPT-4o mini vision.
    Used when PyMuPDF cannot extract meaningful text from a PDF.
    Uses ChatOpenAI (LangChain) so the call is traced via the shared
    RunnableConfig callback manager — no separate @traceable needed.
    """

    def __init__(self, api_key: str | None = None) -> None:
        self._llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=api_key or settings.openai_api_key,
        )

    async def extract(
        self,
        image_bytes_list: list[bytes],
        config: RunnableConfig | None = None,
    ) -> str:
        """
        Send PDF page images to GPT-4o mini and extract all text.
        Preserves structure including labels, values, and units.
        """
        content: list[dict] = [{"type": "text", "text": _EXTRACT_PROMPT}]

        for image_bytes in image_bytes_list:
            b64 = base64.b64encode(image_bytes).decode("utf-8")
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "high"},
                }
            )

        message = HumanMessage(content=content)
        response = await self._llm.ainvoke([message], config=config)
        return response.content or ""
