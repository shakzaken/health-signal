from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import traceable

from rag.retriever import Retriever

SYSTEM_PROMPT = """You are a personal health assistant helping a user understand their health data.

You have access to the user's uploaded health documents including blood tests, lab results,
doctor notes, symptom logs, and supplement records.

Guidelines:
- Explain findings in clear, simple language
- Always present information as observations, not medical diagnoses
- Highlight trends and changes over time when relevant
- Suggest questions to ask a doctor when appropriate
- Be calm and factual — avoid alarmist language
- If the context does not contain enough information to answer, say so clearly
- Always answer in the same language the user asked the question in
"""

TRANSLATE_TO_HEBREW_PROMPT = """You are a translator. Translate the following question to Hebrew.
Return only the translated text, nothing else."""


class QueryChain:
    """
    RAG query chain: retrieve relevant chunks from Qdrant, then generate
    an answer with the LLM using those chunks as context.

    All documents are stored in Hebrew in the vector store.
    If the user's question is in English, it is translated to Hebrew before
    retrieval so that embedding similarity is meaningful.
    The final answer is always in the same language as the original question.
    """

    def __init__(self, retriever: Retriever, llm: BaseChatModel) -> None:
        self._retriever = retriever
        self._llm = llm

    async def _translate_to_hebrew(self, text: str) -> str:
        """Translate text to Hebrew using the LLM."""
        messages = [
            SystemMessage(content=TRANSLATE_TO_HEBREW_PROMPT),
            HumanMessage(content=text),
        ]
        response = await self._llm.ainvoke(messages)
        return response.content.strip()

    def _is_english(self, text: str) -> bool:
        """Return True if the text is predominantly ASCII (English)."""
        ascii_chars = sum(1 for c in text if ord(c) < 128 and c.isalpha())
        total_alpha = sum(1 for c in text if c.isalpha())
        if total_alpha == 0:
            return True
        return (ascii_chars / total_alpha) > 0.8

    @traceable(name="rag_query_chain")
    async def answer(
        self,
        question: str,
        user_id: str = "default",
        document_type: str | None = None,
    ) -> dict:
        """
        1. If the question is in English, translate it to Hebrew for retrieval.
        2. Retrieve relevant chunks from Qdrant using the Hebrew query.
        3. Build context string from retrieved chunks.
        4. Call the LLM with context + original question (answer in user's language).
        5. Return answer text and source chunks.
        """
        retrieval_query = question
        if self._is_english(question):
            retrieval_query = await self._translate_to_hebrew(question)

        chunks = self._retriever.retrieve(
            retrieval_query, user_id=user_id, document_type=document_type
        )

        if not chunks:
            return {
                "answer": "I couldn't find relevant information in your uploaded documents to answer that question.",
                "sources": [],
            }

        context = "\n\n---\n\n".join(
            f"[{c['document_type']} | {c['source_date'] or 'unknown date'} | {c['filename']}]\n{c['text']}"
            for c in chunks
        )

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=f"Context from the user's health documents:\n\n{context}\n\nQuestion: {question}"
            ),
        ]

        response = await self._llm.ainvoke(messages)

        return {
            "answer": response.content,
            "sources": chunks,
        }
