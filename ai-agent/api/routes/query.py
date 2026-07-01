from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agents.supervisor import Supervisor
from api.deps import get_current_user_id, get_supervisor

router = APIRouter(prefix="/api/query", tags=["query"])


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    session_id: Optional[str] = None
    document_type: Optional[str] = None


class SourceChunk(BaseModel):
    text: str
    document_id: Optional[str] = None
    document_type: Optional[str] = None
    source_date: Optional[str] = None
    filename: Optional[str] = None
    score: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    route: str


@router.post("/stream")
async def query_documents_stream(
    request: QueryRequest,
    user_id: str = Depends(get_current_user_id),
    supervisor: Supervisor = Depends(get_supervisor),
):
    """Stream the answer as Server-Sent Events (text/event-stream).

    Each event is a JSON object:
    - {"token": "..."} for each chunk of the answer
    - {"sources": [...]} as the final event
    """
    return StreamingResponse(
        supervisor.run_stream(
            question=request.question,
            session_id=request.session_id,
            document_type=request.document_type,
            user_id=user_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    user_id: str = Depends(get_current_user_id),
    supervisor: Supervisor = Depends(get_supervisor),
):
    result = await supervisor.run(
        question=request.question,
        session_id=request.session_id,
        document_type=request.document_type,
        user_id=user_id,
    )
    return QueryResponse(
        answer=result["answer"],
        sources=[SourceChunk(**s) for s in result["sources"]],
        route=result["route"],
    )
