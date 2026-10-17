"""python -m bench.selfcheck: proves each task is fair without calling a model.

In its starting state the project's own tests pass and the hidden check fails; with the reference fix, both pass.
(Scoring can't tell a failing hidden check from a failing project test, so the starting state is run twice.)"""
import sys

from .tasks import load, prepare, score


def main() -> int:
    ok = True
    for task in load(sys.argv[1:] or None):
        folder = prepare(task)
        visible_ok, visible_line = score(task, folder, hidden=False)
        start_ok, start_line = score(task, folder)
        fixed_ok, fixed_line = score(task, prepare(task, solved=True))
        fair = visible_ok and not start_ok and fixed_ok
        ok &= fair
        note = "" if visible_ok else f"  project tests fail at the start: {visible_line}"
        print(f"{'ok  ' if fair else 'BAD '} {task.id:22} start: {start_line:40.40}  fixed: {fixed_line}{note}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
