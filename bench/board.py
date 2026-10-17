"""python -m bench.board RESULTS: the scoreboard of a benchmark run, one row per task and one column per try.

RESULTS is a results file (results/ep01.jsonl) or a run label (.runs/results/<label>.jsonl). A file that holds
several runs shows the last one. Spends nothing."""
import json
import sys
from pathlib import Path

from agent.llm import RUNS

SMOKE = 5  # t01-t05 are the cheap smoke set; t06-t15 the hard ten


def rows_of(arg: str) -> list[dict]:
    path = Path(arg)
    if not path.exists():
        path = RUNS / "results" / f"{arg}.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    last = rows[-1]["run"]
    return [r for r in rows if r["run"] == last]


def main() -> int:
    rows = rows_of(sys.argv[1])
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
    smoke = [r for r in rows if r["task"] in tasks[:SMOKE]]
    hard = [r for r in rows if r["task"] in tasks[SMOKE:]]
    day = rows[0]["run"].rsplit("-", 2)[-2]
    print(f"Score {passed}/{len(rows)} ({passed / len(rows):.0%}): smoke {sum(r['passed'] for r in smoke)}/{len(smoke)}, "
          f"hard {sum(r['passed'] for r in hard)}/{len(hard)}. ${sum(r['usd'] for r in rows):.4f}, "
          f"{day[:4]}-{day[4:6]}-{day[6:]}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
