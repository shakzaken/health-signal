import os

from fastapi import FastAPI, Request

from api.routes import health, ingest, query
from core.config import settings
from core.logger import get_logger
from rag.qdrant_client import ensure_collection, get_qdrant_client

logger = get_logger(__name__)

# Set LangSmith env vars at startup
os.environ["LANGCHAIN_TRACING_V2"] = settings.langchain_tracing_v2
os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project


app = FastAPI(
    title="HealthSignal AI Agent",
    description="Ingestion pipeline and RAG query service",
    version="0.1.0",
)

app.include_router(health.router)
app.include_router(ingest.router)
app.include_router(query.router)


@app.on_event("startup")
async def startup():
    logger.info(f"Starting ai-agent — qdrant={settings.qdrant_host}:{settings.qdrant_port}")
    client = get_qdrant_client()
    ensure_collection(client)
    logger.info("Qdrant collection ready")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"→ {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"← {request.method} {request.url.path} {response.status_code}")
    return response
