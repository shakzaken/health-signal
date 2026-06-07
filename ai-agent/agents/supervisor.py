import asyncio
import uuid
from typing import Literal, Optional

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tracers.langchain import LangChainTracer
from langgraph.graph import END, StateGraph
from pydantic import BaseModel
from typing_extensions import TypedDict

from agents.doctor_report import DoctorReportAgent
from agents.lab_analysis import LabAnalysisAgent
from agents.pattern_detection import PatternDetectionAgent
from agents.timeline import TimelineAgent
from core.logger import get_logger
from rag.query_chain import QueryChain

logger = get_logger(__name__)

COMPRESS_THRESHOLD = 14  # trigger summarization once total messages exceed this

CLASSIFY_PROMPT = """You are a routing assistant for a personal health AI.

Classify the user's question into one of five categories:

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

- "doctor_report" — the user wants to generate a structured report to bring to a doctor appointment,
  or wants a comprehensive health summary across all data types
  (e.g. "generate a doctor report", "prepare me for my appointment", "give me a full health summary",
  "what should I tell my doctor?")

- "rag" — the question is general, about the content of uploaded documents, doctor notes, diet,
  or anything that does not fit the above categories
  (e.g. "what did my doctor say about my diet?", "what does my journal say about brain fog?")

Return only the category name, nothing else.
"""


class RouteDecision(BaseModel):
    route: Literal["lab_analysis", "pattern_detection", "timeline", "doctor_report", "rag"]


class AgentState(TypedDict):
    question: str
    user_id: str
    session_id: Optional[str]
    summary: str                      # rolling summary of older conversation turns
    recent_history: list[dict]        # last N turns verbatim [{role, content}, ...]
    document_type: Optional[str]
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
      - doctor_report     → DoctorReportAgent sequential pipeline
      - rag               → QueryChain (semantic Qdrant search)

    Conversational memory:
      When a session_id is provided, the supervisor loads the rolling summary and
      recent message history from the backend, passes them to the sub-agent, saves
      the new turn, and triggers summarization if the message count crosses the threshold.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        rag_chain: QueryChain,
        backend_url: str,
    ) -> None:
        self._llm = llm
        self._rag_chain = rag_chain
        self._backend_url = backend_url
        self._lab_agent = LabAnalysisAgent(llm=llm, backend_url=backend_url)
        self._pattern_agent = PatternDetectionAgent(llm=llm, backend_url=backend_url)
        self._timeline_agent = TimelineAgent(llm=llm, backend_url=backend_url)
        self._doctor_agent = DoctorReportAgent(llm=llm, backend_url=backend_url)
        self._graph = self._build_graph()

    # ── Conversation history ──────────────────────────────────────────────────

    async def _load_history(self, session_id: str, user_id: str) -> tuple[str, list[dict]]:
        """Load the rolling summary + recent messages from the backend. Returns (summary, recent_history)."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._backend_url}/conversations/{session_id}",
                    params={"user_id": user_id, "recent": 6},
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()
            summary = data.get("summary") or ""
            recent_history = [
                {"role": m["role"], "content": m["content"]}
                for m in data.get("messages", [])
            ]
            return summary, recent_history
        except Exception as e:
            logger.warning(f"Could not load conversation history — session={session_id} error={e}")
            return "", []

    async def _save_turn(
        self, session_id: str, user_id: str, question: str, answer: str
    ) -> int:
        """Append the user question and assistant answer to the backend. Returns new total message count."""
        total = 0
        try:
            async with httpx.AsyncClient() as client:
                for role, content in [("user", question), ("assistant", answer)]:
                    resp = await client.post(
                        f"{self._backend_url}/conversations/{session_id}/messages",
                        json={"user_id": user_id, "role": role, "content": content},
                        timeout=10.0,
                    )
                    resp.raise_for_status()
                # get updated count
                count_resp = await client.get(
                    f"{self._backend_url}/conversations/{session_id}",
                    params={"user_id": user_id, "recent": 0},
                    timeout=10.0,
                )
                count_resp.raise_for_status()
                total = count_resp.json().get("total_count", 0)
        except Exception as e:
            logger.warning(f"Could not save conversation turn — session={session_id} error={e}")
        return total

    async def _maybe_summarize(
        self,
        session_id: str,
        user_id: str,
        total_count: int,
        config: RunnableConfig,
    ) -> None:
        """If total_count exceeds the threshold, fetch old messages and compress them into a new summary."""
        if total_count <= COMPRESS_THRESHOLD:
            return
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._backend_url}/conversations/{session_id}/to-compress",
                    params={"keep_last": 6},
                    timeout=10.0,
                )
                resp.raise_for_status()
                old_messages = resp.json().get("messages", [])

            if not old_messages:
                return

            transcript = "\n".join(
                f"{m['role'].upper()}: {m['content']}" for m in old_messages
            )
            new_summary = await self._doctor_agent.summarize_conversation(
                transcript, config=config
            )
            async with httpx.AsyncClient() as client:
                await client.put(
                    f"{self._backend_url}/conversations/{session_id}/summary",
                    json={"summary": new_summary},
                    timeout=10.0,
                )
            logger.info(f"Conversation summarized — session={session_id}")
        except Exception as e:
            logger.warning(f"Could not summarize conversation — session={session_id} error={e}")

    # ── Graph nodes ───────────────────────────────────────────────────────────

    async def _classify(self, state: AgentState, config: RunnableConfig) -> AgentState:
        classifier = self._llm.with_structured_output(RouteDecision)
        # include recent history context so follow-up questions are classified correctly
        history_context = ""
        if state["summary"]:
            history_context += f"\nConversation summary: {state['summary']}"
        if state["recent_history"]:
            recent = "\n".join(
                f"{m['role'].upper()}: {m['content']}" for m in state["recent_history"][-4:]
            )
            history_context += f"\nRecent exchanges:\n{recent}"

        user_message = state["question"]
        if history_context:
            user_message = f"{history_context}\n\nNew question: {state['question']}"

        messages = [
            SystemMessage(content=CLASSIFY_PROMPT),
            HumanMessage(content=user_message),
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
            self._lab_agent.initial_state(
                state["question"],
                summary=state["summary"],
                recent_history=state["recent_history"],
            ),
            config=config,
        )
        return {**state, "answer": final["messages"][-1].content, "sources": final["sources"]}

    async def _run_pattern_detection(self, state: AgentState, config: RunnableConfig) -> AgentState:
        final = await self._pattern_agent.graph.ainvoke(
            self._pattern_agent.initial_state(
                state["question"],
                summary=state["summary"],
                recent_history=state["recent_history"],
            ),
            config=config,
        )
        return {**state, "answer": final["messages"][-1].content, "sources": final["sources"]}

    async def _run_timeline(self, state: AgentState, config: RunnableConfig) -> AgentState:
        final = await self._timeline_agent.graph.ainvoke(
            self._timeline_agent.initial_state(
                state["question"],
                summary=state["summary"],
                recent_history=state["recent_history"],
            ),
            config=config,
        )
        return {**state, "answer": final["messages"][-1].content, "sources": final["sources"]}

    async def _run_doctor_report(self, state: AgentState, config: RunnableConfig) -> AgentState:
        # Build conversation context string from summary + recent history
        ctx_parts = []
        if state["summary"]:
            ctx_parts.append(f"Summary of earlier conversation: {state['summary']}")
        if state["recent_history"]:
            turns = "\n".join(
                f"{m['role'].upper()}: {m['content']}" for m in state["recent_history"]
            )
            ctx_parts.append(f"Recent turns:\n{turns}")
        conversation_context = "\n\n".join(ctx_parts)

        # Use a wider period when there is conversation context so the report covers relevant data
        period_days = 365 if conversation_context else 90

        result = await self._doctor_agent.generate(
            user_id=state["user_id"],
            period_days=period_days,
            conversation_context=conversation_context,
            config=config,
        )
        return {**state, "answer": result["report"], "sources": []}

    async def _run_rag(self, state: AgentState, config: RunnableConfig) -> AgentState:
        result = await self._rag_chain.answer(
            question=state["question"],
            user_id=state["user_id"],
            document_type=state["document_type"],
            summary=state["summary"],
            recent_history=state["recent_history"],
            config=config,
        )
        return {**state, "answer": result["answer"], "sources": result["sources"]}

    # ── Routing edge ──────────────────────────────────────────────────────────

    def _route(
        self, state: AgentState
    ) -> Literal["lab_analysis", "pattern_detection", "timeline", "doctor_report", "rag"]:
        return state["route"]

    # ── Graph assembly ────────────────────────────────────────────────────────

    def _build_graph(self):
        graph = StateGraph(AgentState)

        graph.add_node("classify", self._classify)
        graph.add_node("lab_analysis", self._run_lab_analysis)
        graph.add_node("pattern_detection", self._run_pattern_detection)
        graph.add_node("timeline", self._run_timeline)
        graph.add_node("doctor_report", self._run_doctor_report)
        graph.add_node("rag", self._run_rag)

        graph.set_entry_point("classify")
        graph.add_conditional_edges(
            "classify",
            self._route,
            {
                "lab_analysis": "lab_analysis",
                "pattern_detection": "pattern_detection",
                "timeline": "timeline",
                "doctor_report": "doctor_report",
                "rag": "rag",
            },
        )
        graph.add_edge("lab_analysis", END)
        graph.add_edge("pattern_detection", END)
        graph.add_edge("timeline", END)
        graph.add_edge("doctor_report", END)
        graph.add_edge("rag", END)

        return graph.compile()

    # ── Public API ────────────────────────────────────────────────────────────

    async def run(
        self,
        question: str,
        user_id: str = "default",
        session_id: Optional[str] = None,
        document_type: Optional[str] = None,
    ) -> dict:
        config: RunnableConfig = {
            "callbacks": [LangChainTracer()],
            "run_name": "supervisor",
        }

        # Load conversation history if session_id provided
        summary, recent_history = "", []
        if session_id:
            summary, recent_history = await self._load_history(session_id, user_id)

        initial_state: AgentState = {
            "question": question,
            "user_id": user_id,
            "session_id": session_id,
            "summary": summary,
            "recent_history": recent_history,
            "document_type": document_type,
            "answer": "",
            "sources": [],
            "route": "",
        }

        final_state = await self._graph.ainvoke(initial_state, config=config)
        answer = final_state["answer"]

        # Persist the turn and trigger summarization if needed
        if session_id:
            total_count = await self._save_turn(session_id, user_id, question, answer)
            if total_count > COMPRESS_THRESHOLD:
                asyncio.create_task(
                    self._maybe_summarize(session_id, user_id, total_count, config)
                )

        return {
            "answer": answer,
            "sources": final_state["sources"],
        }
