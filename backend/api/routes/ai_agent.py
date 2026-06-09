"""
Proxy routes for the AI agent service.

The frontend sends all requests to the backend; the backend forwards them to
the ai-agent process running on the internal network.  This keeps the ai-agent
port private and centralises auth in one place.
"""

from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from api.deps import get_current_user
from core.config import settings
from core.logger import get_logger
from models.user import User

logger = get_logger(__name__)

router = APIRouter(prefix="/ai", tags=["ai-agent"])

# Timeout for non-streaming calls (report generation can be slow)
QUERY_TIMEOUT = 120.0
REPORT_TIMEOUT = 300.0


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    session_id: Optional[str] = None
    document_type: Optional[str] = None


class ReportRequest(BaseModel):
    period_days: int = 90


def _auth_header(user: User) -> dict:
    """Re-use the backend JWT as the ai-agent auth token."""
    from core.security import create_access_token
    token = create_access_token(str(user.id))
    return {"Authorization": f"Bearer {token}"}


@router.post("/query/stream")
async def proxy_query_stream(
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
):
    """Stream the AI answer as Server-Sent Events, proxied from the ai-agent."""

    async def stream():
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{settings.ai_agent_url}/query/stream",
                    json=request.model_dump(),
                    headers=_auth_header(current_user),
                    timeout=QUERY_TIMEOUT,
                ) as resp:
                    if resp.status_code != 200:
                        error = await resp.aread()
                        logger.error(f"ai-agent stream error — status={resp.status_code} body={error}")
                        return
                    async for chunk in resp.aiter_bytes():
                        yield chunk
        except httpx.RequestError as e:
            logger.error(f"ai-agent stream request failed — {e}")

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/query")
async def proxy_query(
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
):
    """Forward a query to the ai-agent and return the JSON response."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.ai_agent_url}/query",
                json=request.model_dump(),
                headers=_auth_header(current_user),
                timeout=QUERY_TIMEOUT,
            )
    except httpx.RequestError as e:
        logger.error(f"ai-agent query request failed — {e}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI agent unreachable")

    if not resp.is_success:
        logger.error(f"ai-agent query error — status={resp.status_code}")
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return resp.json()


@router.post("/report/generate")
async def proxy_report(
    request: ReportRequest,
    current_user: User = Depends(get_current_user),
):
    """Forward a report generation request to the ai-agent."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.ai_agent_url}/report/generate",
                json=request.model_dump(),
                headers=_auth_header(current_user),
                timeout=REPORT_TIMEOUT,
            )
    except httpx.RequestError as e:
        logger.error(f"ai-agent report request failed — {e}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI agent unreachable")

    if not resp.is_success:
        logger.error(f"ai-agent report error — status={resp.status_code}")
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return resp.json()
