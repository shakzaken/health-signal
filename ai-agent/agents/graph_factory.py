import asyncio
from typing import Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents.agent_state import SubAgentState
from core.logger import get_logger

logger = get_logger(__name__)

MAX_TOOL_STEPS = 10


def create_tool_calling_graph(
    llm: BaseChatModel,
    tools: list,
) -> CompiledStateGraph:
    """
    Build a compiled ReAct graph: call_model → should_continue → call_tools → loop.

    Differences from a raw while loop:
    - Parallel tool execution via asyncio.gather
    - Hard cap at MAX_TOOL_STEPS to prevent infinite loops
    - Full LangSmith trace nesting when invoked as a subgraph
    """
    llm_with_tools = llm.bind_tools(tools)
    tools_by_name = {t.name: t for t in tools}

    async def call_model(state: SubAgentState, config: RunnableConfig) -> dict:
        response = await llm_with_tools.ainvoke(state["messages"], config=config)
        return {"messages": [response]}

    def should_continue(
        state: SubAgentState,
    ) -> Literal["call_tools", "__end__"]:
        last = state["messages"][-1]
        if not (isinstance(last, AIMessage) and last.tool_calls):
            return END

        tool_steps = sum(
            1 for m in state["messages"]
            if isinstance(m, AIMessage) and m.tool_calls
        )
        if tool_steps >= MAX_TOOL_STEPS:
            logger.warning(f"Max tool steps ({MAX_TOOL_STEPS}) reached — forcing END")
            return END

        return "call_tools"

    async def call_tools(state: SubAgentState, config: RunnableConfig) -> dict:
        last = state["messages"][-1]

        async def invoke_one(tool_call: dict) -> ToolMessage:
            tool_fn = tools_by_name.get(tool_call["name"])
            if tool_fn is None:
                logger.warning(f"Unknown tool called: {tool_call['name']}")
                content = f"Unknown tool: {tool_call['name']}"
            else:
                try:
                    content = await tool_fn.ainvoke(tool_call["args"], config=config)
                except Exception as e:
                    logger.error(f"Tool error — tool={tool_call['name']} error={e}")
                    content = f"Tool error: {e}"
            return ToolMessage(content=str(content), tool_call_id=tool_call["id"])

        results = await asyncio.gather(*[invoke_one(tc) for tc in last.tool_calls])
        return {"messages": list(results)}

    graph = StateGraph(SubAgentState)
    graph.add_node("call_model", call_model)
    graph.add_node("call_tools", call_tools)
    graph.set_entry_point("call_model")
    graph.add_conditional_edges(
        "call_model",
        should_continue,
        {"call_tools": "call_tools", END: END},
    )
    graph.add_edge("call_tools", "call_model")

    return graph.compile()
