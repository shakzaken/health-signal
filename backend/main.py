from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration

from api.routes import admin, ai_agent, auth, conversations, documents, health, lab_results, supplements, symptoms, timeline
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, integrations=[FastApiIntegration()])


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

if settings.environment == "dev":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(ai_agent.router)
app.include_router(documents.router)
app.include_router(lab_results.router)
app.include_router(symptoms.router)
app.include_router(supplements.router)
app.include_router(timeline.router)
app.include_router(conversations.router)
app.include_router(admin.router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"→ {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"← {request.method} {request.url.path} {response.status_code}")
    return response
