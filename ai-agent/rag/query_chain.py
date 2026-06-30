from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig

from core.guardrails import SAFETY_INSTRUCTION
from core.language import is_english
from core.logger import get_logger
from rag.retriever import Retriever

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a personal health assistant helping a user understand their health data.

You have access to:
1. The user's uploaded health documents (blood tests, lab results, doctor notes, symptom logs, supplement records)
2. The conversation history with the user (shown as prior messages in this conversation)

Guidelines:
- Use BOTH the conversation history and the health documents to answer questions
- If the user stated something earlier in the conversation (e.g. a preference, a fact about themselves), you can and should refer to it
- Explain health findings in clear, simple language
- Always present information as observations, not medical diagnoses
- Highlight trends and changes over time when relevant
- Suggest questions to ask a doctor when appropriate
- Be calm and factual — avoid alarmist language
- If neither the conversation history nor the health documents contain enough information to answer, say so clearly
- Always answer in the same language the user asked the question in
""" + SAFETY_INSTRUCTION

TRANSLATE_TO_ENGLISH_PROMPT = """You are a translator. Translate the following text to English.
Return only the translated text, nothing else."""

NO_RELEVANT_DOCUMENTS_MESSAGE = (
    "I couldn't find relevant information in your uploaded documents to answer that question."
)


class QueryChain:
    """
    RAG query chain: retrieve relevant chunks from Qdrant, then generate
    an answer with the LLM using those chunks as context.

    The corpus is mixed-language (Hebrew Clalit PDFs + English journal/supplements).
    To handle all query/document language combinations we use dual retrieval:
      - Search Qdrant with the original query (catches same-language docs)
      - If the query is not English, also search with an English translation
        (catches English docs when asking in Hebrew)
      - Merge results by score, deduplicate, take top-K

    The final answer is always in the same language as the original question.
    """

    def __init__(self, retriever: Retriever, llm: BaseChatModel) -> None:
        self._retriever = retriever
        self._llm = llm

    async def _translate_to_english(self, text: str, config: RunnableConfig | None = None) -> str:
        """Translate text to English using the LLM."""
        messages = [
            SystemMessage(content=TRANSLATE_TO_ENGLISH_PROMPT),
            HumanMessage(content=text),
        ]
        response = await self._llm.ainvoke(messages, config=config)
        return response.content.strip()

    def _merge_chunks(self, primary: list[dict], secondary: list[dict], top_k: int) -> list[dict]:
        """Merge two chunk lists by score, deduplicate by chunk id, return top_k."""
        seen_ids: set[str] = set()
        merged: list[dict] = []
        for chunk in sorted(primary + secondary, key=lambda c: c.get("score", 0), reverse=True):
            chunk_id = chunk.get("id") or chunk.get("text", "")[:50]
            if chunk_id not in seen_ids:
                seen_ids.add(chunk_id)
                merged.append(chunk)
        return merged[:top_k]

    async def build_context(
        self,
        question: str,
        user_id: str = "",
        document_type: str | None = None,
        summary: str = "",
        recent_history: list[dict] | None = None,
        config: RunnableConfig | None = None,
    ) -> dict:
        """Build the prompt messages and retrieve chunks, WITHOUT calling the LLM.
        Returns {"messages": [...], "sources": [...], "no_context": bool} for the
        caller to either invoke or stream the LLM."""
        primary_chunks = await self._retriever.retrieve(
            question, user_id=user_id, document_type=document_type
        )

        # Dual retrieval: if the query is not English, also search with an English
        # translation so Hebrew queries can find English journal/supplement documents.
        question_is_english = is_english(question)
        if not question_is_english:
            try:
                english_query = await self._translate_to_english(question, config=config)
                logger.debug(f"Dual retrieval — translated query: {english_query[:80]}")
                secondary_chunks = await self._retriever.retrieve(
                    english_query, user_id=user_id, document_type=document_type
                )
                chunks = self._merge_chunks(primary_chunks, secondary_chunks, top_k=5)
            except Exception as e:
                logger.error(f"Translation for dual retrieval failed — {e}")
                chunks = primary_chunks
        else:
            chunks = primary_chunks

        messages: list[BaseMessage] = [SystemMessage(content=SYSTEM_PROMPT)]
        has_history = bool(recent_history or summary)

        if summary:
            messages.append(SystemMessage(content=f"Summary of earlier conversation:\n{summary}"))

        for msg in (recent_history or []):
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))

        if not chunks and not has_history:
            # Return empty sources with no_context flag — callers use NO_RELEVANT_DOCUMENTS_MESSAGE
            messages.append(HumanMessage(content=question))
            return {"messages": messages, "sources": [], "no_context": True}

        # Explicitly tell the LLM when there is NO prior conversation history.
        # Without this, it may hallucinate a conversation from document content.
        if not has_history:
            messages.append(SystemMessage(
                content=(
                    "IMPORTANT: This is the very start of a new conversation. "
                    "There is NO prior conversation history between you and the user. "
                    "If the user asks what you were previously discussing, or refers to any "
                    "earlier exchange, tell them clearly that this is a brand-new session "
                    "with no previous context."
                )
            ))

        # Add document context as a system message (if any) so the LLM can use
        # BOTH the conversation history AND the retrieved chunks independently.
        if chunks:
            context = "\n\n---\n\n".join(
                f"[{c['document_type']} | {c['source_date'] or 'unknown date'} | {c['filename']}]\n{c['text']}"
                for c in chunks
            )
            messages.append(
                SystemMessage(content=f"Relevant context from the user's health documents:\n\n{context}")
            )

        # Language enforcement: detect the question language and require the reply
        # to match.  This must be placed immediately before the question so the
        # instruction is as prominent as possible, overriding any language influence
        # from Hebrew document chunks.
        if question_is_english:
            messages.append(SystemMessage(
                content=(
                    "CRITICAL: The user's question is in English. "
                    "You MUST reply in English only. "
                    "Do NOT switch to Hebrew or any other language, "
                    "even if the retrieved document excerpts are written in Hebrew."
                )
            ))
        else:
            messages.append(SystemMessage(
                content=(
                    "CRITICAL: The user's question is NOT in English. "
                    "You MUST reply in the same language as the user's question. "
                    "Do NOT switch to English."
                )
            ))

        messages.append(HumanMessage(content=question))
        return {"messages": messages, "sources": chunks, "no_context": False}

    async def answer(
        self,
        question: str,
        user_id: str = "",
        document_type: str | None = None,
        summary: str = "",
        recent_history: list[dict] | None = None,
        config: RunnableConfig | None = None,
    ) -> dict:
        """
        1. Retrieve chunks using the original question.
        2. If query is not English, also retrieve with an English translation and merge.
        3. Build context string from merged chunks.
        4. Call the LLM with context + conversation history + original question.
        5. Return answer text and source chunks.

        config is threaded through every LLM call so all spans appear nested
        under the parent trace in LangSmith.
        """
        ctx = await self.build_context(
            question,
            user_id=user_id,
            document_type=document_type,
            summary=summary,
            recent_history=recent_history,
            config=config,
        )
        if ctx.get("no_context"):
            return {"answer": NO_RELEVANT_DOCUMENTS_MESSAGE, "sources": []}
        response = await self._llm.ainvoke(ctx["messages"], config=config)
        return {"answer": response.content, "sources": ctx["sources"]}
