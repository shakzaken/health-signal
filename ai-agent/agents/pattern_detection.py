import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import tool

from core.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a personal health pattern analyst.

You have access to the following tools:
- fetch_lab_results: retrieves all structured lab test results with markers and dates
- fetch_symptoms_in_range: retrieves symptom entries within a date range
- fetch_supplements_in_range: retrieves supplement entries within a date range
- search_documents: performs a semantic search across all uploaded health documents

Your job is to find meaningful temporal patterns and correlations across different types of health data.

IMPORTANT — follow this sequence:
1. ALWAYS call fetch_lab_results FIRST. This reveals the actual dates of available data. Do not assume any date range before seeing real data.
2. Based on the lab result dates and the question, determine the relevant time window (e.g. if the earliest test is June 2025, search symptoms from 2025-01-01 onward).
3. Call fetch_symptoms_in_range and fetch_supplements_in_range with date ranges derived from the real data — never from assumptions.
4. Use search_documents for any context not captured in structured data.
5. Reason over all collected data to identify temporal patterns and correlations.

Additional guidelines:
- Look for overlapping time periods: do symptoms appear when a lab marker is abnormal? Did a supplement change coincide with a lab improvement?
- Present findings as observations with clear timelines — never as diagnoses
- Be explicit about what is correlation vs. what is speculation
- If the data is insufficient to detect a pattern, say so clearly
- Answer in the same language the user asked in
"""


class PatternDetectionAgent:
    """
    Uses LangChain tool calling to fetch lab results, symptoms, and supplements
    across a time window and detect temporal correlations.
    """

    def __init__(self, llm: BaseChatModel, backend_url: str) -> None:
        self._llm = llm
        self._backend_url = backend_url
        self._tools = self._build_tools()
        self._tools_by_name = {t.name: t for t in self._tools}
        self._llm_with_tools = llm.bind_tools(self._tools)

    def _build_tools(self) -> list:
        backend_url = self._backend_url

        @tool
        async def fetch_lab_results() -> str:
            """Fetch all lab test results with their markers and test dates."""
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{backend_url}/lab-results", timeout=10.0)
                response.raise_for_status()
                results = response.json()

            if not results:
                return "No lab results found."

            lines = []
            for result in results:
                lines.append(f"\nTest date: {result.get('test_date', 'unknown')}")
                if result.get("lab_name"):
                    lines.append(f"Lab: {result['lab_name']}")
                for marker in result.get("markers", []):
                    ref = ""
                    if marker.get("reference_low") is not None and marker.get("reference_high") is not None:
                        ref = f" (normal: {marker['reference_low']}–{marker['reference_high']})"
                    status = f" [{marker['status']}]" if marker.get("status") else ""
                    lines.append(f"  • {marker['name']}: {marker['value']} {marker['unit']}{ref}{status}")
            return "\n".join(lines)

        @tool
        async def fetch_symptoms_in_range(from_date: str, to_date: str) -> str:
            """
            Fetch symptom entries within a date range.
            from_date and to_date must be ISO date strings (YYYY-MM-DD).
            """
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{backend_url}/symptom-entries",
                    params={"from": from_date, "to": to_date},
                    timeout=10.0,
                )
                response.raise_for_status()
                entries = response.json()

            if not entries:
                return f"No symptoms found between {from_date} and {to_date}."

            lines = [f"Symptoms between {from_date} and {to_date}:"]
            for e in entries:
                severity = f" ({e['severity']})" if e.get("severity") else ""
                notes = f" — {e['notes']}" if e.get("notes") else ""
                lines.append(f"  • {e['occurred_at']}: {e['symptom_name']}{severity}{notes}")
            return "\n".join(lines)

        @tool
        async def fetch_supplements_in_range(from_date: str, to_date: str) -> str:
            """
            Fetch supplement entries active within a date range.
            from_date and to_date must be ISO date strings (YYYY-MM-DD).
            """
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{backend_url}/supplement-entries",
                    params={"from": from_date, "to": to_date},
                    timeout=10.0,
                )
                response.raise_for_status()
                entries = response.json()

            if not entries:
                return f"No supplements found between {from_date} and {to_date}."

            lines = [f"Supplements between {from_date} and {to_date}:"]
            for e in entries:
                stopped = f" (stopped {e['stopped_at']})" if e.get("stopped_at") else " (ongoing)"
                started = e.get("started_at", "unknown start")
                lines.append(f"  • {e['name']} {e['dosage']} {e['frequency']} — started {started}{stopped}")
            return "\n".join(lines)

        @tool
        async def search_documents(query: str) -> str:
            """
            Search across all uploaded health documents using semantic search.
            Useful for finding context that isn't captured in structured data.
            """
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{backend_url.replace(':8000', ':8001')}/query",
                    json={"question": query},
                    timeout=30.0,
                )
                response.raise_for_status()
                result = response.json()
            return result.get("answer", "No relevant documents found.")

        return [fetch_lab_results, fetch_symptoms_in_range, fetch_supplements_in_range, search_documents]

    async def analyze(
        self,
        question: str,
        config: RunnableConfig | None = None,
    ) -> dict:
        """
        Run a tool-calling loop to gather health data across multiple types,
        then reason over temporal patterns and correlations.
        """
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=question),
        ]

        while True:
            response = await self._llm_with_tools.ainvoke(messages, config=config)
            messages.append(response)

            if not response.tool_calls:
                break

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_fn = self._tools_by_name.get(tool_name)
                if tool_fn is None:
                    result = f"Unknown tool: {tool_name}"
                else:
                    try:
                        result = await tool_fn.ainvoke(tool_call["args"], config=config)
                    except Exception as e:
                        result = f"Tool error: {e}"
                        logger.warning(f"Tool call failed — tool={tool_name} error={e}")

                messages.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))

        return {"answer": response.content, "sources": []}
