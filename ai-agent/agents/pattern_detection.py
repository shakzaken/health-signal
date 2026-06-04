from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables.config import RunnableConfig

from agents.tools.lab_tools import make_fetch_lab_results
from agents.tools.rag_tools import make_search_documents
from agents.tools.supplement_tools import make_fetch_supplements_in_range
from agents.tools.symptom_tools import make_fetch_symptoms_in_range
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
        # search_documents calls the ai-agent query endpoint, not the backend
        ai_agent_url = self._backend_url.replace(":8000", ":8001")
        return [
            make_fetch_lab_results(self._backend_url),
            make_fetch_symptoms_in_range(self._backend_url),
            make_fetch_supplements_in_range(self._backend_url),
            make_search_documents(ai_agent_url),
        ]

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
