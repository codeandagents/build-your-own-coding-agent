"""python -m bench.run [--tasks t01,t02] [--repeat N] [--first-repeat N] [--label NAME] [--plan] [--run-budget USD]
[--replay-only] [--brief]

Runs the agent on each task in a fresh copy of the project, scores it with the hidden checks, prints a scoreboard
and appends it to .runs/results/<label>.jsonl. --plan spends nothing: it counts the first request's tokens
(token counting is free) and estimates the cost of the run."""
import argparse
import json
import time

from agent import loop
from agent.llm import RUNS, Claude, SpendRefused, price
from agent.sandbox import Sandbox, available

from .tasks import load, prepare, score

# Estimate assumptions. The pilot (2026-10-16, 5 easy tasks) measured 5.2 turns per task, ~870 prompt tokens added
# per turn and 273 output tokens per request ($0.0013 per task; this model gave $0.0013 too). These values plan
# for the harder benchmark: longer tasks over bigger files.
TURNS_TYPICAL = 12
GROWTH_PER_TURN = 1_500  # tokens added per turn: tool output + the model's turn (incl. thinking it keeps)
OUTPUT_PER_TURN = 300


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


def plan(args, tasks) -> int:
    claude = Claude()
    spent = claude.ledger.total()
    typical = worst = 0.0
    print(f"{'task':22} {'first prompt':>12} {'recorded':>8} {'typical':>9} {'worst case':>10}")
    for task in tasks:
        first = loop.request([{"role": "user", "content": task.prompt}])
        prefix = claude.count_tokens(system=first["system"], tools=first["tools"], messages=first["messages"])
        recorded = Claude(salt="r0").recorded(**first)
        t, w = estimate(claude.model, prefix, TURNS_TYPICAL), estimate(claude.model, prefix, loop.MAX_TURNS)
        typical, worst = typical + t, worst + w
        print(f"{task.id:22} {prefix:>12,} {'yes' if recorded else 'no':>8} {'$%.4f' % t:>9} {'$%.4f' % w:>10}")
    n = args.repeat
    print(f"\n{len(tasks)} task(s) x {n} repeat(s): typical ${typical * n:.3f}, worst case ${worst * n:.3f} "
          f"(every task running to {loop.MAX_TURNS} turns)")
    print(f"Spent so far ${spent:.4f} of the ${claude.budget:.2f} budget; this run's cap ${args.run_budget:.2f}.")
    return 0


BRIEF_LINES = 4
CYAN, YELLOW, GREY, GREEN, RED, PLAIN = "\x1b[36m", "\x1b[33m", "\x1b[90m", "\x1b[32m", "\x1b[31m", "\x1b[0m"


def brief(text: str) -> None:
    """The run in short, coloured, for a screen: the agent's words and commands in full, each output's first lines.
    Display only: the model still gets the whole output."""
    if text.startswith("agent: "):
        print(f"{CYAN}{text}{PLAIN}")
    elif text.startswith(("$ ", "> ")):  # a command, or a file tool's call
        print(f"{YELLOW}{text}{PLAIN}")
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
                with Sandbox(folder) as box:
                    result = loop.run(task.prompt, claude, folder, label=task.id, log=brief if args.brief else print,
                                      box=box)
                passed, summary = score(task, folder)
                spent = [e for e in claude.ledger.entries()[before:] if e["run"] == run_id and e["task"] == task.id]
                rows.append({"task": task.id, "repeat": r, "stop": result.stop, "turns": result.turns,
                             "passed": passed, "usd": round(sum(e["usd"] for e in spent), 5),
                             "requests": len(spent), "replayed": sum(e["replayed"] for e in spent),
                             "tests": summary})
                verdict = "PASS" if passed else "FAIL"
                if args.brief:
                    verdict = f"{GREEN if passed else RED}{verdict}{PLAIN}"
                print(f"=== {task.id}: {verdict} ({result.stop}, {result.turns} turns, "
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
