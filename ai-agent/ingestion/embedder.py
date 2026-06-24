from openai import AsyncOpenAI

VECTOR_SIZE = 4096  # qwen/qwen3-embedding-8b default output dimensions


class Embedder:
    """
    Embeds text via the OpenRouter API (Qwen3-Embedding).
    Constructed with the API key and model name — no local model loaded.
    """

    def __init__(self, api_key: str, model: str) -> None:
        self._model = model
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts. Returns a list of float vectors."""
        response = await self._client.embeddings.create(
            model=self._model,
            input=texts,
        )
        return [item.embedding for item in response.data]
