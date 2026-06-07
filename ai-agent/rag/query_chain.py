from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig

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
"""

TRANSLATE_TO_ENGLISH_PROMPT = """You are a translator. Translate the following text to English.
Return only the translated text, nothing else."""


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

    def _is_english(self, text: str) -> bool:
        """Return True if the text is predominantly ASCII alpha characters."""
        ascii_chars = sum(1 for c in text if ord(c) < 128 and c.isalpha())
        total_alpha = sum(1 for c in text if c.isalpha())
        if total_alpha == 0:
            return True
        return (ascii_chars / total_alpha) > 0.8

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

    async def answer(
        self,
        question: str,
        user_id: str = "default",
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
        primary_chunks = self._retriever.retrieve(
            question, user_id=user_id, document_type=document_type
        )

        # Dual retrieval: if the query is not English, also search with English translation
        # so Hebrew queries can find English journal/supplement documents
        if not self._is_english(question):
            try:
                english_query = await self._translate_to_english(question, config=config)
                logger.debug(f"Dual retrieval — translated query: {english_query[:80]}")
                secondary_chunks = self._retriever.retrieve(
                    english_query, user_id=user_id, document_type=document_type
                )
                chunks = self._merge_chunks(primary_chunks, secondary_chunks, top_k=5)
            except Exception as e:
                logger.warning(f"Translation for dual retrieval failed — {e}")
                chunks = primary_chunks
        else:
            chunks = primary_chunks

        # Build the message list — inject conversation history before the question
        messages: list = [SystemMessage(content=SYSTEM_PROMPT)]

        if summary:
            messages.append(SystemMessage(content=f"Summary of earlier conversation:\n{summary}"))

        for msg in (recent_history or []):
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))

        # No document chunks and no conversation history → nothing to answer from
        if not chunks and not (recent_history or summary):
            return {
                "answer": "I couldn't find relevant information in your uploaded documents to answer that question.",
                "sources": [],
            }

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

        # Current question always goes last as a plain HumanMessage
        messages.append(HumanMessage(content=question))

        response = await self._llm.ainvoke(messages, config=config)

        return {
            "answer": response.content,
            "sources": chunks,
        }
