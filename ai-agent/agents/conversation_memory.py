"""
ConversationMemory — manages loading, saving, and summarising conversation
history via the backend HTTP API.

Extracted from Supervisor so each concern is independently testable.
"""

import httpx
from langchain_core.runnables.config import RunnableConfig

from core.logger import get_logger

logger = get_logger(__name__)


class ConversationMemory:
    """Handles all backend I/O for a single conversation session."""

    def __init__(self, backend_url: str, token: str) -> None:
        self._backend_url = backend_url
        self._token = token

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"} if self._token else {}

    async def load(self, session_id: str, user_id: str) -> tuple[str, list[dict]]:
        """Load the rolling summary + recent messages from the backend.

        Returns (summary, recent_history).  On failure returns ("", []) so the
        caller can continue without history rather than crashing.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._backend_url}/api/conversations/{session_id}",
                    headers=self._headers,
                    params={"recent": 6},
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

    async def save_turn(
        self, session_id: str, user_id: str, question: str, answer: str
    ) -> int:
        """Append the user question and assistant answer to the backend.

        Returns the new total message count (used to decide whether to summarise).
        """
        total = 0
        try:
            async with httpx.AsyncClient() as client:
                for role, content in [("user", question), ("assistant", answer)]:
                    resp = await client.post(
                        f"{self._backend_url}/api/conversations/{session_id}/messages",
                        json={"role": role, "content": content},
                        headers=self._headers,
                        timeout=10.0,
                    )
                    resp.raise_for_status()
                count_resp = await client.get(
                    f"{self._backend_url}/api/conversations/{session_id}",
                    headers=self._headers,
                    params={"recent": 0},
                    timeout=10.0,
                )
                count_resp.raise_for_status()
                total = count_resp.json().get("total_count", 0)
        except Exception as e:
            logger.warning(f"Could not save conversation turn — session={session_id} error={e}")
        return total

    async def maybe_summarize(
        self,
        session_id: str,
        user_id: str,
        total_count: int,
        compress_threshold: int,
        config: RunnableConfig,
        summarize_fn,
    ) -> None:
        """If total_count exceeds the threshold, compress old messages into a new summary.

        ``summarize_fn`` is a coroutine that accepts a transcript string and
        returns a summary string — injected to avoid a circular dependency on
        DoctorReportAgent.
        """
        if total_count <= compress_threshold:
            return
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._backend_url}/api/conversations/{session_id}/to-compress",
                    headers=self._headers,
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
            new_summary = await summarize_fn(transcript, config=config)
            async with httpx.AsyncClient() as client:
                await client.put(
                    f"{self._backend_url}/api/conversations/{session_id}/summary",
                    json={"summary": new_summary},
                    headers=self._headers,
                    timeout=10.0,
                )
            logger.info(f"Conversation summarized — session={session_id}")
        except Exception as e:
            logger.warning(f"Could not summarize conversation — session={session_id} error={e}")
