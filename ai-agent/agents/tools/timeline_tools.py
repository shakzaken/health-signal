import httpx
from langchain_core.tools import tool


def make_fetch_timeline(backend_url: str, token: str):
    """Return a tool that fetches chronological health timeline events within a date range."""

    @tool
    async def fetch_timeline(from_date: str, to_date: str) -> str:
        """
        Fetch all health timeline events within a date range.
        Returns lab results, symptoms, and supplement changes in chronological order.
        from_date and to_date must be ISO date strings (YYYY-MM-DD).
        """
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{backend_url}/api/timeline",
                headers=headers,
                params={"from": from_date, "to": to_date},
                timeout=10.0,
            )
            response.raise_for_status()
            events = response.json()

        if not events:
            return f"No health events found between {from_date} and {to_date}."

        lines = [f"Health timeline from {from_date} to {to_date}:"]
        for e in sorted(events, key=lambda x: x["event_date"]):
            lines.append(f"  [{e['event_date']}] {e['event_type'].upper()}: {e['summary']}")
        return "\n".join(lines)

    return fetch_timeline
