"""
FastAPI dependency providers.

Singletons (Embedder, Chunker) are cached with functools.lru_cache so the
expensive model load only happens once per process.
Lightweight objects (QdrantClient, IngestionPipeline, QueryChain) are
re-created per request — the construction cost is negligible.
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from langchain_openai import ChatOpenAI

from agents.doctor_report import DoctorReportAgent
from agents.supervisor import Supervisor
from core.config import settings
from core.security import decode_access_token
from ingestion.chunker import Chunker
from ingestion.embedder import Embedder
from ingestion.parser import DocumentParser
from ingestion.pipeline import IngestionPipeline
from ingestion.vision_extractor import VisionExtractor
from rag.qdrant_client import ensure_collection, get_qdrant_client
from rag.query_chain import QueryChain
from rag.retriever import Retriever
from rag.writer import QdrantWriter
from tools.document_classifier import DocumentClassifier
from tools.lab_extractor import LabExtractor
from tools.supplement_extractor import SupplementExtractor
from tools.symptom_extractor import SymptomExtractor

bearer_scheme = HTTPBearer()


def get_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    """Return the raw JWT string after validating it. Raises 401 on failure."""
    try:
        decode_access_token(credentials.credentials)  # validate
        return credentials.credentials
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    """Validate JWT and return user_id string. Raises 401 on failure."""
    try:
        return decode_access_token(credentials.credentials)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


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
    # ensure_collection is called once at startup in main.py's lifespan handler.
    # No need to re-check on every ingest request.
    llm = get_llm()
    client = get_qdrant_client()
    return IngestionPipeline(
        parser=DocumentParser(VisionExtractor()),
        chunker=get_chunker(),
        embedder=get_embedder(),
        writer=QdrantWriter(client),
        lab_extractor=LabExtractor(llm),
        symptom_extractor=SymptomExtractor(llm),
        supplement_extractor=SupplementExtractor(llm),
        classifier=DocumentClassifier(llm),
    )


def get_supervisor(token: str = Depends(get_token)) -> Supervisor:
    llm = get_llm()
    client = get_qdrant_client()
    rag_chain = QueryChain(
        retriever=Retriever(client=client, embedder=get_embedder()),
        llm=llm,
    )
    return Supervisor(
        llm=llm,
        rag_chain=rag_chain,
        backend_url=settings.backend_url,
        ai_agent_url=settings.ai_agent_url,
        token=token,
    )


def get_doctor_report_agent(token: str = Depends(get_token)) -> DoctorReportAgent:
    return DoctorReportAgent(llm=get_llm(), backend_url=settings.backend_url, token=token)
