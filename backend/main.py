from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from api.routes import documents, health, lab_results, supplements, symptoms, timeline
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting backend — database={settings.database_url} ai_agent={settings.ai_agent_url}")
    # Schema is managed exclusively by Alembic migrations (`make migrate`).
    # create_db_and_tables() is intentionally NOT called here.
    yield
    logger.info("Backend shutting down")


app = FastAPI(
    title="HealthSignal Backend",
    description="Personal health data API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(documents.router)
app.include_router(lab_results.router)
app.include_router(symptoms.router)
app.include_router(supplements.router)
app.include_router(timeline.router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"→ {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"← {request.method} {request.url.path} {response.status_code}")
    return response
