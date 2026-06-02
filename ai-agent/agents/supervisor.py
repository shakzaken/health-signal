from typing import Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langsmith import traceable
from pydantic import BaseModel
from typing_extensions import TypedDict

from agents.lab_analysis import LabAnalysisAgent
from core.logger import get_logger
from rag.query_chain import QueryChain

logger = get_logger(__name__)

CLASSIFY_PROMPT = """You are a routing assistant for a personal health AI.

Classify the user's question into one of two categories:

- "lab_analysis" — the question is about lab test results, blood markers, trends over time,
  reference ranges, or comparisons between tests (e.g. "what is my hemoglobin?",
  "is my cholesterol getting worse?", "what changed in my last blood test?")

- "rag" — the question is general, about symptoms, diet, supplements, doctor notes,
  or anything that is not specifically about structured lab marker values

Return only the category name, nothing else.
"""


class RouteDecision(BaseModel):
    route: Literal["lab_analysis", "rag"]


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
    it to the appropriate agent:
      - lab_analysis → LabAnalysisAgent (structured PostgreSQL data)
      - rag           → QueryChain (semantic Qdrant search)
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
        self._graph = self._build_graph()

    # ── Graph nodes ──────────────────────────────────────────────────────────

    async def _classify(self, state: AgentState) -> AgentState:
        """Classify the question and set the route."""
        classifier = self._llm.with_structured_output(RouteDecision)
        messages = [
            SystemMessage(content=CLASSIFY_PROMPT),
            HumanMessage(content=state["question"]),
        ]
        try:
            decision: RouteDecision = await classifier.ainvoke(messages)
            route = decision.route
        except Exception:
            route = "rag"  # safe fallback
        logger.info(f"Supervisor classified question → route={route}")
        return {**state, "route": route}

    async def _run_lab_analysis(self, state: AgentState) -> AgentState:
        """Run the Lab Analysis Agent."""
        result = await self._lab_agent.analyze(question=state["question"])
        return {**state, "answer": result["answer"], "sources": result["sources"]}

    async def _run_rag(self, state: AgentState) -> AgentState:
        """Run the RAG chain."""
        result = await self._rag_chain.answer(
            question=state["question"],
            user_id=state["user_id"],
            document_type=state["document_type"],
        )
        return {**state, "answer": result["answer"], "sources": result["sources"]}

    # ── Routing edge ─────────────────────────────────────────────────────────

    def _route(self, state: AgentState) -> Literal["lab_analysis", "rag"]:
        return state["route"]

    # ── Graph assembly ────────────────────────────────────────────────────────

    def _build_graph(self):
        graph = StateGraph(AgentState)

        graph.add_node("classify", self._classify)
        graph.add_node("lab_analysis", self._run_lab_analysis)
        graph.add_node("rag", self._run_rag)

        graph.set_entry_point("classify")
        graph.add_conditional_edges(
            "classify",
            self._route,
            {"lab_analysis": "lab_analysis", "rag": "rag"},
        )
        graph.add_edge("lab_analysis", END)
        graph.add_edge("rag", END)

        return graph.compile()

    # ── Public API ────────────────────────────────────────────────────────────

    @traceable(name="supervisor")
    async def run(
        self,
        question: str,
        user_id: str = "default",
        document_type: str | None = None,
    ) -> dict:
        """Route the question to the right agent and return the answer."""
        initial_state: AgentState = {
            "question": question,
            "user_id": user_id,
            "document_type": document_type,
            "answer": "",
            "sources": [],
            "route": "",
        }
        final_state = await self._graph.ainvoke(initial_state)
        return {
            "answer": final_state["answer"],
            "sources": final_state["sources"],
        }
