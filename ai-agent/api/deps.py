"""
FastAPI dependency providers.

Singletons (Embedder, Chunker) are cached with functools.lru_cache so the
expensive model load only happens once per process.
Lightweight objects (QdrantClient, IngestionPipeline, QueryChain) are
re-created per request — the construction cost is negligible.
"""

from functools import lru_cache

from langchain_openai import ChatOpenAI

from agents.supervisor import Supervisor
from core.config import settings
from ingestion.chunker import Chunker
from ingestion.embedder import Embedder
from ingestion.parser import DocumentParser
from ingestion.pipeline import IngestionPipeline
from ingestion.vision_extractor import VisionExtractor
from rag.qdrant_client import ensure_collection, get_qdrant_client
from rag.query_chain import QueryChain
from rag.retriever import Retriever
from rag.writer import QdrantWriter
from tools.lab_extractor import LabExtractor


@lru_cache
def get_embedder() -> Embedder:
    """Singleton — the FastEmbed model is expensive to load."""
    return Embedder()


@lru_cache
def get_chunker() -> Chunker:
    """Singleton — the splitter object is stateless and reusable."""
    return Chunker()


def get_llm() -> ChatOpenAI:
    return ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key)


def get_ingestion_pipeline() -> IngestionPipeline:
    client = get_qdrant_client()
    ensure_collection(client)
    return IngestionPipeline(
        parser=DocumentParser(VisionExtractor()),
        chunker=get_chunker(),
        embedder=get_embedder(),
        writer=QdrantWriter(client),
        lab_extractor=LabExtractor(get_llm()),
    )


def get_supervisor() -> Supervisor:
    llm = get_llm()
    client = get_qdrant_client()
    rag_chain = QueryChain(
        retriever=Retriever(client=client, embedder=get_embedder()),
        llm=llm,
    )
    return Supervisor(llm=llm, rag_chain=rag_chain, backend_url=settings.backend_url)
