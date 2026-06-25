from langchain_core.tools import tool

from rag.retriever import Retriever


def make_search_documents(retriever: Retriever, user_id: str):
    """Return a tool that searches uploaded health documents via the Retriever directly."""

    @tool
    async def search_documents(query: str) -> str:
        """
        Search across all uploaded health documents using semantic search.
        Useful for finding context that isn't captured in structured data —
        e.g. diary entries, doctor notes, lifestyle descriptions.
        """
        chunks = await retriever.retrieve(query=query, user_id=user_id)
        if not chunks:
            return "No relevant documents found."
        lines = []
        for chunk in chunks:
            source = chunk.get("filename") or chunk.get("document_type") or "document"
            date = chunk.get("source_date", "")
            header = f"[{source}{', ' + date if date else ''}]"
            lines.append(f"{header}\n{chunk['text']}")
        return "\n\n---\n\n".join(lines)

    return search_documents
