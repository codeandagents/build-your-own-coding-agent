"""Compaction (episode 5), offline: clearing old tool outputs, the summary, the fresh start, and the guard."""
import json
import os

import pytest

from agent import compact, loop
from agent.compact import CLEARED, KEEP, SUMMARY, clear_old_outputs, restart, summary_request, touched_files
from bench.run import compaction_cost
from tests.test_guards import claude, message

LINES = "".join(f"line {n} " + "x" * 90 + "\n" for n in range(40))  # 4,000-odd characters: ~1,100 counted tokens


def chars(claude, messages, sandboxed):
    """The tests' token count: the conversation's characters / 4 (the real loop asks the API)."""
    return len(json.dumps(messages, default=str)) // 4


def read(*paths, n=1):
    return message([{"type": "tool_use", "id": f"toolu_{n}{i}", "name": "read_file", "input": {"path": p}}
                    for i, p in enumerate(paths)], "tool_use")


def say(text, stop="end_turn"):
    return message([{"type": "text", "text": text}], stop)


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setattr(loop, "size", chars)
    for name in "abcd":
        (tmp_path / f"{name}.md").write_text(LINES, encoding="utf-8")
    return tmp_path


def history(results: list[int]) -> list:
    """A conversation: the task, then one turn per result (thinking + a read_file call; a result of N characters)."""
    messages = [{"role": "user", "content": "the task"}]
    for n, length in enumerate(results):
        turn = message([{"type": "thinking", "thinking": "", "signature": f"sig{n}"},
                        {"type": "tool_use", "id": f"toolu_{n}", "name": "read_file", "input": {"path": f"f{n}.md"}}],
                       "tool_use")
        messages.append({"role": "assistant", "content": turn.content})
        messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": f"toolu_{n}",
                                                      "content": "y" * length, "is_error": False}]})
    return messages


def test_the_window_sits_below_the_ceiling():
    assert loop.WINDOW < loop.PROMPT_CEILING and loop.THRASH == 3 and KEEP == 3


def test_clearing_keeps_the_newest_results_and_notes_the_rest():
    messages = history([2_000, 3_000, 100, 4_000, 5_000])
    new, cleared = clear_old_outputs(messages)
    contents = [new[i]["content"][0]["content"] for i in (2, 4, 6, 8, 10)]
    assert cleared == 2
    assert contents[0] == f"{CLEARED}: the output of read_file(f0.md), 2,000 characters. Run it again if you need it.]"
    assert contents[1].startswith(CLEARED) and "3,000 characters" in contents[1]
    assert contents[2:] == ["y" * 100, "y" * 4_000, "y" * 5_000]  # the newest three, whole
    assert messages[2]["content"][0]["content"] == "y" * 2_000  # the old conversation isn't changed
    assert clear_old_outputs(new)[1] == 0  # nothing left to clear


def test_short_old_results_stay():
    assert clear_old_outputs(history([100, 200, 4_000, 4_000, 4_000]))[1] == 0


def test_clearing_drops_the_thinking_after_the_first_change_only():
    messages = history([100, 2_000, 4_000, 4_000, 4_000])  # the first change is the second result (message 4)
    new, _ = clear_old_outputs(messages)
    kinds = [[compact.kind(b) for b in m["content"]] for m in new if m["role"] == "assistant"]
    assert kinds[:2] == [["thinking", "tool_use"]] * 2  # before the change: still valid, kept
    assert kinds[2:] == [["tool_use"]] * 3  # after it: invalid, dropped (the tool calls stay)


def test_the_summary_request_only_adds_to_the_end():
    messages = history([4_000, 4_000])
    ask = summary_request(messages)
    assert ask[:-1] == messages[:-1]
    assert ask[-1]["content"][:-1] == messages[-1]["content"]
    assert ask[-1]["content"][-1] == {"type": "text", "text": SUMMARY}
    assert "Files and code" in SUMMARY and "don't call any tools" in SUMMARY


def test_the_files_touched_most_recently_come_first(tmp_path):
    for i, name in enumerate(["old.py", "mid.py", "new.py"]):
        (tmp_path / name).write_text("x\n", encoding="utf-8")
        os.utime(tmp_path / name, (1_000_000 + i, 1_000_000 + i))
    calls = message([{"type": "tool_use", "id": "t1", "name": "read_file", "input": {"path": "old.py"}},
                     {"type": "tool_use", "id": "t2", "name": "edit_file", "input": {"path": "./new.py"}},
                     {"type": "tool_use", "id": "t3", "name": "write_file", "input": {"path": "mid.py"}},
                     {"type": "tool_use", "id": "t4", "name": "read_file", "input": {"path": "gone.py"}},
                     {"type": "tool_use", "id": "t5", "name": "read_file", "input": {"path": "../outside.py"}},
                     {"type": "tool_use", "id": "t6", "name": "bash", "input": {"command": "cat old.py"}}], "tool_use")
    assert touched_files([{"role": "assistant", "content": calls.content}], tmp_path) == ["new.py", "mid.py", "old.py"]


def test_the_new_conversation_starts_from_the_task_the_summary_and_the_files(tmp_path):
    (tmp_path / "small.py").write_text("print('hi')\n", encoding="utf-8")
    (tmp_path / "big.md").write_text(LINES, encoding="utf-8")
    messages, read_again, named = restart("Fix the bug.", "1. Request: fix it.", tmp_path, ["small.py", "big.md"],
                                          window=16_000)  # room: 2,000 tokens (~4,000 characters)
    assert (read_again, named) == (["small.py"], ["big.md"])
    [only] = messages
    text = only["content"]
    assert only["role"] == "user" and text.startswith("Fix the bug.\n\n" + compact.RESTART)
    assert "<summary>\n1. Request: fix it.\n</summary>" in text
    assert "small.py:\n     1\tprint('hi')" in text and "big.md: too long to include" in text


def test_a_window_that_isnt_full_changes_nothing(project):
    c = claude(project / "runs", read("a.md"), say("done"))
    result = loop.run("read a", c, project, log=lambda _: None, window=10_000)
    assert (result.stop, result.clearings, result.summaries) == ("done", 0, 0)
    assert len(c.client().calls) == 2


def test_without_compaction_a_full_window_ends_the_task(project):
    c = claude(project / "runs", read("a.md"), say("done"))
    result = loop.run("read a", c, project, log=lambda _: None, window=500, mode="none")
    assert (result.stop, result.turns) == ("context_limit", 1)
    assert len(c.client().calls) == 1


def four_reads(project, mode, *more):
    """a, then b, then c and d in one turn: the window (3,000) fills up after the third turn, and clearing a alone
    isn't enough to make room."""
    c = claude(project / "runs", read("a.md", n=1), read("b.md", n=2), read("c.md", "d.md", n=3), *more)
    log = []
    return c, loop.run("read them all", c, project, log=log.append, window=3_000, mode=mode), log


def test_clearing_only_ends_the_task_when_clearing_isnt_enough(project):
    c, result, log = four_reads(project, "clear")
    assert (result.stop, result.turns, result.clearings) == ("context_limit", 3, 1)
    assert len(c.client().calls) == 3
    assert any(line.startswith("[cleared 1 old tool output:") for line in log)


def test_full_compaction_summarizes_and_starts_again(project):
    c, result, log = four_reads(project, "full", say("SUMMARY TEXT"), say("done"))
    assert (result.stop, result.clearings, result.summaries) == ("done", 1, 1)
    calls = c.client().calls
    ask = calls[3]["messages"]  # the summary request: the cleared conversation, and the instruction at its end
    assert ask[-1]["content"][-1]["text"] == SUMMARY
    assert ask[2]["content"][0]["content"].startswith(CLEARED)  # a's output was cleared first
    assert calls[3]["system"] == calls[2]["system"] and calls[3]["tools"] == calls[2]["tools"]
    fresh = calls[4]["messages"][0]  # then the conversation starts again (the list grew after the call)
    assert fresh["content"].startswith("read them all\n\n") and "<summary>\nSUMMARY TEXT\n</summary>" in fresh["content"]
    assert [e["kind"] for e in c.ledger.entries()] == ["turn", "turn", "turn", "summary", "turn"]
    assert "summary: SUMMARY TEXT" in log


def test_the_guard_stops_a_window_that_fills_up_after_every_summary(project):
    (project / "huge.md").write_text(LINES * 4, encoding="utf-8")  # one read is more than the window
    replies = [read("huge.md", n=1)]
    for n in range(2, 5):
        replies += [say(f"summary {n}"), read("huge.md", n=n)]
    c = claude(project / "runs", *replies)
    log = []
    result = loop.run("read huge", c, project, log=log.append, window=3_000, mode="full")
    assert (result.stop, result.summaries) == ("compaction_thrash", 3)
    assert len(c.client().calls) == 7  # 4 turns, 3 summaries, and no fourth
    assert log[-1] == "[the window filled up again straight after 3 summaries in a row: stopping]"


def test_the_plan_prices_a_compaction():
    assert compaction_cost("claude-haiku-5-5", 32_000, "none") == 0
    assert compaction_cost("claude-haiku-5-5", 32_000, "clear") == pytest.approx(32_000 * 0.125 / 1e6)
    assert compaction_cost("claude-haiku-5-5", 32_000, "full") > 2 * compaction_cost("claude-haiku-5-5", 32_000, "clear")
