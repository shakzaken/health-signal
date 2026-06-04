import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import tool

from core.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a personal health timeline assistant.

You have access to the following tools:
- fetch_timeline: retrieves a chronological list of health events (lab tests, symptoms, supplement changes) within a date range
- fetch_lab_results: retrieves full lab result details including all markers
- fetch_all_supplements: retrieves every supplement with start date, stop date, and reason

Your job is to synthesize a clear, chronological narrative of the user's health over a time period.

IMPORTANT — follow this sequence:
1. ALWAYS call fetch_lab_results FIRST. This reveals the actual dates of available data so you know what time range to request.
2. Based on those dates and the question, call fetch_timeline with a date range wide enough to cover all relevant events (e.g. if earliest test is 2025-06-14, use from_date at least 2 years before that to catch earlier events).
3. If the question is about supplements specifically, ALSO call fetch_all_supplements to get the complete structured supplement list.
4. For significant lab events in the timeline, the full marker details are already available from step 1.
5. Synthesize a clear chronological narrative from all collected data.

Additional guidelines:
- When asked about supplements, medications, or any intervention — list EVERY event found, not just the first one
- Present events in chronological order with clear dates
- Highlight what changed, what improved, what worsened
- Keep the tone calm, factual, and easy to understand
- Answer in the same language the user asked in
"""


class TimelineAgent:
    """
    Fetches timeline events from the backend and synthesizes a chronological
    health narrative over a requested time period.
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
        async def fetch_timeline(from_date: str, to_date: str) -> str:
            """
            Fetch all health timeline events within a date range.
            Returns lab results, symptoms, and supplement changes in chronological order.
            from_date and to_date must be ISO date strings (YYYY-MM-DD).
            """
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{backend_url}/timeline",
                    params={"from": from_date, "to": to_date},
                    timeout=10.0,
                )
                response.raise_for_status()
                events = response.json()

            if not events:
                return f"No health events found between {from_date} and {to_date}."

            lines = [f"Health timeline from {from_date} to {to_date}:"]
            for e in sorted(events, key=lambda x: x["event_date"]):
                lines.append(f"  [{e['event_date']}] {e['event_type'].upper()}: {e['summary']}")
            return "\n".join(lines)

        @tool
        async def fetch_lab_results() -> str:
            """Fetch all lab test results with their markers and dates for detailed context."""
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
        async def fetch_all_supplements() -> str:
            """Fetch all supplement entries with their start dates, stop dates, and reasons."""
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{backend_url}/supplement-entries", timeout=10.0)
                response.raise_for_status()
                entries = response.json()

            if not entries:
                return "No supplement entries found."

            lines = ["All supplements:"]
            for e in entries:
                started = e.get("started_at", "unknown")
                stopped = f" — stopped {e['stopped_at']}" if e.get("stopped_at") else " (ongoing)"
                notes = f" | reason: {e['notes']}" if e.get("notes") else ""
                lines.append(f"  • {e['name']} {e['dosage']} {e['frequency']} — started {started}{stopped}{notes}")
            return "\n".join(lines)

        return [fetch_timeline, fetch_lab_results, fetch_all_supplements]

    async def summarize(
        self,
        question: str,
        config: RunnableConfig | None = None,
    ) -> dict:
        """
        Run a tool-calling loop to gather timeline events and produce a
        chronological health narrative.
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
