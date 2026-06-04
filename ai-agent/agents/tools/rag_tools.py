import httpx
from langchain_core.tools import tool


def make_search_documents(ai_agent_url: str):
    """Return a tool that performs semantic search across uploaded health documents."""

    @tool
    async def search_documents(query: str) -> str:
        """
        Search across all uploaded health documents using semantic search.
        Useful for finding context that isn't captured in structured data.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{ai_agent_url}/query",
                json={"question": query},
                timeout=30.0,
            )
            response.raise_for_status()
            result = response.json()
        return result.get("answer", "No relevant documents found.")

    return search_documents
