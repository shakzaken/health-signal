import httpx
from langchain_core.tools import tool


def make_fetch_supplements_in_range(backend_url: str, token: str):
    """Return a tool that fetches supplement entries active within a date range."""

    @tool
    async def fetch_supplements_in_range(from_date: str, to_date: str) -> str:
        """
        Fetch supplement entries active within a date range.
        from_date and to_date must be ISO date strings (YYYY-MM-DD).
        """
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{backend_url}/api/supplement-entries",
                headers=headers,
                params={"from": from_date, "to": to_date},
                timeout=10.0,
            )
            response.raise_for_status()
            entries = response.json()

        if not entries:
            return f"No supplements found between {from_date} and {to_date}."

        lines = [f"Supplements between {from_date} and {to_date}:"]
        for e in entries:
            stopped = f" (stopped {e['stopped_at']})" if e.get("stopped_at") else " (ongoing)"
            started = e.get("started_at", "unknown start")
            lines.append(f"  • {e['name']} {e['dosage']} {e['frequency']} — started {started}{stopped}")
        return "\n".join(lines)

    return fetch_supplements_in_range


def make_fetch_all_supplements(backend_url: str, token: str):
    """Return a tool that fetches every supplement entry with full detail."""

    @tool
    async def fetch_all_supplements() -> str:
        """Fetch all supplement entries with their start dates, stop dates, and reasons."""
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{backend_url}/api/supplement-entries", headers=headers, timeout=10.0
            )
            response.raise_for_status()
            entries = response.json()

        if not entries:
            return "No supplement entries found."

        lines = ["All supplements:"]
        for e in entries:
            started = e.get("started_at", "unknown")
            stopped = f" — stopped {e['stopped_at']}" if e.get("stopped_at") else " (ongoing)"
            notes = f" | reason: {e['notes']}" if e.get("notes") else ""
            lines.append(f"  • {e['name']} {e['dosage']} {e['frequency']} — started {started}{stopped}{notes}")
        return "\n".join(lines)

    return fetch_all_supplements
