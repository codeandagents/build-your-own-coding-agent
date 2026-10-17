"""The sandbox (episode 4). The first tests run anywhere; the rest need Docker and the byoca-sandbox image
(docker build -t byoca-sandbox sandbox), and are skipped without them."""
import subprocess
import sys
import time

import pytest

from agent import loop, sandbox, tools
from agent.sandbox import Sandbox, inside
from agent.tools import run_tool
from bench import escape
from bench import run as bench_run
from tests.test_guards import bash_call, claude, message

MISSING = sandbox.available()
needs_docker = pytest.mark.skipif(bool(MISSING), reason=f"no sandbox: {MISSING}")


def test_a_path_from_the_sandbox_works_in_the_file_tools(tmp_path):
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    assert inside(tmp_path).startswith("/") and inside(tmp_path).endswith(tmp_path.name)
    assert run_tool("read_file", {"path": inside(tmp_path) + "/a.txt"}, tmp_path) == ("     1\thello", False)


def test_without_docker_there_is_no_sandbox(monkeypatch):
    monkeypatch.setattr(sandbox.shutil, "which", lambda name: None)
    assert sandbox.available() == "Docker isn't installed"


def test_the_benchmark_wont_run_without_its_sandbox(monkeypatch, capsys):
    monkeypatch.setattr(bench_run, "available", lambda: "Docker isn't installed")
    monkeypatch.setattr(sys, "argv", ["bench.run", "--tasks", "t01"])
    assert bench_run.main() == 2
    assert "only in its sandbox" in capsys.readouterr().out


def test_the_old_rails_matched_text_not_reach():
    assert escape.rails("cat ../.env") and escape.rails("find / -name notes.md")
    assert not escape.rails("cp clinic.json ../clinic-before-dedupe.json")  # ep 2's write outside the folder
    assert not escape.rails('grep -rl "a\\|b" / --exclude-dir=proc')  # ep 3's whole-disk grep: the \| hid the /
    assert not escape.rails('cd "$OLDPWD" && ls')
    harmless = next(a for a in escape.ATTEMPTS if a.seen.startswith("ep 2 act 1, t09"))
    assert escape.rails(harmless.command)  # a / in Python code, a line after a grep


@pytest.fixture
def box(tmp_path):
    with Sandbox(tmp_path) as box:
        yield box


@needs_docker
def test_a_command_runs_in_the_project_at_its_own_path(tmp_path, box):
    code, output = box.run("pwd && echo hi > made.txt", timeout=30)
    assert (code, output.strip()) == (0, inside(tmp_path))
    assert (tmp_path / "made.txt").read_text().strip() == "hi"


@needs_docker
def test_the_folder_above_holds_only_the_project(tmp_path, box):
    (tmp_path.parent / "neighbour.txt").write_text("not for the agent", encoding="utf-8")
    assert box.run("ls -a ..", timeout=30)[1].split() == [".", "..", tmp_path.name]


@needs_docker
def test_nothing_outside_the_project_is_writable(tmp_path, box):
    code, output = box.run("touch ../outside.txt", timeout=30)
    assert code and "Read-only file system" in output
    assert not (tmp_path.parent / "outside.txt").exists()


@needs_docker
def test_tmp_is_writable_and_lasts_the_task(box):
    box.run("echo scratch > /tmp/check.txt", timeout=30)
    assert box.run("cat /tmp/check.txt", timeout=30) == (0, "scratch\n")


@needs_docker
def test_there_is_no_network(box):
    code, output = box.run("curl -sS --max-time 10 https://example.com", timeout=30)
    assert code and "Could not resolve host" in output


@needs_docker
def test_this_machines_environment_stays_outside(box, monkeypatch):
    monkeypatch.setenv("CLINIC_DB_URL", "postgres://clinic:hunter2@db/clinic")
    assert "hunter2" not in box.run("env", timeout=30)[1]


@needs_docker
def test_the_tools_the_tests_need_are_there(box):
    assert box.run("python -m pytest --version", timeout=30)[1].strip() == "pytest 9.1.1"
    assert box.run("git --version", timeout=30)[0] == 0


@needs_docker
def test_a_timeout_ends_the_whole_pipeline(box):
    began = time.perf_counter()
    with pytest.raises(subprocess.TimeoutExpired):
        box.run("sleep 30 | cat", timeout=2)
    assert time.perf_counter() - began < 15


@needs_docker
def test_a_command_left_running_in_the_background_doesnt_hold_up_the_agent(box):
    began = time.perf_counter()
    box.run("sleep 30 &", timeout=60)
    assert time.perf_counter() - began < 15


@needs_docker
def test_in_the_sandbox_bash_runs_without_asking(tmp_path, box, monkeypatch):
    monkeypatch.setattr(tools, "approve", lambda command: pytest.fail("asked in the sandbox"))
    assert run_tool("bash", {"command": "echo hi"}, tmp_path, box) == ("hi\n", False)


@needs_docker
def test_the_loop_runs_the_agents_commands_in_the_sandbox(tmp_path, box):
    c = claude(tmp_path / "runs", bash_call("pwd"), message())
    assert loop.run("where are you?", c, tmp_path, log=lambda _: None, box=box).stop == "done"
    assert c.client().calls[1]["messages"][2]["content"][0]["content"] == inside(tmp_path) + "\n"
    assert "Commands run in a sandbox" in c.client().calls[0]["tools"][0]["description"]


@needs_docker
def test_every_escape_is_contained(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("BYOCA_WORK_ROOT", str(tmp_path / "work"))
    monkeypatch.setenv("CLINIC_DB_URL", "")  # escape sets its own marked values; this puts them back afterwards
    monkeypatch.setenv("OLDPWD", "")
    assert escape.main() == 0, capsys.readouterr().out
