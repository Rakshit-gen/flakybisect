"""Self-check: no pytest required, run directly with `python tests/test_flakybisect.py`."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flakybisect.bisect import bisect_commits
from flakybisect.classify import classify
from flakybisect.runner import RunResult, rerun

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")


def test_deterministic_failure_is_not_flaky():
    results = rerun('python3 -c "import sys; sys.exit(1)"', cwd=REPO_ROOT, times=4)
    passed_flags = {r.passed for r in results}
    assert len(passed_flags) == 1, "a command that always fails must not look flaky"


def test_alternating_exit_code_is_flaky():
    # exits 0 on even PID parity vs a fixed seed isn't reliable across runs, so force
    # alternation deterministically via a counter file instead of relying on randomness.
    counter_file = os.path.join(REPO_ROOT, ".flaky_test_counter")
    if os.path.exists(counter_file):
        os.remove(counter_file)
    cmd = (
        f'python3 -c "'
        f"import os; f='{counter_file}'; n=int(open(f).read()) if os.path.exists(f) else 0; "
        f"open(f,'w').write(str(n+1)); import sys; sys.exit(0 if n % 2 == 0 else 1)\""
    )
    results = rerun(cmd, cwd=REPO_ROOT, times=4)
    os.remove(counter_file)
    passed_flags = {r.passed for r in results}
    assert len(passed_flags) == 2, "an alternating pass/fail command must look flaky"


def test_bisect_runs_across_real_commits():
    results = bisect_commits(REPO_ROOT, 'python3 -c "import sys; sys.exit(0)"', count=3)
    assert len(results) == 3
    assert all(c.passed for c in results)
    assert all(len(c.sha) == 40 for c in results)


def test_classify_picks_up_keyword_hints():
    reruns = [RunResult(passed=False, returncode=1, output_tail="ConnectionRefusedError: network unreachable")]
    label = classify(reruns, bisect=[])
    assert "network" in label


def test_classify_falls_back_without_signal():
    reruns = [RunResult(passed=False, returncode=1, output_tail="AssertionError: 1 != 2")]
    label = classify(reruns, bisect=[])
    assert "non-deterministic" in label or "regression" in label


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"\n{len(tests)} checks passed")
