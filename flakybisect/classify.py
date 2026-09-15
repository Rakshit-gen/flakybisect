"""Classify why a test is flaky from rerun output and bisect results.

Heuristic-only by default (no API key needed). If ANTHROPIC_API_KEY is set,
refines the guess with an LLM call over the collected failure output.
"""
from __future__ import annotations

import os

from .bisect import CommitResult
from .runner import RunResult

_KEYWORD_HINTS = {
    "race / ordering": ["race", "thread", "lock", "concurrent", "order"],
    "timing / timeout": ["timeout", "timed out", "sleep", "slow"],
    "network / external dependency": ["connection", "network", "dns", "refused", "unreachable"],
    "resource leak / shared state": ["already exists", "port in use", "address already", "leak"],
}


def _heuristic_classify(reruns: list[RunResult], bisect: list[CommitResult]) -> str:
    combined_output = "\n".join(r.output_tail.lower() for r in reruns)
    for label, keywords in _KEYWORD_HINTS.items():
        if any(kw in combined_output for kw in keywords):
            return label

    if bisect:
        passed_flags = {c.passed for c in bisect}
        if len(passed_flags) > 1:
            return "code regression (result changes across recent commits)"

    return "non-deterministic (no code/keyword signal, likely timing or shared state)"


def classify(reruns: list[RunResult], bisect: list[CommitResult]) -> str:
    heuristic = _heuristic_classify(reruns, bisect)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return heuristic

    try:
        from langchain_anthropic import ChatAnthropic

        llm = ChatAnthropic(model="claude-sonnet-5", max_tokens=200)
        failure_snippets = "\n---\n".join(r.output_tail for r in reruns if not r.passed)[:4000]
        bisect_summary = "\n".join(f"{c.sha[:8]} passed={c.passed} {c.subject}" for c in bisect)
        prompt = (
            "A test is flaky. A cheap heuristic guessed the cause as: "
            f"'{heuristic}'.\n\nFailure output samples:\n{failure_snippets}\n\n"
            f"Bisect results (last commits, oldest first):\n{bisect_summary}\n\n"
            "In one short sentence, give the most likely root cause category "
            "(e.g. race condition, timeout, test order dependency, shared "
            "external resource, code regression). If the heuristic already "
            "looks right, just confirm it concisely."
        )
        response = llm.invoke(prompt)
        return response.content.strip() or heuristic
    except Exception:
        return heuristic
