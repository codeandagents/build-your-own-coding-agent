"""python -m bench.selfcheck [--sandbox] [tNN ...]: proves each task is fair without calling a model.

In its starting state the project's own tests pass and the hidden check fails; with the reference fix, both pass.
(Scoring can't tell a failing hidden check from a failing project test, so the starting state is run twice.)
--sandbox runs the project's tests where the agent runs them, in its sandbox: they must pass there too."""
import sys

from agent.sandbox import Sandbox

from .tasks import load, prepare, score


def main() -> int:
    args = sys.argv[1:]
    sandboxed = "--sandbox" in args
    ok = True
    for task in load([a for a in args if a != "--sandbox"] or None):
        folder = prepare(task)
        visible_ok, visible_line = in_sandbox(folder) if sandboxed else score(task, folder, hidden=False)
        start_ok, start_line = score(task, folder)
        fixed_ok, fixed_line = score(task, prepare(task, solved=True))
        fair = visible_ok and not start_ok and fixed_ok
        ok &= fair
        note = "" if visible_ok else f"  project tests fail at the start: {visible_line}"
        print(f"{'ok  ' if fair else 'BAD '} {task.id:22} start: {start_line:40.40}  fixed: {fixed_line}{note}")
    return 0 if ok else 1


def in_sandbox(folder) -> tuple[bool, str]:
    """The project's own tests, run in the agent's sandbox (Linux, no network), on the task's starting state."""
    with Sandbox(folder) as box:
        code, output = box.run("python -m pytest -q -p no:cacheprovider tests", timeout=300)
    lines = [line for line in output.splitlines() if line.strip()]
    return code == 0, lines[-1] if lines else ""


if __name__ == "__main__":
    raise SystemExit(main())
