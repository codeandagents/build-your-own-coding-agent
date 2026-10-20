"""python -m agent "the task" [--cwd DIR] [--replay-only] [--window TOKENS] [--compact none|clear|full]
[--memory DIR]"""
import argparse
from contextlib import nullcontext
from pathlib import Path

from . import compact, sandbox
from .llm import Claude
from .loop import WINDOW, run


def main() -> int:
    parser = argparse.ArgumentParser(prog="agent")
    parser.add_argument("task")
    parser.add_argument("--cwd", type=Path, default=Path.cwd(), help="the project to work in")
    parser.add_argument("--replay-only", action="store_true", help="never call the API; replay recorded responses")
    parser.add_argument("--window", type=int, default=WINDOW, help="the context window, in tokens")
    parser.add_argument("--compact", choices=compact.MODES, default="full",
                        help="past the window: none ends the task, clear clears old tool outputs, full also summarizes")
    parser.add_argument("--memory", type=Path,
                        help="a folder outside the project for the agent's memory, kept from one session to the next")
    args = parser.parse_args()
    claude = Claude(replay_only=args.replay_only)
    cwd = args.cwd.resolve()
    if args.memory:
        args.memory.mkdir(parents=True, exist_ok=True)
    missing = sandbox.available()
    if missing:
        print(f"No sandbox ({missing}): you'll be asked before each command runs.")
    with nullcontext() if missing else sandbox.Sandbox(cwd, args.memory) as box:
        result = run(args.task, claude, cwd, box=box, window=args.window, mode=args.compact, memory=args.memory)
    print(f"[{result.stop} after {result.turns} turns]")
    return 0 if result.stop == "done" else 1


raise SystemExit(main())
