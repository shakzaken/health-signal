import asyncio
import json
from typing import AsyncGenerator, Literal, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tracers.langchain import LangChainTracer
from langgraph.graph import END, StateGraph
from pydantic import BaseModel
from typing_extensions import TypedDict

from agents.conversation_memory import ConversationMemory
from agents.doctor_report import DoctorReportAgent
from agents.lab_analysis import LabAnalysisAgent
from agents.pattern_detection import PatternDetectionAgent
from agents.timeline import TimelineAgent
from core.logger import get_logger
from rag.query_chain import NO_RELEVANT_DOCUMENTS_MESSAGE, QueryChain
from rag.retriever import Retriever

logger = get_logger(__name__)

# 14 messages = ~7 back-and-forth turns.
# At this point the context is long enough that older turns dilute relevance
# more than they add value.
COMPRESS_THRESHOLD = 14

CLASSIFY_PROMPT = """You are a routing assistant for a personal health AI.

Classify the user's question into one of five categories:

- "lab_analysis" — the question is about specific lab test results, blood markers, their numeric values,
  reference ranges, or trends for a single marker over time
  (e.g. "what is my hemoglobin?", "is my cholesterol getting worse?", "what changed in my last blood test?")
  NOTE: questions about supplement *dosage*, *dose changes*, or *when a supplement was started/stopped*
  are NOT lab_analysis — they belong to "timeline" or "rag"

- "pattern_detection" — the question asks about correlations, causes, or patterns across different
  types of health data (labs, symptoms, supplements) over time; OR asks how a symptom or feeling
  changed over time; OR asks about the impact of a lifestyle event (work stress, exercise, diet)
  on health symptoms or energy
  (e.g. "why was I so tired in January?", "did my fatigue correlate with low Vitamin D?",
  "what patterns do you see in my health data?", "did anything change after I started the supplement?",
  "did my morning stiffness change over time?", "how did my energy levels change?",
  "did my symptoms improve after starting supplements?", "was there a relationship between X and Y?",
  "what happened to my health during a stressful period?", "did work stress affect my symptoms?",
  "what changed when I started exercising / changed my diet?")

- "timeline" — the question asks for a summary or chronological overview of health events
  over a period of time, OR asks when something started/stopped/happened, OR asks about
  current status of supplements (what am I taking now, what do I take currently)
  (e.g. "what happened to my health in the last 6 months?", "give me a health summary for 2024",
  "what health events happened around March?", "summarize my health history",
  "when did I start taking supplements?", "when did I stop iron?", "what supplements did I take and when?",
  "what supplements am I currently taking?", "what am I taking right now?", "are my supplements working?")

- "doctor_report" — the user wants to generate a structured report to bring to a doctor appointment,
  or wants a comprehensive health summary across all data types
  (e.g. "generate a doctor report", "prepare me for my appointment", "give me a full health summary",
  "what should I tell my doctor?")

- "rag" — the question is about the content of uploaded documents, doctor notes, diet, supplement
  dosage details, or anything that does not fit the above categories
  (e.g. "what did my doctor say about my diet?", "what does my journal say about brain fog?",
  "what dose of vitamin D am I taking?", "did my supplement dose change?", "why did I start fish oil?")

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
        retriever: Retriever,
        backend_url: str,
        token: str = "",
    ) -> None:
        if not token:
            logger.warning(
                "Supervisor constructed without a token — all backend calls will fail silently."
            )
        self._llm = llm
        self._rag_chain = rag_chain
        self._retriever = retriever
        self._backend_url = backend_url
        self._token = token
        self._memory = ConversationMemory(backend_url=backend_url, token=token)
        self._lab_agent = LabAnalysisAgent(llm=llm, backend_url=backend_url, token=token)
        self._doctor_agent = DoctorReportAgent(llm=llm, backend_url=backend_url, token=token)
        self._graph = self._build_graph()
        # Keep strong references to background tasks so CPython doesn't GC them
        # before they complete (see asyncio docs on create_task).
        self._background_tasks: set[asyncio.Task] = set()

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
        except Exception as e:
            logger.error(f"Supervisor classification failed, falling back to rag — {e}")
            route = "rag"
        logger.info(f"Supervisor classified question → route={route}")
        return {**state, "route": route}

    async def _run_sub_agent(
        self,
        state: AgentState,
        config: RunnableConfig,
        agent,
        run_name: str,
    ) -> AgentState:
        """Invoke a sub-agent graph and merge its output back into the supervisor state."""
        agent_config: RunnableConfig = {
            **config,
            "run_name": run_name,
            "tags": config.get("tags", []) + [run_name],
        }
        final = await agent.graph.ainvoke(
            agent.initial_state(state["question"], state["summary"], state["recent_history"]),
            config=agent_config,
        )
        return {**state, "answer": final["messages"][-1].content, "sources": final["sources"]}

    async def _run_lab_analysis(self, state: AgentState, config: RunnableConfig) -> AgentState:
        return await self._run_sub_agent(state, config, self._lab_agent, "lab_analysis_agent")

    async def _run_pattern_detection(self, state: AgentState, config: RunnableConfig) -> AgentState:
        pattern_agent = PatternDetectionAgent(
            llm=self._llm,
            backend_url=self._backend_url,
            retriever=self._retriever,
            user_id=state["user_id"],
            token=self._token,
        )
        return await self._run_sub_agent(state, config, pattern_agent, "pattern_detection_agent")

    async def _run_timeline(self, state: AgentState, config: RunnableConfig) -> AgentState:
        timeline_agent = TimelineAgent(
            llm=self._llm,
            backend_url=self._backend_url,
            retriever=self._retriever,
            user_id=state["user_id"],
            token=self._token,
        )
        return await self._run_sub_agent(state, config, timeline_agent, "timeline_agent")

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

    # ── Background task helper ────────────────────────────────────────────────

    def _schedule_summarize(
        self,
        session_id: str,
        user_id: str,
        total_count: int,
        config: RunnableConfig,
    ) -> None:
        """Fire-and-forget summarisation task with a tracked reference."""
        task = asyncio.create_task(
            self._memory.maybe_summarize(
                session_id=session_id,
                user_id=user_id,
                total_count=total_count,
                compress_threshold=COMPRESS_THRESHOLD,
                config=config,
                summarize_fn=self._doctor_agent.summarize_conversation,
            )
        )
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    # ── Public API ────────────────────────────────────────────────────────────

    async def run(
        self,
        question: str,
        user_id: str = "",
        session_id: Optional[str] = None,
        document_type: Optional[str] = None,
    ) -> dict:
        config: RunnableConfig = {
            "callbacks": [LangChainTracer()],
            "run_name": "supervisor",
            "metadata": {
                "user_id": user_id,
                "session_id": str(session_id) if session_id else None,
            },
            "tags": ["supervisor"],
        }

        # Load conversation history if session_id provided
        summary, recent_history = "", []
        if session_id:
            summary, recent_history = await self._memory.load(session_id, user_id)

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
            total_count = await self._memory.save_turn(session_id, user_id, question, answer)
            if total_count > COMPRESS_THRESHOLD:
                self._schedule_summarize(session_id, user_id, total_count, config)

        return {
            "answer": answer,
            "sources": final_state["sources"],
        }

    async def run_stream(
        self,
        question: str,
        user_id: str = "",
        session_id: Optional[str] = None,
        document_type: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream the answer as SSE-formatted data lines.
        Yields strings of the form 'data: {json}\\n\\n'.
        Token events: {"token": "..."}
        Sources event (last): {"sources": [...]}
        """
        # Load conversation history
        summary, recent_history = "", []
        if session_id:
            summary, recent_history = await self._memory.load(session_id, user_id)

        # Classify the question (fast, non-streaming) — use a lightweight config for this call
        pre_state: AgentState = {
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
        classify_config: RunnableConfig = {
            "callbacks": [LangChainTracer()],
            "run_name": "supervisor_classify",
            "metadata": {"user_id": user_id, "session_id": str(session_id) if session_id else None},
            "tags": ["supervisor", "classify"],
        }
        classified = await self._classify(pre_state, classify_config)
        route = classified["route"]
        logger.info(f"Stream — classified route={route}")

        # Now build the main streaming config with route known
        config: RunnableConfig = {
            "callbacks": [LangChainTracer()],
            "run_name": "supervisor_stream",
            "metadata": {
                "user_id": user_id,
                "session_id": str(session_id) if session_id else None,
                "route": route,
            },
            "tags": ["supervisor_stream", route],
        }

        answer_parts: list[str] = []
        sources: list[dict] = []

        if route == "rag":
            ctx = await self._rag_chain.build_context(
                question=question,
                user_id=user_id,
                document_type=document_type,
                summary=summary,
                recent_history=recent_history,
                config=config,
            )
            sources = ctx["sources"]
            if ctx.get("no_context"):
                yield f"data: {json.dumps({'token': NO_RELEVANT_DOCUMENTS_MESSAGE})}\n\n"
                answer_parts.append(NO_RELEVANT_DOCUMENTS_MESSAGE)
            else:
                async for chunk in self._llm.astream(ctx["messages"], config=config):
                    content = chunk.content
                    if isinstance(content, str) and content:
                        answer_parts.append(content)
                        yield f"data: {json.dumps({'token': content})}\n\n"

        elif route == "doctor_report":
            # Doctor report uses a complex sequential pipeline — run fully then stream
            result = await self._run_doctor_report(classified, config)
            full_answer = result["answer"]
            # Stream in chunks so the client sees progress
            chunk_size = 10
            for i in range(0, len(full_answer), chunk_size):
                chunk = full_answer[i:i + chunk_size]
                answer_parts.append(chunk)
                yield f"data: {json.dumps({'token': chunk})}\n\n"
            sources = []

        else:
            # lab_analysis | pattern_detection | timeline
            pattern_agent = PatternDetectionAgent(
                llm=self._llm,
                backend_url=self._backend_url,
                retriever=self._retriever,
                user_id=user_id,
                token=self._token,
            )
            timeline_agent = TimelineAgent(
                llm=self._llm,
                backend_url=self._backend_url,
                retriever=self._retriever,
                user_id=user_id,
                token=self._token,
            )
            agent_map = {
                "lab_analysis": self._lab_agent,
                "pattern_detection": pattern_agent,
                "timeline": timeline_agent,
            }
            agent_run_names = {
                "lab_analysis": "lab_analysis_agent",
                "pattern_detection": "pattern_detection_agent",
                "timeline": "timeline_agent",
            }
            agent = agent_map[route]
            agent_state = agent.initial_state(question, summary, recent_history)
            agent_config: RunnableConfig = {
                **config,
                "run_name": agent_run_names[route],
                "tags": config.get("tags", []) + [agent_run_names[route]],
            }

            async for event in agent.graph.astream_events(
                agent_state, config=agent_config, version="v2"
            ):
                kind = event["event"]
                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    content = chunk.content
                    if isinstance(content, str) and content:
                        answer_parts.append(content)
                        yield f"data: {json.dumps({'token': content})}\n\n"
                elif kind == "on_chain_end":
                    # Capture sources from final agent state
                    output = event["data"].get("output")
                    if isinstance(output, dict) and "sources" in output:
                        sources = output["sources"]

        # Persist conversation turn
        answer = "".join(answer_parts)
        if session_id and answer:
            total_count = await self._memory.save_turn(session_id, user_id, question, answer)
            if total_count > COMPRESS_THRESHOLD:
                self._schedule_summarize(session_id, user_id, total_count, config)

        yield f"data: {json.dumps({'sources': sources})}\n\n"
