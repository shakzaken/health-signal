from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routes import documents, health, lab_results, timeline
from db.session import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield


app = FastAPI(
    title="HealthSignal Backend",
    description="Personal health data API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(documents.router)
app.include_router(lab_results.router)
app.include_router(timeline.router)
