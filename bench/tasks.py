"""Tasks: load them, set up a fresh copy of the project for one, and score the result.

A task folder holds task.md (the prompt), check/ (the hidden tests) and, all optional:
- start/: files copied over the project (data or logs the task needs), and start.json: edits that create the
  starting state (a bug) from the base project;
- solution/ and solution.json: the reference fix, for the self-check. Bug tasks need none: the base is the fix.
The starting state is base + start/ + start.json; the solved state is base + start/ + solution/ + solution.json.
An edit is {"file", "find", "replace"}; `find` must occur exactly once, or at least once with "all": true (every
occurrence is replaced)."""
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from agent.llm import settings

HERE = Path(__file__).parent
PROJECT = HERE / "project"
TASKS = HERE / "tasks"
MARKER = ".byoca-work"  # only folders under a work root that carries this file are ever deleted


@dataclass
class Task:
    id: str
    prompt: str
    path: Path

    def edits(self, name: str) -> list[dict]:
        path = self.path / name
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def load(ids: list[str] | None = None) -> list[Task]:
    tasks = [Task(p.name, (p / "task.md").read_text(encoding="utf-8").strip(), p)
             for p in sorted(TASKS.iterdir()) if (p / "task.md").exists()]
    if ids:
        tasks = [t for t in tasks if any(t.id.startswith(i) for i in ids)]
    return tasks


def work_root() -> Path:
    root = Path(settings().get("work_root") or Path(tempfile.gettempdir()) / "byoca-work")
    root.mkdir(parents=True, exist_ok=True)
    (root / MARKER).touch()
    return root


def apply_edits(folder: Path, edits: list[dict]) -> None:
    for edit in edits:
        path = folder / edit["file"]
        text = path.read_text(encoding="utf-8")
        found = text.count(edit["find"])
        if found != 1 and not (edit.get("all") and found):
            raise ValueError(f"{edit['file']}: expected {'some' if edit.get('all') else 'exactly one'} "
                             f"{edit['find']!r}, found {found}")
        # newline="": keep LF on Windows too, so an edited file looks like every other file in the project
        path.write_text(text.replace(edit["find"], edit["replace"]), encoding="utf-8", newline="")


def prepare(task: Task, *, solved: bool = False) -> Path:
    """A fresh copy of the project in the task's starting state (or with its reference fix)."""
    root = work_root()
    folder = root / task.id
    if folder.exists():
        if not (root / MARKER).exists():
            raise RuntimeError(f"refusing to delete {folder}: {root} is not a work root")
        shutil.rmtree(folder)
    shutil.copytree(PROJECT, folder, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    overlay(folder, task.path / "start")
    if solved:
        overlay(folder, task.path / "solution")
        apply_edits(folder, task.edits("solution.json"))
    else:
        apply_edits(folder, task.edits("start.json"))
    return folder


def overlay(folder: Path, files: Path) -> None:
    """Copy a task's start/ or solution/ folder over the work copy (new files and replacements)."""
    if files.is_dir():
        shutil.copytree(files, folder, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))


def score(task: Task, folder: Path, *, hidden: bool = True) -> tuple[bool, str]:
    """Pass = the project's original tests (restored, in case the agent edited them) and the hidden check pass.
    hidden=False runs the project's tests alone (the self-check: they must pass in every starting state).
    The restore covers conftest.py and tests/fixtures/ too; tests the agent added stay, and must pass."""
    shutil.copytree(PROJECT / "tests", folder / "tests", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    for check in (task.path / "check").glob("test_*.py"):
        if hidden:
            shutil.copy2(check, folder / "tests" / check.name)
        else:
            (folder / "tests" / check.name).unlink(missing_ok=True)
    done = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"], cwd=folder,
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    lines = [line for line in done.stdout.splitlines() if line.strip()]
    return done.returncode == 0, lines[-1] if lines else done.stderr.strip()[-200:]
