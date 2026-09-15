# flakybisect

A flaky test tells you almost nothing — it fails, you rerun it, it passes, you
move on. `flakybisect` reruns the test at HEAD to confirm it's actually
flaky, then bisects it against your recent commits and classifies the likely
root cause (race condition, timeout, order dependency, shared resource,
or an actual regression) instead of you guessing from a wall of CI logs.

Built as a [LangGraph](https://github.com/langchain-ai/langgraph) `StateGraph`:
a rerun loop, a conditional branch (stable vs. flaky), a real git-worktree
bisect over your last N commits, and a classification step — heuristic by
default, refined by an LLM call if `ANTHROPIC_API_KEY` is set.

## Install

```bash
pip install -e .
# optional, for LLM-refined classification:
pip install -e ".[llm]"
```

## Use

```bash
flakybisect --cmd "pytest tests/test_thing.py::test_flaky" --reruns 5 --commits 5
```

Exits `0` if the test wasn't actually flaky, `1` if it was — so it's
CI-pipeline-friendly.

```
# flakybisect report: `pytest tests/test_thing.py::test_flaky`

Reran 5x at HEAD: 3 passed, 2 failed.

**Likely cause:** race / ordering

## Bisect (last commits, newest first)
- `a1b2c3d4` [pass] fix: guard against double-init
- `e5f6a7b8` [pass] add retry to flaky client call
- `9c0d1e2f` [FAIL] refactor: extract client into shared fixture
```

## How it works

1. **rerun** — runs your test command N times at `HEAD`.
2. If every run agrees, it's reported as not flaky and the graph ends there.
3. **bisect** — otherwise, checks out each of the last N commits into a
   disposable `git worktree` and reruns the test once per commit.
4. **classify** — scans failure output for keywords (`timeout`, `race`,
   `connection refused`, ...) and correlates with the bisect results. With
   `ANTHROPIC_API_KEY` set, hands the same evidence to an LLM for a sharper
   read.
5. **report** — a markdown summary, printed and optionally written with `-o`.

## Test it yourself

```bash
python tests/test_flakybisect.py
```

No API key or network access required — the LLM step is opt-in only.
