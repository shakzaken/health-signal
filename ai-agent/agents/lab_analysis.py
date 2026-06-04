import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import tool

from core.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a personal health assistant specializing in lab result analysis.

You have access to the following tools:
- fetch_all_lab_results: retrieves the user's full lab history with all markers
- get_marker_history: retrieves the historical values for a specific marker by name

Guidelines:
- Use tools to fetch the data you need before answering
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
    Uses LangChain tool calling to fetch lab data from the backend and answer
    questions about the user's lab history.

    The LLM decides which tools to call based on the question — either fetching
    all results or drilling into a specific marker's history.
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
        async def fetch_all_lab_results() -> str:
            """Fetch all lab test results with their markers from the database."""
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
        async def get_marker_history(marker_name: str) -> str:
            """Get historical values for a specific lab marker by name (e.g. 'Cholesterol', 'Hemoglobin')."""
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{backend_url}/lab-results/markers/{marker_name}/history",
                    timeout=10.0,
                )
                response.raise_for_status()
                history = response.json().get("history", [])

            if not history:
                return f"No historical data found for marker: {marker_name}"

            lines = [f"History for {marker_name}:"]
            for entry in history:
                ref = ""
                if entry.get("reference_low") is not None and entry.get("reference_high") is not None:
                    ref = f" (normal: {entry['reference_low']}–{entry['reference_high']})"
                status = f" [{entry['status']}]" if entry.get("status") else ""
                date_label = entry.get("test_date") or entry.get("created_at", "unknown date")
                lines.append(f"  • {date_label}: {entry['value']} {entry['unit']}{ref}{status}")
            return "\n".join(lines)

        return [fetch_all_lab_results, get_marker_history]

    async def analyze(
        self,
        question: str,
        config: RunnableConfig | None = None,
    ) -> dict:
        """
        Run a tool-calling loop: the LLM decides which tools to call,
        results are fed back, and the loop ends when the LLM produces a final answer.

        config is threaded through every LLM and tool call so all spans appear
        nested under the parent trace in LangSmith.
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
