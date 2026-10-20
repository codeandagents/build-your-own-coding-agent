"""python -m bench.run [--tasks t01,t02] [--repeat N] [--first-repeat N] [--label NAME] [--plan] [--run-budget USD]
[--replay-only] [--brief] [--window TOKENS] [--compact none|clear|full] [--memory none|empty|FOLDER]

Runs the agent on each task in a fresh copy of the project, scores it with the hidden checks, prints a scoreboard
and appends it to .runs/results/<label>.jsonl. --plan spends nothing: it counts the first request's tokens
(token counting is free) and estimates the cost of the run. --window and --compact set the context window and what
happens past it (episode 5: agent/compact.py). --memory (episode 6: agent/memory.py): each task starts with no
memory, an empty one (the default), or a copy of a saved one; a folder with r0, r1... in it (bench.yesterday's) gives
try N its own rN. Every task starts from that copy, so no task learns from another; what a task saved is kept in
.runs/memory/<run>/ to read afterwards."""
import argparse
import json
import shutil
import time
from pathlib import Path

from agent import compact, loop
from agent import memory as mem
from agent.llm import RUNS, Claude, SpendRefused, price
from agent.sandbox import Sandbox, available

from .tasks import PROJECT, load, prepare, score, work_root

# Estimate assumptions. The pilot (2026-10-16, 5 easy tasks) measured 5.2 turns per task, ~870 prompt tokens added
# per turn and 273 output tokens per request ($0.0013 per task; this model gave $0.0013 too). These values plan
# for the harder benchmark: longer tasks over bigger files.
TURNS_TYPICAL = 12
GROWTH_PER_TURN = 1_500  # tokens added per turn: tool output + the model's turn (incl. thinking it keeps)
OUTPUT_PER_TURN = 300
SUMMARY_OUT = 2_000      # tokens a summary request writes (the summary, and the thinking before it)
COMPACTIONS_WORST = 10   # compactions in one try, for the worst case (the thrash guard stops a try that keeps filling up)


class Usage:  # the shape price() reads
    def __init__(self, input_tokens=0, cache_creation_input_tokens=0, cache_read_input_tokens=0, output_tokens=0):
        self.input_tokens, self.output_tokens = input_tokens, output_tokens
        self.cache_creation_input_tokens, self.cache_read_input_tokens = cache_creation_input_tokens, cache_read_input_tokens


def estimate(model: str, prefix: int, turns: int) -> float:
    """Cost of one task with prompt caching: each turn writes what's new and reads the rest from the cache."""
    total = 0.0
    for i in range(turns):
        prompt = prefix + i * GROWTH_PER_TURN
        new = prefix if i == 0 else GROWTH_PER_TURN
        total += price(model, Usage(0, new, prompt - new, OUTPUT_PER_TURN))
    return total


def compaction_cost(model: str, window: int, mode: str) -> float:
    """What one compaction adds, at most. Clearing rewrites the cache from the first cleared output on (at most the
    whole window). A summary also writes its request to the cache, writes the summary, and starts a new conversation
    (the summary, and files read again: an eighth of the window)."""
    clearing = price(model, Usage(0, window, 0, 0))
    summary = price(model, Usage(0, window, 0, SUMMARY_OUT)) + price(model, Usage(0, window // 8 + SUMMARY_OUT, 0, 0))
    return {"none": 0.0, "clear": clearing, "full": clearing + summary}[mode]


def start_memory(source: str, repeat: int) -> Path | None:
    """One try's memory folder, fresh: None (no memory), empty, or a copy of a saved one (its rN for try N+1, if it
    has those). It sits outside the project, next to the work copies, as Claude Code's sits outside the repository
    (~/.claude/projects/<project>/memory/)."""
    if source == "none":
        return None
    live = work_root() / "memory"  # under the work root, which carries the marker: safe to delete
    if live.exists():
        shutil.rmtree(live)
    live.mkdir(parents=True)
    if source != "empty":
        root = Path(source)
        tries = sorted(p.name for p in root.glob("r[0-9]*") if p.is_dir())
        saved = root / f"r{repeat}" if tries else root
        if not saved.is_dir():
            raise SystemExit(f"--memory: no folder {saved}" + (f" (it has {', '.join(tries)})" if tries else ""))
        shutil.copytree(saved, live, dirs_exist_ok=True)
    return live


def saved_files(before: dict, memory: Path | None) -> list[str]:
    """The memory files a session wrote or changed."""
    after = mem.snapshot(memory) if memory else {}
    return [name for name, text in after.items() if before.get(name) != text]


def plan(args, tasks) -> int:
    claude = Claude()
    spent = claude.ledger.total()
    typical = worst = 0.0
    print(f"{'task':22} {'first prompt':>12} {'recorded':>8} {'typical':>9} {'worst case':>10}")
    for task in tasks:
        memory = start_memory(args.memory, args.first_repeat)  # the first try's memory, as the run will start it
        first = loop.request([mem.first_message(task.prompt, PROJECT, memory)], memory=memory)
        prefix = claude.count_tokens(system=first["system"], tools=first["tools"], messages=first["messages"])
        recorded = Claude(salt="r0").recorded(**first)
        t, w = estimate(claude.model, prefix, TURNS_TYPICAL), estimate(claude.model, prefix, loop.MAX_TURNS)
        typical, worst = typical + t, worst + w
        print(f"{task.id:22} {prefix:>12,} {'yes' if recorded else 'no':>8} {'$%.4f' % t:>9} {'$%.4f' % w:>10}")
    n = args.repeat
    print(f"\n{len(tasks)} task(s) x {n} repeat(s): typical ${typical * n:.3f}, worst case ${worst * n:.3f} "
          f"(every task running to {loop.MAX_TURNS} turns)")
    if args.compact != "none":
        each = compaction_cost(claude.model, args.window, args.compact)
        print(f"Window {args.window:,} tokens, compaction '{args.compact}': each compaction adds up to ${each:.4f}; "
              f"{COMPACTIONS_WORST} in every try would add ${each * COMPACTIONS_WORST * len(tasks) * n:.3f}.")
    print(f"Spent so far ${spent:.4f} of the ${claude.budget:.2f} budget; this run's cap ${args.run_budget:.2f}.")
    return 0


BRIEF_LINES = 4
SUMMARY_LINES = 12  # a summary's first lines
HARNESS = ("[context:", "[cleared", "[summary:", "[still past", "[the window", "[the summary",  # loop.run's own lines
           "[project instructions", "[memory", "[loaded")
CYAN, YELLOW, GREY, GREEN, RED, MAGENTA, BOLD, PLAIN = ("\x1b[36m", "\x1b[33m", "\x1b[90m", "\x1b[32m", "\x1b[31m",
                                                        "\x1b[35m", "\x1b[1m", "\x1b[0m")


def brief(text: str) -> None:
    """The run in short, coloured, for a screen: the agent's words and commands in full, each output's first lines.
    Display only: the model still gets the whole output."""
    if text.startswith("agent: "):
        print(f"{CYAN}{text}{PLAIN}")
    elif text.startswith("user: "):  # the user's reply (yesterday's code review)
        print(f"{BOLD}{text}{PLAIN}")
    elif text.startswith(("$ ", "> ")):  # a command, or a file tool's call
        print(f"{YELLOW}{text}{PLAIN}")
    elif text.startswith(HARNESS):  # the harness at work: the window, a compaction
        print(f"{MAGENTA}{text}{PLAIN}")
    elif text.startswith("summary: "):
        lines = text.splitlines()
        more = "\n..." if len(lines) > SUMMARY_LINES else ""
        print(f"{MAGENTA}{chr(10).join(lines[:SUMMARY_LINES])}{more}{PLAIN}")
    else:
        lines = text.splitlines()
        more = "\n..." if len(lines) > BRIEF_LINES else ""
        print(f"{GREY}{chr(10).join(lines[:BRIEF_LINES])}{more}{PLAIN}")


def main() -> int:
    parser = argparse.ArgumentParser(prog="bench.run")
    parser.add_argument("--tasks", help="comma-separated task ids or prefixes (default: all)")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--first-repeat", type=int, default=0,
                        help="number the tries from here: --first-repeat 3 --repeat 3 adds tries 4-6, new requests")
    parser.add_argument("--label", default="dev")
    parser.add_argument("--plan", action="store_true", help="estimate only; spends nothing")
    parser.add_argument("--run-budget", type=float, default=0.50, help="stop this run once it has cost this much")
    parser.add_argument("--replay-only", action="store_true", help="never call the API")
    parser.add_argument("--brief", action="store_true", help="short, coloured output (each command's first lines)")
    parser.add_argument("--window", type=int, default=loop.WINDOW, help="the context window, in tokens")
    parser.add_argument("--compact", choices=compact.MODES, default="full",
                        help="past the window: none ends the task, clear clears old tool outputs, full also summarizes")
    parser.add_argument("--memory", default="empty",
                        help="none, empty (the default), or a saved memory folder (with r0, r1...: one per try)")
    args = parser.parse_args()
    tasks = load(args.tasks.split(",") if args.tasks else None)
    if args.plan:
        return plan(args, tasks)
    if missing := available():  # the agent never runs commands on this machine unattended
        print(f"The benchmark runs the agent only in its sandbox, and the sandbox can't start: {missing}")
        return 2

    run_id = f"{args.label}-{time.strftime('%Y%m%d-%H%M%S')}"
    rows = []
    try:
        for r in range(args.first_repeat, args.first_repeat + args.repeat):
            for task in tasks:
                folder = prepare(task)
                claude = Claude(run=run_id, salt=f"r{r}", run_budget_usd=args.run_budget, replay_only=args.replay_only)
                print(f"\n=== {task.id} (repeat {r + 1}) in {folder}")
                before = len(claude.ledger.entries())  # this try's requests only, not the task's earlier tries
                memory = start_memory(args.memory, r)
                remembered = mem.snapshot(memory) if memory else {}
                with Sandbox(folder) as box:
                    result = loop.run(task.prompt, claude, folder, label=task.id, log=brief if args.brief else print,
                                      box=box, window=args.window, mode=args.compact, memory=memory)
                passed, summary = score(task, folder)
                saved = saved_files(remembered, memory)
                if saved:  # kept to read afterwards; the next task starts from the copy again
                    shutil.copytree(memory, RUNS / "memory" / run_id / f"{task.id}-r{r}", dirs_exist_ok=True)
                spent = [e for e in claude.ledger.entries()[before:] if e["run"] == run_id and e["task"] == task.id]
                rows.append({"task": task.id, "repeat": r, "stop": result.stop, "turns": result.turns,
                             "passed": passed, "usd": round(sum(e["usd"] for e in spent), 5),
                             "requests": len(spent), "replayed": sum(e["replayed"] for e in spent),
                             "window": args.window, "compact": args.compact, "clearings": result.clearings,
                             "summaries": result.summaries, "memory": args.memory, "memory_saved": saved,
                             "tests": summary})
                verdict = "PASS" if passed else "FAIL"
                if args.brief:
                    verdict = f"{GREEN if passed else RED}{verdict}{PLAIN}"
                compacted = "".join(f", {n} {what}" for n, what in ((result.clearings, "cleared"),
                                                                     (result.summaries, "summarized"),
                                                                     (len(saved), "memory saved")) if n)
                print(f"=== {task.id}: {verdict} ({result.stop}, {result.turns} turns{compacted}, "
                      f"${rows[-1]['usd']:.4f}) {summary}")
    except SpendRefused as e:
        print(f"\nSTOPPED: {e}")
    finally:
        if rows:
            out = RUNS / "results" / f"{args.label}.jsonl"
            out.parent.mkdir(parents=True, exist_ok=True)
            with out.open("a", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps({"run": run_id, **row}) + "\n")
            board(rows, Claude().ledger.total())
    return 0


def board(rows: list[dict], total: float) -> None:
    print(f"\n{'task':22} {'rep':>3} {'result':6} {'stop':13} {'turns':>5} {'cost':>8}")
    for row in rows:
        print(f"{row['task']:22} {row['repeat'] + 1:>3} {'PASS' if row['passed'] else 'FAIL':6} {row['stop']:13} "
              f"{row['turns']:>5} {'$%.4f' % row['usd']:>8}")
    passed = sum(r["passed"] for r in rows)
    cost = sum(r["usd"] for r in rows)
    print(f"\nScore {passed}/{len(rows)}. This run ${cost:.4f}; all runs so far ${total:.4f}.")


if __name__ == "__main__":
    raise SystemExit(main())
