from typing import Annotated

from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from core.language import is_english


class SubAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    sources: list[dict]


def language_enforcement_message(question: str) -> SystemMessage:
    """
    Return a SystemMessage that enforces reply language matching the question.

    This is placed immediately before the final HumanMessage in every agent so
    it overrides any language influence from tool results (e.g. Hebrew document
    chunks retrieved from Qdrant).
    """
    if is_english(question):
        return SystemMessage(
            content=(
                "CRITICAL LANGUAGE RULE: The user's question is in English. "
                "You MUST write your entire response in English. "
                "Do NOT switch to Hebrew or any other language, "
                "even if tool results or document excerpts are in Hebrew."
            )
        )
    else:
        return SystemMessage(
            content=(
                "CRITICAL LANGUAGE RULE: The user's question is NOT in English. "
                "You MUST write your entire response in the same language as the question. "
                "Do NOT switch to English."
            )
        )
