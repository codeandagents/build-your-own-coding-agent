"""The file tools (episode 2), offline: read with line numbers and ranges, write, edit by exact replacement."""
import os

import pytest

from agent import loop
from agent.tools import MAX_OUTPUT, describe, run_tool
from tests.test_guards import claude, message


def call(tmp_path, name, **args):
    return run_tool(name, args, tmp_path)


def edit(tmp_path, path, old, new, **more):
    return call(tmp_path, "edit_file", path=path, old_string=old, new_string=new, **more)


def put(tmp_path, name, data: bytes):
    (tmp_path / name).write_bytes(data)


def test_read_shows_line_numbers_and_a_range(tmp_path):
    put(tmp_path, "a.txt", b"".join(b"line %d\n" % n for n in range(1, 11)))
    output, is_error = call(tmp_path, "read_file", path="a.txt", offset=4, limit=2)
    assert not is_error and output == "     4\tline 4\n     5\tline 5"
    assert call(tmp_path, "read_file", path="a.txt")[0].splitlines()[-1] == "    10\tline 10"
    assert call(tmp_path, "read_file", path="a.txt", offset=20)[0] == "(a.txt has 10 lines)"


def test_a_long_read_is_cut_like_bash_output(tmp_path):
    put(tmp_path, "big.md", b"x" * 100 + b"\n" + b"y" * 30_000 + b"\n")
    output, _ = call(tmp_path, "read_file", path="big.md")
    assert len(output) < MAX_OUTPUT + 100 and "more characters cut]" in output


def test_a_missing_file_is_an_error(tmp_path):
    output, is_error = call(tmp_path, "read_file", path="nope.py")
    assert is_error and output == "No such file: nope.py"


def test_edit_replaces_text_that_occurs_exactly_once(tmp_path):
    put(tmp_path, "m.py", b"A = 1\nB = 2\n")
    output, is_error = edit(tmp_path, "m.py", "B = 2", "B = 3")
    assert not is_error and output == "Edited m.py: 1 replacement, from line 2"
    assert (tmp_path / "m.py").read_bytes() == b"A = 1\nB = 3\n"


def test_edit_refuses_text_that_occurs_more_than_once(tmp_path):
    put(tmp_path, "m.py", b"x = 1\ny = 1\n")
    output, is_error = edit(tmp_path, "m.py", "= 1", "= 2")
    assert is_error and "occurs 2 times" in output and "replace_all" in output
    assert (tmp_path / "m.py").read_bytes() == b"x = 1\ny = 1\n"


def test_replace_all_replaces_every_occurrence(tmp_path):
    put(tmp_path, "m.py", b"x = 1\ny = 1\n")
    output, is_error = edit(tmp_path, "m.py", "= 1", "= 2", replace_all=True)
    assert not is_error and output == "Edited m.py: 2 replacements, from line 1"
    assert (tmp_path / "m.py").read_bytes() == b"x = 2\ny = 2\n"


def test_edit_refuses_text_that_is_not_there(tmp_path):
    put(tmp_path, "m.py", b"def f():\n    return 1\n")
    output, is_error = edit(tmp_path, "m.py", "def f():\n  return 1", "def f():\n  return 2")  # wrong indentation
    assert is_error and output.startswith("old_string not found in m.py")
    assert (tmp_path / "m.py").read_bytes() == b"def f():\n    return 1\n"


def test_non_ascii_text_survives_an_edit(tmp_path):
    put(tmp_path, "messages.py", "SMS = 'Kia ora $owner. Reply STOP to opt out.'\nSIGN = 'Ngā mihi, Harbourside Vets'\n"
        .encode("utf-8"))
    assert not edit(tmp_path, "messages.py", "Reply STOP", "Txt STOP")[1]
    assert not edit(tmp_path, "messages.py", "Ngā mihi,", "Ngā mihi nui,")[1]
    assert (tmp_path / "messages.py").read_text(encoding="utf-8") == \
        "SMS = 'Kia ora $owner. Txt STOP to opt out.'\nSIGN = 'Ngā mihi nui, Harbourside Vets'\n"
    assert "Ngā mihi nui" in call(tmp_path, "read_file", path="messages.py")[0]


def test_windows_line_ends_are_left_alone(tmp_path):
    put(tmp_path, "crlf.txt", b"one\r\ntwo\r\nthree\r\n")
    assert call(tmp_path, "read_file", path="crlf.txt")[0] == "     1\tone\n     2\ttwo\n     3\tthree"
    assert not edit(tmp_path, "crlf.txt", "two", "TWO")[1]
    assert not edit(tmp_path, "crlf.txt", "one\nTWO", "ONE\nTWO")[1]  # lines as read_file shows them
    assert (tmp_path / "crlf.txt").read_bytes() == b"ONE\r\nTWO\r\nthree\r\n"


def test_write_creates_folders_and_never_adds_carriage_returns(tmp_path):
    output, is_error = call(tmp_path, "write_file", path="tests/new/test_x.py", content="def test_x():\n    pass\n")
    assert not is_error and output == "Wrote tests/new/test_x.py (23 characters)"
    assert (tmp_path / "tests/new/test_x.py").read_bytes() == b"def test_x():\n    pass\n"


@pytest.mark.parametrize("path", ["../outside.txt", "sub/../../outside.txt", ".env", "config/.env.local"])
@pytest.mark.parametrize("tool", ["read_file", "write_file", "edit_file"])
def test_paths_outside_the_folder_are_refused(tmp_path, tool, path):
    work = tmp_path / "work"
    work.mkdir()
    (tmp_path / "outside.txt").write_text("secret", encoding="utf-8")
    args = {"read_file": {}, "write_file": {"content": "x"}, "edit_file": {"old_string": "secret", "new_string": "x"}}
    output, is_error = run_tool(tool, {"path": path, **args[tool]}, work)
    assert is_error and output.startswith("Blocked by the harness")
    assert (tmp_path / "outside.txt").read_text(encoding="utf-8") == "secret"


def test_an_absolute_path_elsewhere_is_refused(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    (tmp_path / "outside.txt").write_text("secret", encoding="utf-8")
    output, is_error = run_tool("read_file", {"path": str(tmp_path / "outside.txt")}, work)
    assert is_error and output.startswith("Blocked by the harness")


@pytest.mark.skipif(os.name != "nt", reason="Git Bash paths exist on Windows only")
def test_a_git_bash_path_into_the_folder_works(tmp_path):
    put(tmp_path, "a.txt", b"hello\n")
    drive, rest = str(tmp_path.resolve()).split(":", 1)
    git_bash_path = f"/{drive.lower()}{rest.replace(os.sep, '/')}/a.txt"
    assert call(tmp_path, "read_file", path=git_bash_path) == ("     1\thello", False)


def test_a_wrong_argument_is_an_error_not_a_crash(tmp_path):
    output, is_error = call(tmp_path, "write_file", path="a.txt")
    assert is_error and "content" in output


def test_the_log_shows_file_tools_as_calls():
    assert describe("bash", {"command": "pytest -q"}) == "$ pytest -q"
    assert describe("read_file", {"path": "t.md", "offset": 300, "limit": 100}) == "> read_file(t.md, offset=300, limit=100)"
    assert describe("edit_file", {"path": "m.py", "old_string": "a", "new_string": "b"}) == "> edit_file(m.py)"


def test_the_loop_runs_a_file_tool(tmp_path):
    put(tmp_path, "notes.md", b"remember the milk\n")
    read = message([{"type": "tool_use", "id": "toolu_1", "name": "read_file", "input": {"path": "notes.md"}}], "tool_use")
    c = claude(tmp_path / "runs", read, message())
    assert loop.run("read the notes", c, tmp_path, log=lambda _: None).stop == "done"
    tool_result = c.client().calls[1]["messages"][2]["content"][0]
    assert tool_result["content"] == "     1\tremember the milk" and not tool_result["is_error"]
