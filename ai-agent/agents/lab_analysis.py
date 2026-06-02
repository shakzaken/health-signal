import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import traceable

from core.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a personal health assistant specializing in lab result analysis.

You have access to the user's full lab marker history from their blood tests.

Guidelines:
- Identify trends: is a marker going up, down, or stable over time?
- Flag values outside the reference range and explain what that means in plain language
- Compare the most recent result to previous ones when multiple tests are available
- Always present findings as observations, not diagnoses
- Suggest questions to ask a doctor when a value looks concerning
- Be calm and factual — avoid alarmist language
- Answer in the same language the user asked the question in
"""


class LabAnalysisAgent:
    """
    Fetches structured lab marker history from the backend and uses the LLM
    to provide trend analysis and plain-language explanations.
    """

    def __init__(self, llm: BaseChatModel, backend_url: str) -> None:
        self._llm = llm
        self._backend_url = backend_url

    async def _fetch_lab_results(self) -> list[dict]:
        """Fetch all lab results with their markers from the backend."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self._backend_url}/lab-results",
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()

    async def _fetch_marker_history(self, marker_name: str) -> list[dict]:
        """Fetch historical values for a specific marker."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self._backend_url}/lab-results/markers/{marker_name}/history",
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json().get("history", [])

    def _format_lab_data(self, lab_results: list[dict]) -> str:
        """Format lab results into a readable context string for the LLM."""
        if not lab_results:
            return "No lab results found."

        lines = []
        for result in lab_results:
            lines.append(f"\n📋 Test date: {result.get('test_date', 'unknown')}")
            if result.get("lab_name"):
                lines.append(f"   Lab: {result['lab_name']}")
            for marker in result.get("markers", []):
                ref = ""
                if marker.get("reference_low") is not None and marker.get("reference_high") is not None:
                    ref = f" (normal: {marker['reference_low']}–{marker['reference_high']})"
                status = f" [{marker['status']}]" if marker.get("status") else ""
                lines.append(
                    f"   • {marker['name']}: {marker['value']} {marker['unit']}{ref}{status}"
                )

        return "\n".join(lines)

    @traceable(name="lab_analysis_agent")
    async def analyze(self, question: str) -> dict:
        """
        Fetch lab history and generate an analysis answering the user's question.
        Returns answer text — no source chunks (data comes from PostgreSQL, not Qdrant).
        """
        logger.info("Lab analysis agent — fetching lab results from backend")
        try:
            lab_results = await self._fetch_lab_results()
        except Exception as e:
            logger.warning(f"Failed to fetch lab results — {e}")
            return {
                "answer": "I couldn't retrieve your lab results at this time. Please try again later.",
                "sources": [],
            }

        if not lab_results:
            return {
                "answer": "No lab results have been saved yet. Please upload a blood test or lab report first.",
                "sources": [],
            }

        context = self._format_lab_data(lab_results)
        logger.info(f"Lab analysis agent — {len(lab_results)} results loaded")

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=f"Lab results history:\n{context}\n\nQuestion: {question}"
            ),
        ]

        response = await self._llm.ainvoke(messages)
        return {
            "answer": response.content,
            "sources": [],
        }
