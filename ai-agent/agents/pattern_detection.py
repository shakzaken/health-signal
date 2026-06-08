from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from agents.agent_state import SubAgentState, language_enforcement_message
from agents.graph_factory import create_tool_calling_graph
from agents.tools.lab_tools import make_fetch_lab_results
from agents.tools.rag_tools import make_search_documents
from agents.tools.supplement_tools import make_fetch_supplements_in_range
from agents.tools.symptom_tools import make_fetch_symptoms_in_range

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
    LangGraph-based agent for detecting temporal patterns across lab results,
    symptoms, and supplements. Exposes a compiled subgraph the supervisor invokes directly.
    """

    def __init__(self, llm: BaseChatModel, backend_url: str, token: str = "") -> None:
        # search_documents calls the ai-agent query endpoint, not the backend
        ai_agent_url = backend_url.replace(":8000", ":8001")
        tools = [
            make_fetch_lab_results(backend_url, token),
            make_fetch_symptoms_in_range(backend_url, token),
            make_fetch_supplements_in_range(backend_url, token),
            make_search_documents(ai_agent_url, token),
        ]
        self.graph: CompiledStateGraph = create_tool_calling_graph(llm, tools)

    def initial_state(
        self,
        question: str,
        summary: str = "",
        recent_history: list[dict] | None = None,
    ) -> SubAgentState:
        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        if summary:
            messages.append(SystemMessage(content=f"Conversation context (summary of earlier turns):\n{summary}"))
        for msg in (recent_history or []):
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
        messages.append(language_enforcement_message(question))
        messages.append(HumanMessage(content=question))
        return {"messages": messages, "sources": []}

    async def analyze(self, question: str, config: RunnableConfig | None = None) -> dict:
        final_state = await self.graph.ainvoke(self.initial_state(question), config=config)
        return {"answer": final_state["messages"][-1].content, "sources": final_state["sources"]}
