from fastembed import TextEmbedding

MODEL_NAME = "BAAI/bge-small-en-v1.5"

# Loaded once at module level — model is cached after first download
_model: TextEmbedding | None = None


def get_model() -> TextEmbedding:
    global _model
    if _model is None:
        _model = TextEmbedding(model_name=MODEL_NAME)
    return _model


def embed_chunks(chunks: list[str]) -> list[list[float]]:
    """Embed a list of text chunks. Returns a list of float vectors."""
    model = get_model()
    embeddings = list(model.embed(chunks))
    return [e.tolist() for e in embeddings]
