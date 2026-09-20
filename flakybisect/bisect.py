"""Rerun the test against each of the last N commits via disposable git worktrees."""
from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass

from .runner import run_once


@dataclass
class CommitResult:
    sha: str
    subject: str
    passed: bool


def _run_git(args: list[str], cwd: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout.strip()


def recent_commits(repo: str, count: int) -> list[tuple[str, str]]:
    if count <= 0:
        return []
    log = _run_git(["log", f"-n{count}", "--format=%H%x09%s"], repo)
    commits = []
    for line in log.splitlines():
        sha, _, subject = line.partition("\t")
        commits.append((sha, subject))
    return commits


def bisect_commits(repo: str, test_cmd: str, count: int) -> list[CommitResult]:
    results = []
    for sha, subject in recent_commits(repo, count):
        with tempfile.TemporaryDirectory(prefix="flakybisect-") as worktree_dir:
            _run_git(["worktree", "add", "--detach", worktree_dir, sha], repo)
            try:
                run_result = run_once(test_cmd, cwd=worktree_dir)
            finally:
                _run_git(["worktree", "remove", "--force", worktree_dir], repo)
            results.append(CommitResult(sha=sha, subject=subject, passed=run_result.passed))
    return results
