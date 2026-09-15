"""Run a test command N times and report the pass/fail pattern."""
from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass


@dataclass
class RunResult:
    passed: bool
    returncode: int
    output_tail: str  # last chunk of combined stdout+stderr, for classification


def run_once(test_cmd: str, cwd: str, timeout: int = 120) -> RunResult:
    try:
        proc = subprocess.run(
            shlex.split(test_cmd),
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        return RunResult(passed=proc.returncode == 0, returncode=proc.returncode, output_tail=output[-2000:])
    except subprocess.TimeoutExpired:
        return RunResult(passed=False, returncode=-1, output_tail="TIMEOUT")


def rerun(test_cmd: str, cwd: str, times: int) -> list[RunResult]:
    return [run_once(test_cmd, cwd) for _ in range(times)]
