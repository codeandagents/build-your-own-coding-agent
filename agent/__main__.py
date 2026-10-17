"""python -m agent "the task" [--cwd DIR] [--replay-only]"""
import argparse
from pathlib import Path

from .llm import Claude
from .loop import run


def main() -> int:
    parser = argparse.ArgumentParser(prog="agent")
    parser.add_argument("task")
    parser.add_argument("--cwd", type=Path, default=Path.cwd(), help="the project to work in")
    parser.add_argument("--replay-only", action="store_true", help="never call the API; replay recorded responses")
    args = parser.parse_args()
    claude = Claude(replay_only=args.replay_only)
    result = run(args.task, claude, args.cwd.resolve())
    print(f"[{result.stop} after {result.turns} turns]")
    return 0 if result.stop == "done" else 1


raise SystemExit(main())
