import httpx
from langchain_core.tools import tool


def make_fetch_symptoms_in_range(backend_url: str, token: str):
    """Return a tool that fetches symptom entries within a date range."""

    @tool
    async def fetch_symptoms_in_range(from_date: str, to_date: str) -> str:
        """
        Fetch symptom entries within a date range.
        from_date and to_date must be ISO date strings (YYYY-MM-DD).
        """
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{backend_url}/api/symptom-entries",
                headers=headers,
                params={"from": from_date, "to": to_date},
                timeout=10.0,
            )
            response.raise_for_status()
            entries = response.json()

        if not entries:
            return f"No symptoms found between {from_date} and {to_date}."

        lines = [f"Symptoms between {from_date} and {to_date}:"]
        for e in entries:
            severity = f" ({e['severity']})" if e.get("severity") else ""
            notes = f" — {e['notes']}" if e.get("notes") else ""
            lines.append(f"  • {e['occurred_at']}: {e['symptom_name']}{severity}{notes}")
        return "\n".join(lines)

    return fetch_symptoms_in_range
