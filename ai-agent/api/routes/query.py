from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.deps import get_query_chain
from rag.query_chain import QueryChain

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    question: str
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


@router.post("", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    chain: QueryChain = Depends(get_query_chain),
):
    result = await chain.answer(
        question=request.question,
        document_type=request.document_type,
    )
    return QueryResponse(
        answer=result["answer"],
        sources=[SourceChunk(**s) for s in result["sources"]],
    )
