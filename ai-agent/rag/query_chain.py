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
"""


class QueryChain:
    """
    RAG query chain: retrieve relevant chunks from Qdrant, then generate
    an answer with the LLM using those chunks as context.
    """

    def __init__(self, retriever: Retriever, llm: BaseChatModel) -> None:
        self._retriever = retriever
        self._llm = llm

    @traceable(name="rag_query_chain")
    async def answer(
        self,
        question: str,
        user_id: str = "default",
        document_type: str | None = None,
    ) -> dict:
        """
        1. Retrieve relevant chunks from Qdrant (filtered by user).
        2. Build context string from retrieved chunks.
        3. Call the LLM with context + question.
        4. Return answer text and source chunks.
        """
        chunks = self._retriever.retrieve(
            question, user_id=user_id, document_type=document_type
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
