"""The benchmark's task set-up: start/ and solution/ overlays and edits. Offline, no model calls."""
import json

import pytest

from bench.tasks import Task, apply_edits, load, prepare


def make_task(tmp_path):
    folder = tmp_path / "t99-overlays"
    (folder / "start" / "logs").mkdir(parents=True)
    (folder / "start" / "logs" / "import.log").write_text("row 2: ok\n", encoding="utf-8")
    (folder / "solution" / "petclinic").mkdir(parents=True)
    (folder / "solution" / "petclinic" / "closures.py").write_text("CLOSED = set()\n", encoding="utf-8")
    (folder / "start.json").write_text(json.dumps([{"file": "petclinic/settings.py", "find": "GST_PERCENT = 15\n",
                                                    "replace": "GST_PERCENT = 16\n"}]), encoding="utf-8")
    return Task(folder.name, "prompt", folder)


def test_start_state_gets_start_files_and_edits(tmp_path, monkeypatch):
    monkeypatch.setenv("BYOCA_WORK_ROOT", str(tmp_path / "work"))
    work = prepare(make_task(tmp_path))
    assert (work / "logs" / "import.log").read_text(encoding="utf-8") == "row 2: ok\n"
    assert not (work / "petclinic" / "closures.py").exists()
    settings = (work / "petclinic" / "settings.py").read_bytes()
    assert b"GST_PERCENT = 16\n" in settings
    assert b"\r\n" not in settings  # edited files keep LF on Windows too


def test_solved_state_gets_start_and_solution_files(tmp_path, monkeypatch):
    monkeypatch.setenv("BYOCA_WORK_ROOT", str(tmp_path / "work"))
    work = prepare(make_task(tmp_path), solved=True)
    assert (work / "logs" / "import.log").exists()
    assert (work / "petclinic" / "closures.py").exists()
    assert b"GST_PERCENT = 15\n" in (work / "petclinic" / "settings.py").read_bytes()


def test_an_edit_can_replace_every_occurrence(tmp_path):
    (tmp_path / "a.py").write_text("x = telephone\ny = telephone\n", encoding="utf-8")
    apply_edits(tmp_path, [{"file": "a.py", "find": "telephone", "replace": "phone", "all": True}])
    assert (tmp_path / "a.py").read_text(encoding="utf-8") == "x = phone\ny = phone\n"
    with pytest.raises(ValueError, match="exactly one"):
        apply_edits(tmp_path, [{"file": "a.py", "find": "phone", "replace": "tel"}])
    with pytest.raises(ValueError, match="some"):
        apply_edits(tmp_path, [{"file": "a.py", "find": "fax", "replace": "tel", "all": True}])


def test_every_task_has_a_prompt_and_a_hidden_check():
    tasks = load()
    assert len(tasks) == 15
    for task in tasks:
        assert task.prompt
        assert list((task.path / "check").glob("test_*.py")), task.id
