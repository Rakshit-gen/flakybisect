"""Turn the finished graph state into a report. Register your own with @register_reporter."""
from __future__ import annotations

import json

from .plugins import register_reporter


@register_reporter("markdown")
def markdown_report(state: dict) -> str:
    lines = [f"# flakybisect report: `{state['test_cmd']}`", ""]
    reruns = state["rerun_results"]
    pass_count = sum(r.passed for r in reruns)
    lines.append(f"Reran {len(reruns)}x at HEAD: {pass_count} passed, {len(reruns) - pass_count} failed.")

    if not state["is_flaky"]:
        lines.append("")
        lines.append("Not flaky, result was consistent across all reruns.")
        return "\n".join(lines)

    lines.append("")
    lines.append(f"**Likely cause:** {state['classification']}")
    lines.append("")
    lines.append("## Bisect (last commits, newest first)")
    for c in state.get("bisect_results", []):
        status = "pass" if c.passed else "FAIL"
        lines.append(f"- `{c.sha[:8]}` [{status}] {c.subject}")

    return "\n".join(lines)


@register_reporter("json")
def json_report(state: dict) -> str:
    """Machine-readable report, for piping into CI (auto-file a ticket, gate a merge, ...)."""
    reruns = state["rerun_results"]
    payload = {
        "test_cmd": state["test_cmd"],
        "is_flaky": state["is_flaky"],
        "reruns_passed": sum(r.passed for r in reruns),
        "reruns_total": len(reruns),
        "classification": state.get("classification"),
        "bisect": [
            {"sha": c.sha, "subject": c.subject, "passed": c.passed} for c in state.get("bisect_results", [])
        ],
    }
    return json.dumps(payload, indent=2)
