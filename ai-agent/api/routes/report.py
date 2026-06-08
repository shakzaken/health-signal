from fastapi import APIRouter, Depends
from langchain_core.tracers.langchain import LangChainTracer
from pydantic import BaseModel

from agents.doctor_report import DoctorReportAgent
from api.deps import get_current_user_id, get_doctor_report_agent

router = APIRouter(prefix="/report", tags=["report"])


class ReportRequest(BaseModel):
    period_days: int = 90


class ReportResponse(BaseModel):
    report: str


@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    request: ReportRequest,
    user_id: str = Depends(get_current_user_id),
    agent: DoctorReportAgent = Depends(get_doctor_report_agent),
):
    config = {
        "callbacks": [LangChainTracer()],
        "run_name": "doctor_report_agent",
        "metadata": {"user_id": user_id, "period_days": request.period_days},
        "tags": ["doctor_report_agent"],
    }
    result = await agent.generate(
        user_id=user_id,
        period_days=request.period_days,
        config=config,
    )
    return ReportResponse(report=result["report"])
