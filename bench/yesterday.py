"""python -m bench.yesterday [--session multi-pet] [--repeat N] [--first-repeat N] [--label NAME] [--no-remember]
[--plan] [--run-budget USD] [--brief]

Episode 6's "yesterday": a session that teaches the agent something, so that "today" can be measured with what it
kept. The agent starts with an empty memory and does the session's task (bench/sessions/multi-pet/task.md: add a
multi-pet discount). When it says it's done, the user replies: code review sends the work back with the clinic's rules
for discounts (review.md), and asks it to remember them (remember.md; --no-remember leaves that line out). The
session's hidden check scores the fix, and the memory folder is kept in .runs/memory/<label>/r<N>/.

Today: `bench.run --memory .runs/memory/<label>` gives try N of every task yesterday's memory rN, in a fresh copy of
the project. Yesterday's code is gone; only what the agent saved remains."""
import argparse
import json
import shutil
import time

from agent import loop
from agent import memory as mem
from agent.llm import RUNS, Claude, SpendRefused
from agent.sandbox import Sandbox, available

from .run import GREEN, PLAIN, RED, TURNS_TYPICAL, board, brief, estimate, start_memory
from .tasks import PROJECT, prepare, score, session


def main() -> int:
    parser = argparse.ArgumentParser(prog="bench.yesterday")
    parser.add_argument("--session", default="multi-pet", help="a folder in bench/sessions")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--first-repeat", type=int, default=0)
    parser.add_argument("--label", default="yesterday")
    parser.add_argument("--no-remember", action="store_true", help="code review doesn't ask it to remember the rules")
    parser.add_argument("--plan", action="store_true", help="estimate only; spends nothing")
    parser.add_argument("--run-budget", type=float, default=0.10, help="stop this run once it has cost this much")
    parser.add_argument("--brief", action="store_true", help="short, coloured output (each command's first lines)")
    args = parser.parse_args()
    task = session(args.session)
    review = (task.path / "review.md").read_text(encoding="utf-8").strip()
    if not args.no_remember:
        review += "\n\n" + (task.path / "remember.md").read_text(encoding="utf-8").strip()

    if args.plan:  # two requests from the user: the task, then the review
        claude, memory = Claude(), start_memory("empty", args.first_repeat)
        first = loop.request([mem.first_message(task.prompt, PROJECT, memory)], memory=memory)
        prefix = claude.count_tokens(system=first["system"], tools=first["tools"], messages=first["messages"])
        typical = estimate(claude.model, prefix, 2 * TURNS_TYPICAL)
        worst = estimate(claude.model, prefix, 2 * loop.MAX_TURNS)
        print(f"{task.id}: first prompt {prefix:,} tokens; {args.repeat} session(s): typical ${typical * args.repeat:.3f}, "
              f"worst case ${worst * args.repeat:.3f}. Spent so far ${claude.ledger.total():.4f} of "
              f"${claude.budget:.2f}; this run's cap ${args.run_budget:.2f}.")
        return 0
    if missing := available():
        print(f"The agent runs only in its sandbox, and the sandbox can't start: {missing}")
        return 2

    run_id = f"{args.label}-{time.strftime('%Y%m%d-%H%M%S')}"
    rows = []
    try:
        for r in range(args.first_repeat, args.first_repeat + args.repeat):
            folder, memory = prepare(task), start_memory("empty", r)
            claude = Claude(run=run_id, salt=f"r{r}", run_budget_usd=args.run_budget)
            print(f"\n=== {task.id} (repeat {r + 1}) in {folder}")
            before = len(claude.ledger.entries())
            with Sandbox(folder, memory) as box:
                result = loop.run(task.prompt, claude, folder, label=task.id, log=brief if args.brief else print,
                                  box=box, memory=memory, replies=(review,))
            passed, summary = score(task, folder)
            kept = RUNS / "memory" / args.label / f"r{r}"  # today's memory for try r + 1
            if kept.exists():
                shutil.rmtree(kept)
            shutil.copytree(memory, kept)
            saved = mem.snapshot(memory)
            spent = [e for e in claude.ledger.entries()[before:] if e["run"] == run_id and e["task"] == task.id]
            rows.append({"task": task.id, "repeat": r, "stop": result.stop, "turns": result.turns, "passed": passed,
                         "usd": round(sum(e["usd"] for e in spent), 5), "requests": len(spent),
                         "replayed": sum(e["replayed"] for e in spent), "remember": not args.no_remember,
                         "memory_saved": list(saved), "tests": summary})
            verdict = "PASS" if passed else "FAIL"
            if args.brief:
                verdict = f"{GREEN if passed else RED}{verdict}{PLAIN}"
            print(f"=== {task.id}: {verdict} ({result.stop}, {result.turns} turns, ${rows[-1]['usd']:.4f}) {summary}")
            print(f"=== memory kept in {RUNS.name}/memory/{args.label}/r{r}: {len(saved)} file{'s' * (len(saved) != 1)}")
            for name, text in saved.items():
                print(f"--- {name}\n{text.rstrip()}")
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


if __name__ == "__main__":
    raise SystemExit(main())
