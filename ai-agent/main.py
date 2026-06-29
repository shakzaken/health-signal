import os
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request
from sentry_sdk.integrations.fastapi import FastApiIntegration

from api.routes import health, ingest, query, report
from core.config import settings
from core.logger import get_logger
from rag.qdrant_client import ensure_collection, get_qdrant_client

logger = get_logger(__name__)

if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, integrations=[FastApiIntegration()])

# Set LangSmith env vars before any langchain import
os.environ["LANGCHAIN_TRACING_V2"] = settings.langchain_tracing_v2
os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting ai-agent — qdrant={settings.qdrant_host}:{settings.qdrant_port}")
    client = get_qdrant_client()
    ensure_collection(client)
    logger.info("Qdrant collection ready")
    yield
    logger.info("AI agent shutting down")


app = FastAPI(
    title="HealthSignal AI Agent",
    description="Ingestion pipeline and RAG query service",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(ingest.router)
app.include_router(query.router)
app.include_router(report.router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"→ {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"← {request.method} {request.url.path} {response.status_code}")
    return response
