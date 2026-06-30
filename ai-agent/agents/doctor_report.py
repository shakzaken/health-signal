import asyncio
from datetime import date, timedelta
from typing import Optional

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from core.guardrails import SAFETY_INSTRUCTION
from core.logger import get_logger

logger = get_logger(__name__)

REPORT_SYSTEM_PROMPT = """You are a personal health assistant helping a user prepare for a doctor appointment.

You will receive a structured summary of the user's recent health data:
- Abnormal lab markers (outside reference range) with trends
- Recent symptoms
- Recent supplement changes

Your task is to write a clear, well-structured doctor visit report and generate a list of suggested questions the user should ask their doctor.

Format the report with clear sections:
1. ABNORMAL LAB MARKERS — list each marker, its value vs reference range, and trend direction (improving / worsening / stable)
2. RECENT SYMPTOMS — list symptoms with frequency and severity
3. SUPPLEMENT CHANGES — list any starts or stops in the period
4. SUGGESTED QUESTIONS FOR YOUR DOCTOR — 3–6 specific, medically relevant questions derived from the data

Guidelines:
- Be factual and calm — present observations, never diagnoses
- Highlight what has changed or is trending in the wrong direction
- Make the questions specific to the user's actual data (e.g. name the marker, name the symptom)
- Write in plain language — the report is for the user, not for a clinician
- If there is no data in a section, say "No data available for this period"
""" + SAFETY_INSTRUCTION

SUMMARIZE_PROMPT = """Summarize the following conversation history into a short paragraph (3–5 sentences).
Focus on what health topics were discussed, what data was looked at, and what conclusions were reached.
This summary will be used as context for future questions in this conversation.

Conversation:
{transcript}

Summary:"""


class DoctorReportState(TypedDict):
    user_id: str
    period_days: int
    conversation_context: str   # summary + recent turns from the supervisor — empty when called directly
    lab_summary: str
    symptom_summary: str
    supplement_summary: str
    report: str


class DoctorReportAgent:
    """
    LangGraph sequential pipeline that generates a doctor visit prep report.

    Graph: fetch_data → generate_report → END

    Unlike the ReAct sub-agents, this uses deterministic sequential nodes — we always
    want the same three data sections and the same report format, so there is no need
    for a tool-calling loop.
    """

    def __init__(self, llm: BaseChatModel, backend_url: str, token: str = "") -> None:
        self._llm = llm
        self._backend_url = backend_url
        self._token = token
        self._graph = self._build_graph()

    @property
    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"} if self._token else {}

    # ── Data fetching helpers ─────────────────────────────────────────────────

    async def _get_json(self, url: str, params: dict | None = None) -> list | None:
        """GET the URL and return parsed JSON, or None on failure."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    url,
                    headers=self._auth_headers,
                    params=params,
                    timeout=15.0,
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.warning(f"Backend request failed — url={url} error={e}")
            return None

    async def _fetch_abnormal_labs(self, period_days: int) -> str:
        """Fetch lab results and return a summary of abnormal markers."""
        results = await self._get_json(f"{self._backend_url}/api/lab-results")
        if results is None:
            return "Could not fetch lab results."
        if not results:
            return "No lab results found."

        cutoff = date.today() - timedelta(days=period_days)
        lines = []
        for result in results:
            test_date_str = result.get("test_date")
            if not test_date_str:
                continue
            try:
                test_date = date.fromisoformat(test_date_str)
            except ValueError:
                continue
            if test_date < cutoff:
                continue

            abnormal = [
                m for m in result.get("markers", [])
                if m.get("status") in ("low", "high")
            ]
            if not abnormal:
                continue

            lines.append(f"\nBlood test — {test_date_str}:")
            for m in abnormal:
                ref = ""
                if m.get("reference_low") is not None and m.get("reference_high") is not None:
                    ref = f" (normal: {m['reference_low']}–{m['reference_high']})"
                lines.append(f"  • {m['name']}: {m['value']} {m['unit']}{ref} [{m['status'].upper()}]")

        return "\n".join(lines) if lines else "No abnormal markers found in this period."

    async def _fetch_symptoms(self, period_days: int) -> str:
        """Fetch recent symptom entries."""
        from_date = (date.today() - timedelta(days=period_days)).isoformat()
        entries = await self._get_json(
            f"{self._backend_url}/api/symptom-entries", params={"from": from_date}
        )
        if entries is None:
            return "Could not fetch symptom data."
        if not entries:
            return "No symptoms recorded in this period."

        lines = []
        for e in entries:
            severity = f" ({e['severity']})" if e.get("severity") else ""
            occurred = e.get("occurred_at", "unknown date")
            notes = f" — {e['notes']}" if e.get("notes") else ""
            lines.append(f"  • {e['symptom_name']}{severity} on {occurred}{notes}")
        return "\n".join(lines)

    async def _fetch_supplements(self, period_days: int) -> str:
        """Fetch supplement entries from the period."""
        from_date = (date.today() - timedelta(days=period_days)).isoformat()
        entries = await self._get_json(
            f"{self._backend_url}/api/supplement-entries", params={"from": from_date}
        )
        if entries is None:
            return "Could not fetch supplement data."
        if not entries:
            return "No supplement entries recorded in this period."

        lines = []
        for e in entries:
            dosage = f" {e['dosage']}" if e.get("dosage") else ""
            freq = f", {e['frequency']}" if e.get("frequency") else ""
            started = f" (started: {e['started_at']})" if e.get("started_at") else ""
            lines.append(f"  • {e['name']}{dosage}{freq}{started}")
        return "\n".join(lines)

    # ── Graph nodes ───────────────────────────────────────────────────────────

    async def _fetch_data(
        self, state: DoctorReportState, config: RunnableConfig
    ) -> DoctorReportState:
        """Fetch all three data sources in parallel."""
        period = state["period_days"]
        lab_summary, symptom_summary, supplement_summary = await asyncio.gather(
            self._fetch_abnormal_labs(period),
            self._fetch_symptoms(period),
            self._fetch_supplements(period),
        )
        return {
            **state,
            "lab_summary": lab_summary,
            "symptom_summary": symptom_summary,
            "supplement_summary": supplement_summary,
        }

    async def _generate_report(
        self, state: DoctorReportState, config: RunnableConfig
    ) -> DoctorReportState:
        """Call LLM to generate the structured report from the fetched data."""
        period = state["period_days"]
        user_data = (
            f"Period: last {period} days\n\n"
            f"ABNORMAL LAB MARKERS:\n{state['lab_summary']}\n\n"
            f"RECENT SYMPTOMS:\n{state['symptom_summary']}\n\n"
            f"SUPPLEMENT CHANGES:\n{state['supplement_summary']}"
        )
        if state.get("conversation_context"):
            user_data += f"\n\nCONVERSATION CONTEXT (topics the user has been asking about — use this to make the suggested questions more relevant):\n{state['conversation_context']}"

        messages = [
            SystemMessage(content=REPORT_SYSTEM_PROMPT),
            HumanMessage(content=user_data),
        ]
        response = await self._llm.ainvoke(messages, config=config)
        return {**state, "report": response.content}

    # ── Graph assembly ────────────────────────────────────────────────────────

    def _build_graph(self):
        graph = StateGraph(DoctorReportState)
        graph.add_node("fetch_data", self._fetch_data)
        graph.add_node("generate_report", self._generate_report)
        graph.set_entry_point("fetch_data")
        graph.add_edge("fetch_data", "generate_report")
        graph.add_edge("generate_report", END)
        return graph.compile()

    # ── Public API ────────────────────────────────────────────────────────────

    async def generate(
        self,
        user_id: str = "",
        period_days: int = 90,
        conversation_context: str = "",
        config: Optional[RunnableConfig] = None,
    ) -> dict:
        initial: DoctorReportState = {
            "user_id": user_id,
            "period_days": period_days,
            "conversation_context": conversation_context,
            "lab_summary": "",
            "symptom_summary": "",
            "supplement_summary": "",
            "report": "",
        }
        final = await self._graph.ainvoke(initial, config=config)
        return {"report": final["report"]}

    async def summarize_conversation(
        self, transcript: str, config: Optional[RunnableConfig] = None
    ) -> str:
        """Compress a conversation transcript into a short summary paragraph."""
        prompt = SUMMARIZE_PROMPT.format(transcript=transcript)
        response = await self._llm.ainvoke(
            [HumanMessage(content=prompt)], config=config
        )
        return response.content.strip()
