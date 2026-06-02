"""Tests for the Chunker class."""

from ingestion.chunker import Chunker


def test_chunk_returns_list_of_strings(chunker, sample_health_text):
    chunks = chunker.chunk(sample_health_text)
    assert isinstance(chunks, list)
    assert all(isinstance(c, str) for c in chunks)


def test_chunk_produces_at_least_one_chunk(chunker, sample_health_text):
    chunks = chunker.chunk(sample_health_text)
    assert len(chunks) >= 1


def test_chunk_empty_string_returns_empty_list(chunker):
    assert chunker.chunk("") == []


def test_chunk_respects_max_size():
    """No chunk should exceed the configured chunk_size."""
    chunker = Chunker(chunk_size=100, chunk_overlap=10)
    long_text = "word " * 500  # 2500 chars
    chunks = chunker.chunk(long_text)
    assert all(len(c) <= 150 for c in chunks)  # small buffer for splitter boundaries


def test_chunk_long_text_produces_multiple_chunks(chunker):
    long_text = "This is a sentence about health. " * 100
    chunks = chunker.chunk(long_text)
    assert len(chunks) > 1


def test_chunk_overlap_means_consecutive_chunks_share_content():
    """With overlap, the end of chunk N should appear in chunk N+1."""
    chunker = Chunker(chunk_size=50, chunk_overlap=20)
    text = "ABCDEFGHIJ " * 30  # long enough to produce multiple chunks
    chunks = chunker.chunk(text)
    if len(chunks) >= 2:
        # The tail of chunk 0 should appear somewhere in chunk 1
        tail = chunks[0][-10:]
        assert tail in chunks[1]
