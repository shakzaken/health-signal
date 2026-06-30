import httpx
from langchain_core.tools import tool


def make_fetch_lab_results(backend_url: str, token: str):
    """Return a tool that fetches all lab results with markers and test dates."""

    @tool
    async def fetch_lab_results() -> str:
        """Fetch all lab test results with their markers and test dates."""
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{backend_url}/api/lab-results", headers=headers, timeout=10.0
            )
            response.raise_for_status()
            results = response.json()

        if not results:
            return "No lab results found."

        # Build per-test detail lines (oldest first so history reads chronologically)
        sorted_results = sorted(results, key=lambda r: r.get("test_date") or "")
        lines = []
        for result in sorted_results:
            lines.append(f"\nTest date: {result.get('test_date', 'unknown')}")
            if result.get("lab_name"):
                lines.append(f"Lab: {result['lab_name']}")
            for marker in result.get("markers", []):
                ref = ""
                if marker.get("reference_low") is not None and marker.get("reference_high") is not None:
                    ref = f" (normal: {marker['reference_low']}–{marker['reference_high']})"
                status = f" [{marker['status']}]" if marker.get("status") else ""
                lines.append(f"  • {marker['name']}: {marker['value']} {marker['unit']}{ref}{status}")

        # Explicit summary of any marker that was ever outside normal range
        abnormal_statuses = {"high", "low", "borderline_low", "borderline_high", "critical"}
        ever_abnormal: dict[str, list[str]] = {}
        for result in sorted_results:
            date = result.get("test_date", "?")
            for marker in result.get("markers", []):
                if (marker.get("status") or "").lower() in abnormal_statuses:
                    name = marker["name"]
                    ever_abnormal.setdefault(name, []).append(
                        f"{date}: {marker['value']} {marker['unit']} [{marker['status']}]"
                    )

        if ever_abnormal:
            lines.append("\n\n=== MARKERS WITH ANY ABNORMAL READING (across all test dates) ===")
            for name, entries in ever_abnormal.items():
                lines.append(f"  {name}:")
                for entry in entries:
                    lines.append(f"    - {entry}")

        return "\n".join(lines)

    return fetch_lab_results


def make_get_marker_history(backend_url: str, token: str):
    """Return a tool that fetches the full history of a single lab marker by name."""

    @tool
    async def get_marker_history(marker_name: str) -> str:
        """Get historical values for a specific lab marker by name (e.g. 'Cholesterol', 'Hemoglobin')."""
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{backend_url}/api/lab-results/markers/{marker_name}/history",
                headers=headers,
                timeout=10.0,
            )
            response.raise_for_status()
            history = response.json().get("history", [])

        if not history:
            return f"No historical data found for marker: {marker_name}"

        lines = [f"History for {marker_name}:"]
        for entry in history:
            ref = ""
            if entry.get("reference_low") is not None and entry.get("reference_high") is not None:
                ref = f" (normal: {entry['reference_low']}–{entry['reference_high']})"
            status = f" [{entry['status']}]" if entry.get("status") else ""
            date_label = entry.get("test_date") or entry.get("created_at", "unknown date")
            lines.append(f"  • {date_label}: {entry['value']} {entry['unit']}{ref}{status}")
        return "\n".join(lines)

    return get_marker_history
