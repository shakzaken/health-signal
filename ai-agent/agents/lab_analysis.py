from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables.config import RunnableConfig

from agents.tools.lab_tools import make_fetch_lab_results, make_get_marker_history
from core.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a personal health assistant specializing in lab result analysis.

You have access to the following tools:
- fetch_lab_results: retrieves the user's full lab history with all markers
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
        return [
            make_fetch_lab_results(self._backend_url),
            make_get_marker_history(self._backend_url),
        ]

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
