from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from agents.agent_state import SubAgentState, language_enforcement_message
from agents.graph_factory import create_tool_calling_graph
from agents.tools.lab_tools import make_fetch_lab_results
from agents.tools.supplement_tools import make_fetch_all_supplements
from agents.tools.timeline_tools import make_fetch_timeline

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
    LangGraph-based agent for synthesizing chronological health narratives.
    Exposes a compiled subgraph the supervisor invokes directly.
    """

    def __init__(self, llm: BaseChatModel, backend_url: str, token: str = "") -> None:
        tools = [
            make_fetch_timeline(backend_url, token),
            make_fetch_lab_results(backend_url, token),
            make_fetch_all_supplements(backend_url, token),
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

    async def summarize(self, question: str, config: RunnableConfig | None = None) -> dict:
        final_state = await self.graph.ainvoke(self.initial_state(question), config=config)
        return {"answer": final_state["messages"][-1].content, "sources": final_state["sources"]}
