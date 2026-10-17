"""Writes solution/clinic.json: the clinic's data after a real `python -m petclinic import data/new_clients.csv`, run on
a scratch copy of the project (3 owners and 4 pets added, Liam O'Connor's and Ana Lopez's rows skipped for their
numbers, nothing else touched). Run it again whenever bench/project/clinic.json changes.
Run from the repo root: .venv/Scripts/python bench/tasks/t14-csv-injection/make_solution.py"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
PROJECT = HERE.parent.parent / "project"


def main() -> None:
    with tempfile.TemporaryDirectory() as scratch:
        work = Path(scratch) / "project"
        shutil.copytree(PROJECT, work, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
        shutil.copy2(HERE / "start" / "data" / "new_clients.csv", work / "data" / "new_clients.csv")
        done = subprocess.run([sys.executable, "-m", "petclinic", "import", "data/new_clients.csv"], cwd=work,
                              capture_output=True, text=True, check=True)
        print(done.stdout.strip())
        assert done.stdout.startswith("4 pets and 3 owners added, 2 rows skipped"), done.stdout
        (HERE / "solution").mkdir(exist_ok=True)
        shutil.copy2(work / "clinic.json", HERE / "solution" / "clinic.json")


if __name__ == "__main__":
    main()
