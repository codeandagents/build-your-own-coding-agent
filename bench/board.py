"""python -m bench.board RESULTS [RESULTS ...]: the scoreboard of a benchmark run, one row per task and one column per try.

RESULTS is a results file (results/ep01.jsonl) or a run label (.runs/results/<label>.jsonl). A file that holds
several runs shows the last one. Several files make one board: later tries of the same harness (a run made with
--first-repeat 3 adds tries 4-6). Spends nothing."""
import json
import sys
from pathlib import Path

from agent.llm import RUNS

SMOKE = ("t01", "t02", "t03", "t04", "t05")  # the cheap smoke set; t06-t15 are the hard ten


def rows_of(arg: str) -> list[dict]:
    path = Path(arg)
    if not path.exists():
        path = RUNS / "results" / f"{arg}.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    last = rows[-1]["run"]
    return [r for r in rows if r["run"] == last]


def main() -> int:
    rows = [row for arg in sys.argv[1:] for row in rows_of(arg)]
    tries_seen = [(r["task"], r["repeat"]) for r in rows]
    if len(set(tries_seen)) < len(tries_seen):
        raise SystemExit("the same try appears in two files: give each harness's runs once")
    tasks = list(dict.fromkeys(r["task"] for r in rows))
    tries = max(r["repeat"] for r in rows) + 1
    print(f"{'task':22}" + "".join(f"{'try %d' % (i + 1):>7}" for i in range(tries)) + f"{'turns':>7}{'cost':>9}")
    for task in tasks:
        mine = sorted((r for r in rows if r["task"] == task), key=lambda r: r["repeat"])
        cells = {r["repeat"]: "PASS" if r["passed"] else "FAIL" for r in mine}
        turns = sum(r["turns"] for r in mine) / len(mine)
        cost = sum(r["usd"] for r in mine) / len(mine)
        print(f"{task:22}" + "".join(f"{cells.get(i, '-'):>7}" for i in range(tries)) + f"{turns:>7.1f}"
              f"{'$%.4f' % cost:>9}")
    passed = sum(r["passed"] for r in rows)
    smoke = [r for r in rows if r["task"].startswith(SMOKE)]
    hard = [r for r in rows if r["task"][:1] == "t" and r["task"][1:3].isdigit() and r not in smoke]
    split = (f": smoke {sum(r['passed'] for r in smoke)}/{len(smoke)}, hard {sum(r['passed'] for r in hard)}/{len(hard)}"
             if smoke and hard else "")  # a board of a few tasks (or of yesterday's sessions) has no split
    days = sorted({r["run"].rsplit("-", 2)[-2] for r in rows})
    print(f"Score {passed}/{len(rows)} ({passed / len(rows):.0%}){split}. ${sum(r['usd'] for r in rows):.4f}, "
          + ", ".join(f"{d[:4]}-{d[4:6]}-{d[6:]}" for d in days) + ".")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
