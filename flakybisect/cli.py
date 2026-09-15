from __future__ import annotations

import argparse
import sys

from .graph import build_graph
from .plugins import CLASSIFIERS, REPORTERS


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="flakybisect",
        description="Rerun a flaky test, bisect recent commits, and classify the likely root cause.",
    )
    parser.add_argument("--cmd", help='test command, e.g. "pytest tests/test_x.py::test_y"')
    parser.add_argument("--repo", default=".", help="git repo root (default: current directory)")
    parser.add_argument("--reruns", type=int, default=5, help="times to rerun at HEAD (default: 5)")
    parser.add_argument("--commits", type=int, default=5, help="recent commits to bisect if flaky (default: 5)")
    parser.add_argument("--classifier", default="hybrid", choices=sorted(CLASSIFIERS), help="default: hybrid")
    parser.add_argument("--reporter", default="markdown", choices=sorted(REPORTERS), help="default: markdown")
    parser.add_argument("-o", "--out", help="write the report to this file")
    parser.add_argument("--list-plugins", action="store_true", help="list registered classifiers/reporters and exit")
    args = parser.parse_args(argv)

    if args.list_plugins:
        print("classifiers:", ", ".join(sorted(CLASSIFIERS)))
        print("reporters:  ", ", ".join(sorted(REPORTERS)))
        return 0

    if not args.cmd:
        parser.error("--cmd is required")

    app = build_graph(classifier=args.classifier, reporter=args.reporter)
    final_state = app.invoke(
        {"test_cmd": args.cmd, "repo": args.repo, "reruns": args.reruns, "commits": args.commits}
    )

    report = final_state["report"]
    print(report)
    if args.out:
        with open(args.out, "w") as f:
            f.write(report)

    return 0 if not final_state["is_flaky"] else 1


if __name__ == "__main__":
    sys.exit(main())
