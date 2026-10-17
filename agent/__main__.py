"""python -m agent "the task" [--cwd DIR] [--replay-only]"""
import argparse
from contextlib import nullcontext
from pathlib import Path

from . import sandbox
from .llm import Claude
from .loop import run


def main() -> int:
    parser = argparse.ArgumentParser(prog="agent")
    parser.add_argument("task")
    parser.add_argument("--cwd", type=Path, default=Path.cwd(), help="the project to work in")
    parser.add_argument("--replay-only", action="store_true", help="never call the API; replay recorded responses")
    args = parser.parse_args()
    claude = Claude(replay_only=args.replay_only)
    cwd = args.cwd.resolve()
    missing = sandbox.available()
    if missing:
        print(f"No sandbox ({missing}): you'll be asked before each command runs.")
    with nullcontext() if missing else sandbox.Sandbox(cwd) as box:
        result = run(args.task, claude, cwd, box=box)
    print(f"[{result.stop} after {result.turns} turns]")
    return 0 if result.stop == "done" else 1


raise SystemExit(main())
