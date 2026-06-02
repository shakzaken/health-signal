"""Tests for the Embedder class."""

from ingestion.embedder import Embedder

VECTOR_SIZE = 1024  # intfloat/multilingual-e5-large


def test_embed_returns_correct_number_of_vectors(embedder):
    chunks = ["hello world", "lab results", "cholesterol levels"]
    vectors = embedder.embed(chunks)
    assert len(vectors) == len(chunks)


def test_embed_returns_correct_vector_dimension(embedder):
    vectors = embedder.embed(["some health text"])
    assert len(vectors[0]) == VECTOR_SIZE


def test_embed_vectors_are_floats(embedder):
    vectors = embedder.embed(["test"])
    assert all(isinstance(v, float) for v in vectors[0])


def test_embed_similar_texts_have_high_cosine_similarity(embedder):
    """Semantically similar texts should be closer in vector space."""
    import math

    def cosine_sim(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x ** 2 for x in a))
        norm_b = math.sqrt(sum(x ** 2 for x in b))
        return dot / (norm_a * norm_b)

    v1, v2, v3 = embedder.embed([
        "blood test results hemoglobin",
        "hemoglobin blood count test",   # similar
        "car engine oil change",          # unrelated
    ])
    sim_similar = cosine_sim(v1, v2)
    sim_unrelated = cosine_sim(v1, v3)
    assert sim_similar > sim_unrelated


def test_embedder_model_is_lazy_loaded():
    """Model should not be loaded until embed() is first called."""
    fresh = Embedder()
    assert fresh._model is None
    fresh.embed(["trigger load"])
    assert fresh._model is not None


def test_embedder_reuses_model_across_calls(embedder):
    model_before = embedder._model
    embedder.embed(["another call"])
    assert embedder._model is model_before
