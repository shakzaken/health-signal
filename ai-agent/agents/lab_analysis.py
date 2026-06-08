from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from agents.agent_state import SubAgentState, language_enforcement_message
from agents.graph_factory import create_tool_calling_graph
from agents.tools.lab_tools import make_fetch_lab_results, make_get_marker_history

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
    LangGraph-based agent for answering questions about lab results.
    Exposes a compiled subgraph that the supervisor invokes directly.
    """

    def __init__(self, llm: BaseChatModel, backend_url: str, token: str = "") -> None:
        tools = [
            make_fetch_lab_results(backend_url, token),
            make_get_marker_history(backend_url, token),
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
