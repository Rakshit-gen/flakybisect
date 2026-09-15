"""LangGraph wiring: rerun -> (stable? end : bisect -> classify) -> report.

The classifier and reporter are swappable: build_graph(classifier=..., reporter=...)
picks by name from the flakybisect.plugins registries (see classify.py, reporters.py,
or register your own).
"""
from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, StateGraph

from . import classify as _classify  # noqa: F401  (registers built-in classifiers)
from . import reporters as _reporters  # noqa: F401  (registers built-in reporters)
from .bisect import CommitResult, bisect_commits
from .plugins import CLASSIFIERS, REPORTERS
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


def build_graph(classifier: str = "hybrid", reporter: str = "markdown"):
    classify_fn = CLASSIFIERS[classifier]
    report_fn = REPORTERS[reporter]

    def node_classify(state: State) -> dict:
        label = classify_fn(state["rerun_results"], state.get("bisect_results", []))
        return {"classification": label}

    def node_report(state: State) -> dict:
        return {"report": report_fn(state)}

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
