"""LangGraph wiring: rerun -> (stable? end : bisect -> classify) -> report."""
from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, StateGraph

from .bisect import CommitResult, bisect_commits
from .classify import classify
from .runner import RunResult, rerun


class State(TypedDict, total=False):
    test_cmd: str
    repo: str
    reruns: int
    commits: int
    rerun_results: list[RunResult]
    is_flaky: bool
    bisect_results: list[CommitResult]
    classification: str
    report: str


def node_rerun(state: State) -> dict:
    results = rerun(state["test_cmd"], cwd=state["repo"], times=state["reruns"])
    passed_flags = {r.passed for r in results}
    return {"rerun_results": results, "is_flaky": len(passed_flags) > 1}


def route_after_rerun(state: State) -> str:
    return "bisect" if state["is_flaky"] else "report"


def node_bisect(state: State) -> dict:
    results = bisect_commits(state["repo"], state["test_cmd"], state["commits"])
    return {"bisect_results": results}


def node_classify(state: State) -> dict:
    label = classify(state["rerun_results"], state.get("bisect_results", []))
    return {"classification": label}


def node_report(state: State) -> dict:
    lines = [f"# flakybisect report: `{state['test_cmd']}`", ""]
    reruns = state["rerun_results"]
    pass_count = sum(r.passed for r in reruns)
    lines.append(f"Reran {len(reruns)}x at HEAD: {pass_count} passed, {len(reruns) - pass_count} failed.")

    if not state["is_flaky"]:
        lines.append("")
        lines.append("Not flaky, result was consistent across all reruns.")
        return {"report": "\n".join(lines)}

    lines.append("")
    lines.append(f"**Likely cause:** {state['classification']}")
    lines.append("")
    lines.append("## Bisect (last commits, newest first)")
    for c in state.get("bisect_results", []):
        status = "pass" if c.passed else "FAIL"
        lines.append(f"- `{c.sha[:8]}` [{status}] {c.subject}")

    return {"report": "\n".join(lines)}


def build_graph():
    graph = StateGraph(State)
    graph.add_node("rerun", node_rerun)
    graph.add_node("bisect", node_bisect)
    graph.add_node("classify", node_classify)
    graph.add_node("report", node_report)

    graph.set_entry_point("rerun")
    graph.add_conditional_edges("rerun", route_after_rerun, {"bisect": "bisect", "report": "report"})
    graph.add_edge("bisect", "classify")
    graph.add_edge("classify", "report")
    graph.add_edge("report", END)

    return graph.compile()
