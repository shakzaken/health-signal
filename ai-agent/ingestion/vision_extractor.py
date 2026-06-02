import base64

from openai import AsyncOpenAI

from core.config import settings


class VisionExtractor:
    """
    OCR fallback using GPT-4o mini vision.
    Used when PyMuPDF cannot extract meaningful text from a PDF.
    Client is lazy-initialized to avoid import-time failure without an API key.
    """

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or settings.openai_api_key
        self._client: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client

    async def extract(self, image_bytes_list: list[bytes]) -> str:
        """
        Send PDF page images to GPT-4o mini and extract all text.
        Preserves structure including labels, values, and units.
        """
        content: list[dict] = [
            {
                "type": "text",
                "text": (
                    "Extract all text from this medical document exactly as it appears. "
                    "Preserve structure including labels, values, and units. "
                    "Return only the extracted text, no commentary."
                ),
            }
        ]

        for image_bytes in image_bytes_list:
            b64 = base64.b64encode(image_bytes).decode("utf-8")
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "high"},
                }
            )

        client = self._get_client()
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": content}],
            max_tokens=4096,
        )

        return response.choices[0].message.content or ""
