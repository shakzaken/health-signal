from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from rag.query_chain import answer_query

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    question: str
    document_type: Optional[str] = None


class SourceChunk(BaseModel):
    text: str
    document_id: Optional[str]
    document_type: Optional[str]
    source_date: Optional[str]
    filename: Optional[str]
    score: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]


@router.post("", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    result = await answer_query(
        question=request.question,
        document_type=request.document_type,
    )
    return QueryResponse(
        answer=result["answer"],
        sources=[SourceChunk(**s) for s in result["sources"]],
    )
