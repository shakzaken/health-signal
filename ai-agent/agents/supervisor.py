from typing import Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tracers.langchain import LangChainTracer
from langgraph.graph import END, StateGraph
from pydantic import BaseModel
from typing_extensions import TypedDict

from agents.lab_analysis import LabAnalysisAgent
from agents.pattern_detection import PatternDetectionAgent
from agents.timeline import TimelineAgent
from core.logger import get_logger
from rag.query_chain import QueryChain

logger = get_logger(__name__)

CLASSIFY_PROMPT = """You are a routing assistant for a personal health AI.

Classify the user's question into one of four categories:

- "lab_analysis" — the question is about specific lab test results, blood markers, their values,
  reference ranges, or trends for a single marker over time
  (e.g. "what is my hemoglobin?", "is my cholesterol getting worse?", "what changed in my last blood test?")

- "pattern_detection" — the question asks about correlations, causes, or patterns across different
  types of health data (labs, symptoms, supplements) over time
  (e.g. "why was I so tired in January?", "did my fatigue correlate with low Vitamin D?",
  "what patterns do you see in my health data?", "did anything change after I started the supplement?")

- "timeline" — the question asks for a summary or chronological overview of health events
  over a period of time, OR asks when something started/stopped/happened
  (e.g. "what happened to my health in the last 6 months?", "give me a health summary for 2024",
  "what health events happened around March?", "summarize my health history",
  "when did I start taking supplements?", "when did I stop iron?", "what supplements did I take and when?")

- "rag" — the question is general, about the content of uploaded documents, doctor notes, diet,
  or anything that does not fit the above categories
  (e.g. "what did my doctor say about my diet?", "what does my journal say about brain fog?")

Return only the category name, nothing else.
"""


class RouteDecision(BaseModel):
    route: Literal["lab_analysis", "pattern_detection", "timeline", "rag"]


class AgentState(TypedDict):
    question: str
    user_id: str
    document_type: str | None
    answer: str
    sources: list[dict]
    route: str


class Supervisor:
    """
    LangGraph-based supervisor that classifies the user's question and routes
    it to the appropriate sub-agent graph:
      - lab_analysis      → LabAnalysisAgent subgraph
      - pattern_detection → PatternDetectionAgent subgraph
      - timeline          → TimelineAgent subgraph
      - rag               → QueryChain (semantic Qdrant search)

    Each sub-agent is a compiled LangGraph that the supervisor invokes directly,
    giving full end-to-end trace nesting in LangSmith.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        rag_chain: QueryChain,
        backend_url: str,
    ) -> None:
        self._llm = llm
        self._rag_chain = rag_chain
        self._lab_agent = LabAnalysisAgent(llm=llm, backend_url=backend_url)
        self._pattern_agent = PatternDetectionAgent(llm=llm, backend_url=backend_url)
        self._timeline_agent = TimelineAgent(llm=llm, backend_url=backend_url)
        self._graph = self._build_graph()

    # ── Graph nodes ──────────────────────────────────────────────────────────

    async def _classify(self, state: AgentState, config: RunnableConfig) -> AgentState:
        classifier = self._llm.with_structured_output(RouteDecision)
        messages = [
            SystemMessage(content=CLASSIFY_PROMPT),
            HumanMessage(content=state["question"]),
        ]
        try:
            decision: RouteDecision = await classifier.ainvoke(messages, config=config)
            route = decision.route
        except Exception:
            route = "rag"
        logger.info(f"Supervisor classified question → route={route}")
        return {**state, "route": route}

    async def _run_lab_analysis(self, state: AgentState, config: RunnableConfig) -> AgentState:
        final = await self._lab_agent.graph.ainvoke(
            self._lab_agent.initial_state(state["question"]), config=config
        )
        return {**state, "answer": final["messages"][-1].content, "sources": final["sources"]}

    async def _run_pattern_detection(self, state: AgentState, config: RunnableConfig) -> AgentState:
        final = await self._pattern_agent.graph.ainvoke(
            self._pattern_agent.initial_state(state["question"]), config=config
        )
        return {**state, "answer": final["messages"][-1].content, "sources": final["sources"]}

    async def _run_timeline(self, state: AgentState, config: RunnableConfig) -> AgentState:
        final = await self._timeline_agent.graph.ainvoke(
            self._timeline_agent.initial_state(state["question"]), config=config
        )
        return {**state, "answer": final["messages"][-1].content, "sources": final["sources"]}

    async def _run_rag(self, state: AgentState, config: RunnableConfig) -> AgentState:
        result = await self._rag_chain.answer(
            question=state["question"],
            user_id=state["user_id"],
            document_type=state["document_type"],
            config=config,
        )
        return {**state, "answer": result["answer"], "sources": result["sources"]}

    # ── Routing edge ─────────────────────────────────────────────────────────

    def _route(self, state: AgentState) -> Literal["lab_analysis", "pattern_detection", "timeline", "rag"]:
        return state["route"]

    # ── Graph assembly ────────────────────────────────────────────────────────

    def _build_graph(self):
        graph = StateGraph(AgentState)

        graph.add_node("classify", self._classify)
        graph.add_node("lab_analysis", self._run_lab_analysis)
        graph.add_node("pattern_detection", self._run_pattern_detection)
        graph.add_node("timeline", self._run_timeline)
        graph.add_node("rag", self._run_rag)

        graph.set_entry_point("classify")
        graph.add_conditional_edges(
            "classify",
            self._route,
            {
                "lab_analysis": "lab_analysis",
                "pattern_detection": "pattern_detection",
                "timeline": "timeline",
                "rag": "rag",
            },
        )
        graph.add_edge("lab_analysis", END)
        graph.add_edge("pattern_detection", END)
        graph.add_edge("timeline", END)
        graph.add_edge("rag", END)

        return graph.compile()

    # ── Public API ────────────────────────────────────────────────────────────

    async def run(
        self,
        question: str,
        user_id: str = "default",
        document_type: str | None = None,
    ) -> dict:
        initial_state: AgentState = {
            "question": question,
            "user_id": user_id,
            "document_type": document_type,
            "answer": "",
            "sources": [],
            "route": "",
        }
        config: RunnableConfig = {
            "callbacks": [LangChainTracer()],
            "run_name": "supervisor",
        }
        final_state = await self._graph.ainvoke(initial_state, config=config)
        return {
            "answer": final_state["answer"],
            "sources": final_state["sources"],
        }
