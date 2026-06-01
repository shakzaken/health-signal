import base64

from openai import AsyncOpenAI

from core.config import settings


def _get_client() -> AsyncOpenAI:
    """Lazy-initialize the OpenAI client so import doesn't fail without a key."""
    return AsyncOpenAI(api_key=settings.openai_api_key)


async def extract_text_with_vision(image_bytes_list: list[bytes]) -> str:
    """
    Send PDF page images to GPT-4o mini and extract all text.
    Used as OCR fallback when PyMuPDF fails to extract meaningful text.
    """
    content = [
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

    client = _get_client()
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": content}],
        max_tokens=4096,
    )

    return response.choices[0].message.content or ""
