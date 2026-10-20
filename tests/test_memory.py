"""Memory (episode 6), offline: the instructions and the memory's index in the first message, a subfolder's
instructions with the first read there, the memory folder for the file tools, the user's reply, and a fresh start
after a summary that reads it all again."""
import json

import pytest

from agent import compact, loop, memory, tools
from agent.tools import run_tool
from bench import run as bench_run
from tests.test_guards import claude, message

RULES = "# Notes for coding agents\n\n- Run the tests with `python -m pytest -q`.\n"
BILLING = "# Billing\n\n- A percentage is `money.percent_of`.\n"


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "project"
    (root / "petclinic" / "billing").mkdir(parents=True)
    (root / "AGENTS.md").write_text(RULES, encoding="utf-8")
    (root / "petclinic" / "billing" / "AGENTS.md").write_text(BILLING, encoding="utf-8")
    (root / "petclinic" / "billing" / "invoices.py").write_text("KINDS = ()\n", encoding="utf-8")
    (root / "petclinic" / "store.py").write_text("x = 1\n", encoding="utf-8")
    return root


@pytest.fixture
def notes(tmp_path):
    folder = tmp_path / "memory"
    folder.mkdir()
    (folder / "MEMORY.md").write_text("- [Discount rules](discounts.md): how a discount goes on an invoice\n",
                                      encoding="utf-8")
    (folder / "discounts.md").write_text("---\nname: discounts\ntype: feedback\n---\nRight after the consults.\n",
                                         encoding="utf-8")
    return folder


def call(name, n=1, **args):
    return message([{"type": "tool_use", "id": f"toolu_{n}", "name": name, "input": args}], "tool_use")


def say(text):
    return message([{"type": "text", "text": text}], "end_turn")


def test_claude_md_wins_over_agents_md(project):
    assert memory.folder_files(project) == [project / "AGENTS.md"]
    (project / "CLAUDE.md").write_text("Use pnpm.\n", encoding="utf-8")
    assert memory.folder_files(project) == [project / "CLAUDE.md"]


def test_the_first_message_has_the_instructions_and_the_index_then_the_task(project, notes):
    first = memory.first_message("Add the discount.", project, notes)
    context, task = first["content"]
    assert task == {"type": "text", "text": "Add the discount."}
    assert context["text"].startswith("<context>\nProject instructions, from AGENTS.md:\n# Notes for coding agents")
    assert f"Your memory's index, from {(notes / 'MEMORY.md').as_posix()}:\n- [Discount rules]" in context["text"]
    assert "Right after the consults" not in context["text"]  # a memory's own file is read when it's needed


def test_nothing_to_load_leaves_episode_5s_first_message(tmp_path):
    assert memory.first_message("Fix it.", tmp_path, None) == {"role": "user", "content": "Fix it."}
    empty = tmp_path / "memory"
    empty.mkdir()
    assert "is empty: nothing has been saved yet" in memory.first_message("Fix it.", tmp_path, empty)["content"][0]["text"]


def test_the_index_is_cut_at_200_lines_or_25kb(notes):
    (notes / "MEMORY.md").write_text("".join(f"- line {n}\n" for n in range(300)), encoding="utf-8")
    kept = memory.index(notes).split("\n")
    assert kept[199] == "- line 199" and "the rest isn't loaded" in kept[200] and len(kept) == 201
    (notes / "MEMORY.md").write_text("x" * 30_000, encoding="utf-8")
    assert len(memory.index(notes).split("\n")[0]) == 25 * 1024


def test_a_subfolders_agents_md_comes_with_the_first_read_there(project):
    loaded = set()
    invoices = project / "petclinic" / "billing" / "invoices.py"
    assert memory.nested(project, invoices, "write_file", loaded) == []  # AGENTS.md: only a read loads it
    assert memory.nested(project, invoices, "read_file", loaded) == [project / "petclinic" / "billing" / "AGENTS.md"]
    assert memory.nested(project, invoices, "read_file", loaded) == []  # once
    assert memory.nested(project, project / "petclinic" / "store.py", "read_file", set()) == []  # no file there
    text = memory.attach("KINDS = ()", [project / "petclinic" / "billing" / "AGENTS.md"], project)
    assert "<instructions from petclinic/billing/AGENTS.md, which apply to the files in petclinic/billing/>" in text


def test_a_subfolders_claude_md_comes_with_a_write_too(project):
    (project / "petclinic" / "billing" / "CLAUDE.md").write_text("Cents only.\n", encoding="utf-8")
    found = memory.nested(project, project / "petclinic" / "billing" / "invoices.py", "edit_file", set())
    assert found == [project / "petclinic" / "billing" / "CLAUDE.md"]  # and not its AGENTS.md


def test_reading_the_instructions_file_itself_adds_nothing(project):
    loaded = set()
    agents = project / "petclinic" / "billing" / "AGENTS.md"
    assert memory.nested(project, agents, "read_file", loaded) == []
    assert memory.nested(project, project / "petclinic" / "billing" / "invoices.py", "read_file", loaded) == []


def test_the_file_tools_use_the_memory_folder_only_while_a_session_runs(project, notes):
    path = (notes / "MEMORY.md").as_posix()
    assert run_tool("read_file", {"path": path}, project) == (f"Blocked by the harness: {path}", True)
    with tools.also(notes):
        output, error = run_tool("read_file", {"path": path}, project)
        assert not error and "[Discount rules]" in output
        assert not run_tool("write_file", {"path": (notes / "new.md").as_posix(), "content": "hi"}, project)[1]
        found, _ = run_tool("find_files", {"pattern": "*.md", "path": notes.as_posix()}, project)
        assert found.split("\n") == [(notes / name).as_posix() for name in ("MEMORY.md", "discounts.md", "new.md")]
        assert run_tool("read_file", {"path": (notes.parent / "other.md").as_posix()}, project)[1]  # next to it: no
    assert run_tool("read_file", {"path": path}, project)[1]


def test_the_system_prompt_names_the_memory_folder_only_when_there_is_one(notes):
    assert loop.request([])["system"] == loop.SYSTEM
    with_memory = loop.request([], memory=notes)["system"]
    assert with_memory.startswith(loop.SYSTEM) and notes.resolve().as_posix() in with_memory
    assert "type: user, feedback, project or reference" in with_memory


def test_the_loop_sends_the_users_reply_when_the_agent_stops(project, notes, monkeypatch):
    monkeypatch.setattr(loop, "size", lambda *_: 0)
    c = claude(project.parent / "runs", say("Done: added it."), say("Fixed, and saved the rules."))
    log = []
    result = loop.run("Add it.", c, project, log=log.append, memory=notes, replies=("Review: put it after the consults.",))
    assert (result.stop, result.turns) == ("done", 2)
    conversation = c.client().calls[1]["messages"]  # the list itself: it has grown since the call
    assert conversation[2] == {"role": "user", "content": "Review: put it after the consults."}
    assert "user: Review: put it after the consults." in log
    assert log[:2] == [f"[project instructions: AGENTS.md, {len(RULES)} characters]",
                       f"[memory: {(notes / 'MEMORY.md').as_posix()}, 1 line]"]


def test_the_loop_adds_the_subfolders_instructions_to_the_first_read_there(project, monkeypatch):
    monkeypatch.setattr(loop, "size", lambda *_: 0)
    c = claude(project.parent / "runs", call("read_file", path="petclinic/billing/invoices.py"),
               call("read_file", 2, path="petclinic/billing/invoices.py"), say("done"))
    log = []
    loop.run("Look.", c, project, log=log.append)
    conversation = c.client().calls[2]["messages"]  # the list itself: it has grown since the call
    first, again = (conversation[n]["content"][0]["content"] for n in (2, 4))
    assert first.startswith("     1\tKINDS = ()") and "money.percent_of" in first
    assert "money.percent_of" not in again
    assert "[loaded petclinic/billing/AGENTS.md: the instructions for that folder]" in log


def test_a_fresh_start_after_a_summary_reads_the_instructions_and_memory_again(project, notes):
    messages, _, _ = compact.restart("Add it.\n\nReview: fix it.", "1. Request: add it.", project, [], 32_000,
                                     context=memory.context(project, notes))
    context, text = messages[0]["content"]
    assert "Project instructions, from AGENTS.md" in context["text"] and "[Discount rules]" in context["text"]
    assert text["text"].startswith("Add it.\n\nReview: fix it.\n\n" + compact.RESTART)


def test_memory_files_dont_come_back_as_files_touched(project, notes):
    calls = message([{"type": "tool_use", "id": "t1", "name": "write_file",
                      "input": {"path": (notes / "MEMORY.md").as_posix()}},
                     {"type": "tool_use", "id": "t2", "name": "read_file", "input": {"path": "AGENTS.md"}}], "tool_use")
    with tools.also(notes):
        assert compact.touched_files([{"role": "assistant", "content": calls.content}], project) == ["AGENTS.md"]


@pytest.fixture
def work(tmp_path, monkeypatch):
    root = tmp_path / "work"
    root.mkdir()
    (root / ".byoca-work").touch()
    monkeypatch.setattr(bench_run, "work_root", lambda: root)
    return root


def test_each_try_starts_from_its_own_copy_of_yesterdays_memory(work, tmp_path):
    saved = tmp_path / "saved"
    for r in range(2):
        (saved / f"r{r}").mkdir(parents=True)
        (saved / f"r{r}" / "MEMORY.md").write_text(f"try {r}\n", encoding="utf-8")
    live = bench_run.start_memory(str(saved), 1)
    assert live == work / "memory" and (live / "MEMORY.md").read_text(encoding="utf-8") == "try 1\n"
    (live / "extra.md").write_text("a task wrote this", encoding="utf-8")
    again = bench_run.start_memory(str(saved), 1)
    assert sorted(p.name for p in again.iterdir()) == ["MEMORY.md"]  # what one task saved never reaches the next
    with pytest.raises(SystemExit, match="r0, r1"):
        bench_run.start_memory(str(saved), 2)


def test_empty_none_and_a_plain_folder(work, notes):
    assert bench_run.start_memory("none", 0) is None
    assert list(bench_run.start_memory("empty", 0).iterdir()) == []
    assert sorted(p.name for p in bench_run.start_memory(str(notes), 2).iterdir()) == ["MEMORY.md", "discounts.md"]


def test_the_files_a_session_saved(notes):
    before = memory.snapshot(notes)
    (notes / "MEMORY.md").write_text("- changed\n", encoding="utf-8")
    (notes / "rules.md").write_text("new\n", encoding="utf-8")
    assert bench_run.saved_files(before, notes) == ["MEMORY.md", "rules.md"]


def test_yesterdays_session_is_fair_and_its_reply_asks_to_remember():
    from bench.tasks import session
    task = session("multi-pet")
    assert "Multi-pet discount" in task.prompt and (task.path / "check" / "test_check_multi_pet.py").is_file()
    review = (task.path / "review.md").read_text(encoding="utf-8")
    assert "directly after the last consultation line" in review and "remember" not in review
    assert "remember them for next time" in (task.path / "remember.md").read_text(encoding="utf-8")
    assert json.loads((task.path / "solution.json").read_text(encoding="utf-8"))
