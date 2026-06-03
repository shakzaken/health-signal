"""
Tests for the IngestionPipeline class.

Qdrant writes are mocked — we test the pipeline logic and coordination,
not the Qdrant client itself.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ingestion.chunker import Chunker
from ingestion.embedder import Embedder
from ingestion.parser import DocumentParser
from ingestion.pipeline import IngestionPipeline
from rag.writer import QdrantWriter
from tools.lab_extractor import ExtractedLabResult, LabExtractor

PDF_PATH = str(Path(__file__).parents[2] / "test-data" / "04efd_myTests.pdf")


@pytest.fixture
def mock_writer() -> MagicMock:
    writer = MagicMock(spec=QdrantWriter)
    writer.write = MagicMock()
    return writer


@pytest.fixture
def mock_lab_extractor() -> MagicMock:
    extractor = MagicMock(spec=LabExtractor)
    extractor.extract = AsyncMock(return_value=ExtractedLabResult())
    return extractor


@pytest.fixture
def pipeline(chunker, embedder, mock_writer, mock_lab_extractor) -> IngestionPipeline:
    """Real parser + chunker + embedder, mocked writer and extractor."""
    return IngestionPipeline(
        parser=DocumentParser(),
        chunker=chunker,
        embedder=embedder,
        writer=mock_writer,
        lab_extractor=mock_lab_extractor,
    )


@pytest.mark.asyncio
async def test_pipeline_succeeds_with_real_pdf(pipeline, mock_writer):
    result = await pipeline.run(
        document_id="doc-123",
        file_path=PDF_PATH,
        document_type="lab_report",
        source_date="2024-01-15",
        filename="04efd_myTests.pdf",
    )
    assert result["success"] is True
    assert result["chunks_stored"] > 0
    assert result["document_id"] == "doc-123"


@pytest.mark.asyncio
async def test_pipeline_calls_writer_with_correct_metadata(pipeline, mock_writer):
    await pipeline.run(
        document_id="doc-456",
        file_path=PDF_PATH,
        document_type="blood_test",
        source_date="2024-03-01",
        filename="blood.pdf",
    )
    mock_writer.write.assert_called_once()
    call_kwargs = mock_writer.write.call_args.kwargs
    assert call_kwargs["document_id"] == "doc-456"
    assert call_kwargs["document_type"] == "blood_test"
    assert call_kwargs["filename"] == "blood.pdf"
    assert call_kwargs["source_date"] == "2024-03-01"


@pytest.mark.asyncio
async def test_pipeline_chunks_and_vectors_have_same_length(pipeline, mock_writer):
    await pipeline.run(
        document_id="doc-789",
        file_path=PDF_PATH,
        document_type="lab_report",
        source_date=None,
        filename="test.pdf",
    )
    call_kwargs = mock_writer.write.call_args.kwargs
    assert len(call_kwargs["chunks"]) == len(call_kwargs["vectors"])


@pytest.mark.asyncio
async def test_pipeline_returns_failure_when_file_not_found(pipeline):
    result = await pipeline.run(
        document_id="doc-bad",
        file_path="/nonexistent/path/file.pdf",
        document_type="lab_report",
        source_date=None,
        filename="missing.pdf",
    )
    assert result["success"] is False
    assert result["error"] is not None


@pytest.mark.asyncio
async def test_pipeline_returns_failure_when_no_chunks_produced(mock_writer, mock_lab_extractor, chunker, embedder):
    """If the document produces no chunks, ingestion should fail gracefully."""
    parser = AsyncMock(spec=DocumentParser)
    parser.parse.return_value = ""  # empty text → no chunks

    pipeline = IngestionPipeline(
        parser=parser,
        chunker=chunker,
        embedder=embedder,
        writer=mock_writer,
        lab_extractor=mock_lab_extractor,
    )
    result = await pipeline.run(
        document_id="doc-empty",
        file_path="fake.pdf",
        document_type="lab_report",
        source_date=None,
        filename="fake.pdf",
    )
    assert result["success"] is False
    mock_writer.write.assert_not_called()
