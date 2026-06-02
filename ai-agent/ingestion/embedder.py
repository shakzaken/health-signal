from fastembed import TextEmbedding

MODEL_NAME = "BAAI/bge-small-en-v1.5"


class Embedder:
    """
    Wraps the FastEmbed model for in-process text embedding.
    The model (~130 MB) is lazy-loaded on first use and then reused.
    No GPU required — runs on CPU.
    """

    def __init__(self, model_name: str = MODEL_NAME) -> None:
        self._model_name = model_name
        self._model: TextEmbedding | None = None

    def _get_model(self) -> TextEmbedding:
        if self._model is None:
            self._model = TextEmbedding(model_name=self._model_name)
        return self._model

    def embed(self, chunks: list[str]) -> list[list[float]]:
        """Embed a list of text chunks. Returns a list of float vectors."""
        model = self._get_model()
        return [e.tolist() for e in model.embed(chunks)]
