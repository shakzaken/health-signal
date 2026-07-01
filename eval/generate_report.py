"""
Generate a markdown eval report from run_evals results.

Reads the JSON results file produced by run_evals --output and writes a
human-readable report with:
  - Score table per question
  - Category breakdown
  - Failure analysis with root cause classification
  - Prioritized improvement recommendations

Usage:
    cd ai-agent
    python -m eval.run_evals --token <jwt> --output eval/results.json
    python -m eval.generate_report eval/results.json --out eval/report.md
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


ROOT_CAUSE_MAP = {
    "wrong_route": "Supervisor routed to the wrong agent — fix CLASSIFY_PROMPT in supervisor.py",
    "missing_data": "Data missing from DB — check ingestion extractor for that document type",
    "wrong_date": "LLM picked the wrong date's value — add date-precision instruction to agent system prompt",
    "incomplete_retrieval": "RAG didn't fetch enough context — increase TOP_K or chunk overlap",
    "hallucination": "LLM fabricated values not in the source data — add grounding instructions",
    "safety_violation": "Diagnostic language used — strengthen safety instructions in agent system prompt",
    "unknown": "Root cause unclear — inspect the answer and tool call logs manually",
}


def classify_root_cause(result: dict) -> str:
    """Heuristically classify the root cause of a failing/warning result."""
    answer = result.get("answer", "").lower()
    score = result.get("score", {})
    case = result.get("case", {})

    # Safety violation
    if score.get("safety", 5) < 4:
        return "safety_violation"

    # Explicit routing ground truth beats heuristics when available
    if case.get("expected_route") and not result.get("route_correct", True):
        return "wrong_route"

    # Low completeness with decent relevance → likely incomplete retrieval or missing data
    if score.get("completeness", 5) <= 2 and score.get("relevance", 5) >= 3:
        return "incomplete_retrieval"

    # Low relevance → likely wrong route
    if score.get("relevance", 5) <= 2:
        return "wrong_route"

    # Answer exists but has wrong specific values
    reasoning = result.get("score", {}).get("reasoning", "").lower()
    if any(w in reasoning for w in ["wrong value", "incorrect value", "incorrect date", "wrong date"]):
        return "wrong_date"

    if any(w in reasoning for w in ["not found", "no data", "couldn't find", "no information"]):
        return "missing_data"

    if any(w in reasoning for w in ["fabricat", "hallucin", "not in the document", "invented"]):
        return "hallucination"

    return "unknown"


def generate_report(results: list[dict], output_path: Path, test_number: str | None = None) -> None:
    total = len(results)
    passed = [r for r in results if r["status"] == "PASS"]
    warned = [r for r in results if r["status"] == "WARN"]
    failed = [r for r in results if r["status"] == "FAIL"]

    pass_rate = len(passed) / total * 100 if total else 0
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = []

    # Header
    test_label = f" — Test {test_number}" if test_number else ""
    lines += [
        f"# Health Signal — Eval Report{test_label}",
        f"",
        f"**Generated:** {now}  ",
        f"**Total cases:** {total}  ",
        f"**Pass rate:** {pass_rate:.0f}% ({len(passed)} pass / {len(warned)} warn / {len(failed)} fail)",
        f"",
    ]

    # Overall verdict
    if not failed and not warned:
        lines += ["> ✅ **All cases passed.** System is performing well.", ""]
    elif not failed:
        lines += ["> ⚠️ **No blocking failures, but warnings need attention.**", ""]
    else:
        lines += [f"> ❌ **{len(failed)} blocking failure(s) detected.** Fix before launch.", ""]

    # Score table
    lines += [
        "## Results Table",
        "",
        "| # | ID | Question | Category | Route | Relevance | Safety | Completeness | Status |",
        "|---|-----|----------|----------|-------|-----------|--------|--------------|--------|",
    ]
    for i, r in enumerate(results, 1):
        case = r["case"]
        score = r["score"]
        status_icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(r["status"], "?")
        q = case["question"][:55] + "..." if len(case["question"]) > 55 else case["question"]
        expected_route = case.get("expected_route")
        actual_route = r.get("actual_route", "")
        if not expected_route:
            route_cell = actual_route or "-"
        elif r.get("route_correct", True):
            route_cell = f"✓ {actual_route}"
        else:
            route_cell = f"✗ {actual_route} (expected {'/'.join(expected_route)})"
        lines.append(
            f"| {i} | {case['id']} | {q} | {case.get('category','-')} | {route_cell} | "
            f"{score['relevance']} | {score['safety']} | {score['completeness']} | {status_icon} {r['status']} |"
        )
    lines.append("")

    # Routing accuracy
    routed = [r for r in results if r["case"].get("expected_route")]
    if routed:
        correct = [r for r in routed if r.get("route_correct", True)]
        wrong = [r for r in routed if not r.get("route_correct", True)]
        lines += [
            "## Routing Accuracy",
            "",
            f"**{len(correct)}/{len(routed)} correct** ({len(correct) / len(routed) * 100:.0f}%)",
            "",
        ]
        if wrong:
            lines += ["**Misrouted:**", ""]
            for r in wrong:
                case = r["case"]
                lines.append(
                    f"- [{case['id']}] \"{case['question'][:70]}\" — "
                    f"expected `{'/'.join(case['expected_route'])}`, got `{r.get('actual_route', '')}`"
                )
            lines.append("")

    # Category breakdown
    lines += ["## Category Breakdown", ""]
    categories = sorted({r["case"]["category"] for r in results})
    for cat in categories:
        cat_results = [r for r in results if r["case"]["category"] == cat]
        p = sum(1 for r in cat_results if r["status"] == "PASS")
        w = sum(1 for r in cat_results if r["status"] == "WARN")
        f = sum(1 for r in cat_results if r["status"] == "FAIL")
        avg_rel = sum(r["score"]["relevance"] for r in cat_results) / len(cat_results)
        avg_safe = sum(r["score"]["safety"] for r in cat_results) / len(cat_results)
        avg_comp = sum(r["score"]["completeness"] for r in cat_results) / len(cat_results)
        lines += [
            f"### {cat.upper()}",
            f"- Cases: {len(cat_results)} | ✅ {p} pass / ⚠️ {w} warn / ❌ {f} fail",
            f"- Avg scores: Relevance={avg_rel:.1f}  Safety={avg_safe:.1f}  Completeness={avg_comp:.1f}",
            "",
        ]

    # Failures and warnings detail
    problems = [r for r in results if r["status"] in ("FAIL", "WARN")]
    if problems:
        lines += ["## Failures & Warnings", ""]
        for r in problems:
            case = r["case"]
            score = r["score"]
            root_cause = classify_root_cause(r)
            icon = "❌" if r["status"] == "FAIL" else "⚠️"
            lines += [
                f"### {icon} [{case['id']}] {case['question']}",
                f"",
                f"**Scores:** Relevance={score['relevance']}  Safety={score['safety']}  Completeness={score['completeness']}  ",
                f"**Judge reasoning:** {score['reasoning']}  ",
                f"**Root cause:** `{root_cause}` — {ROOT_CAUSE_MAP[root_cause]}  ",
                f"",
                f"**Answer given:**",
                f"```",
                r.get("answer", "")[:500] + ("..." if len(r.get("answer", "")) > 500 else ""),
                f"```",
                "",
            ]

    # Improvement recommendations
    lines += ["## Improvement Recommendations", ""]

    root_causes = [classify_root_cause(r) for r in problems]
    cause_counts = {}
    for c in root_causes:
        cause_counts[c] = cause_counts.get(c, 0) + 1

    if not problems:
        lines += ["No issues found. Consider expanding the golden dataset to cover more edge cases.", ""]
    else:
        lines += [
            "Prioritized by frequency of root cause:",
            "",
        ]
        for cause, count in sorted(cause_counts.items(), key=lambda x: -x[1]):
            fix = ROOT_CAUSE_MAP[cause]
            affected = [r["case"]["id"] for r in problems if classify_root_cause(r) == cause]
            lines += [
                f"### {cause.replace('_', ' ').title()} ({count} case{'s' if count > 1 else ''})",
                f"**Affected:** {', '.join(affected)}  ",
                f"**Fix:** {fix}",
                "",
            ]

    # Footer
    lines += [
        "---",
        "",
        f"*Report generated by `eval/generate_report.py` on {now}*",
        f"*Reference: [eval/golden_qa.md](golden_qa.md)*",
    ]

    output_path.write_text("\n".join(lines))
    print(f"Report written to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate eval report from results JSON")
    parser.add_argument("results", help="Path to results JSON file (from run_evals --output)")
    parser.add_argument("--out", default="eval/report.md", help="Output markdown path")
    parser.add_argument("--test", default=None, help="Test number label (e.g. 001)")
    args = parser.parse_args()

    results_path = Path(args.results)
    if not results_path.exists():
        print(f"Results file not found: {results_path}")
        sys.exit(1)

    results = json.loads(results_path.read_text())
    generate_report(results, Path(args.out), test_number=args.test)


if __name__ == "__main__":
    main()
