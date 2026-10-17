"""The spend guards and the loop, offline: a fake client stands in for the API."""
import io
import json
import subprocess
import time
from pathlib import Path

import pytest
from anthropic.types import Message

from agent import loop, tools
from agent.llm import Claude, SpendRefused, price
from agent.tools import run_shell, run_tool, tool_env


def message(content=None, stop="end_turn", input_tokens=1000, output=50, cache_write=0, cache_read=0):
    return Message.model_validate({
        "id": "msg_test", "type": "message", "role": "assistant", "model": "claude-haiku-5-5",
        "content": content or [{"type": "text", "text": "done"}], "stop_reason": stop, "stop_sequence": None,
        "usage": {"input_tokens": input_tokens, "output_tokens": output,
                  "cache_creation_input_tokens": cache_write, "cache_read_input_tokens": cache_read}})


def bash_call(command, call_id="toolu_1"):
    return message([{"type": "tool_use", "id": call_id, "name": "bash", "input": {"command": command}}], "tool_use")


class FakeClient:
    def __init__(self, *replies):
        self.replies, self.calls, self.messages = list(replies), [], self

    def create(self, **params):
        self.calls.append(params)
        return self.replies.pop(0)


def claude(tmp_path, *replies, **kwargs):
    kwargs.setdefault("budget_usd", 1.0)
    return Claude(runs=tmp_path, client=FakeClient(*replies), **kwargs)


ASK = {"messages": [{"role": "user", "content": "hi"}], "max_tokens": 10}


def test_prices_per_million_tokens():
    assert price("claude-haiku-5-5", message(input_tokens=50_000, output=0).usage) == pytest.approx(0.10 / 20)
    assert price("claude-haiku-5-5", message(input_tokens=0, output=1_000_000).usage) == pytest.approx(0.50)
    assert price("claude-haiku-5-5", message(input_tokens=0, output=0, cache_read=50_000).usage) == pytest.approx(0.01 / 20)
    assert price("claude-haiku-5-5", message(input_tokens=0, output=0, cache_write=50_000).usage) == pytest.approx(0.125 / 20)


def test_a_prompt_over_100k_tokens_pays_five_times():
    usage = message(input_tokens=1_000, output=1_000, cache_read=100_000).usage
    assert price("claude-haiku-5-5", usage) == pytest.approx(5 * (1_000 * 0.10 + 1_000 * 0.50 + 100_000 * 0.01) / 1e6)


def test_the_same_request_again_is_replayed_free(tmp_path):
    c = claude(tmp_path, message(input_tokens=2_000))
    first = c.create(**ASK)
    again = c.create(**ASK)
    assert len(c.client().calls) == 1
    assert again.content[0].text == first.content[0].text
    usd = [e["usd"] for e in c.ledger.entries()]
    assert usd[0] > 0 and usd[1] == 0


def test_another_repeat_is_a_new_request(tmp_path):
    claude(tmp_path, message()).create(**ASK)
    second = claude(tmp_path, message(), salt="r1")
    second.create(**ASK)
    assert len(second.client().calls) == 1


def test_refuses_before_sending_when_the_budget_is_used_up(tmp_path):
    c = claude(tmp_path, message(), budget_usd=0.5)
    c.ledger.add({"run": "earlier", "task": "", "usd": 0.5})
    with pytest.raises(SpendRefused, match="budget"):
        c.create(**ASK)
    assert c.client().calls == []


def test_refuses_when_this_run_reaches_its_cap(tmp_path):
    c = claude(tmp_path, message(), run="pilot", run_budget_usd=0.1)
    c.ledger.add({"run": "pilot", "task": "t01", "usd": 0.1})
    with pytest.raises(SpendRefused, match="cap"):
        c.create(**ASK)


def test_replay_only_never_calls_the_api(tmp_path):
    with pytest.raises(SpendRefused, match="never recorded"):
        claude(tmp_path, message(), replay_only=True).create(**ASK)


def test_a_replayed_turn_hashes_like_the_live_one(tmp_path):
    live = bash_call("ls")
    replayed = Message.model_validate_json(live.model_dump_json())
    c = claude(tmp_path)
    assert c.key({"messages": [{"role": "assistant", "content": live.content}]}) == \
        c.key({"messages": [{"role": "assistant", "content": replayed.content}]})


def test_budget_settings_come_from_config_json(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({"budget_usd": 10, "warn_usd": 3.5}), encoding="utf-8")
    c = Claude(runs=tmp_path, client=FakeClient())
    assert (c.budget, c.warn_at) == (10.0, 3.5)


def test_the_loop_runs_the_tool_and_stops(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "approve", lambda command: True)  # no sandbox here: the user says yes
    c = claude(tmp_path / "runs", bash_call("echo hello"), message())
    result = loop.run("say hello", c, tmp_path, log=lambda _: None)
    assert (result.stop, result.turns) == ("done", 2)
    tool_result = c.client().calls[1]["messages"][2]["content"][0]  # user, assistant (bash), user (its result)
    assert tool_result["type"] == "tool_result" and "hello" in tool_result["content"]


def test_the_loop_stops_after_max_turns(tmp_path, monkeypatch):
    monkeypatch.setattr(loop, "MAX_TURNS", 3)
    c = claude(tmp_path / "runs", *[bash_call("echo again", f"toolu_{i}") for i in range(3)])
    assert loop.run("loop", c, tmp_path, log=lambda _: None).stop == "max_turns"


def test_the_agents_shell_never_sees_api_keys(monkeypatch):
    monkeypatch.setenv("BYOCA_API_KEY", "secret")
    monkeypatch.setenv("SPRING_AI_ANTHROPIC_API_KEY", "secret")
    assert not [k for k in tool_env() if "KEY" in k.upper()]


def test_without_a_sandbox_a_command_runs_only_with_the_users_yes(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "approve", lambda command: False)
    output, is_error = run_tool("bash", {"command": "touch made.txt"}, tmp_path)
    assert is_error and output.startswith("Not run") and not (tmp_path / "made.txt").exists()
    monkeypatch.setattr(tools, "approve", lambda command: True)
    assert run_tool("bash", {"command": "touch made.txt"}, tmp_path) == ("(no output)", False)
    assert (tmp_path / "made.txt").exists()


def test_nobody_at_the_keyboard_means_no(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("y\n"))  # a pipe, not a terminal: a benchmark run
    assert not tools.approve("ls")


def test_the_model_is_told_whether_its_commands_are_sandboxed():
    sandboxed = loop.request([])["tools"][0]["description"]
    asked = loop.request([], sandboxed=False)["tools"][0]["description"]
    assert "a Linux container with no network" in sandboxed and "the user approves each command" in asked


def test_home_is_the_project(tmp_path):
    code, output = run_shell("cd ~ && pwd -W 2>/dev/null || pwd", tmp_path)
    assert code == 0 and Path(output.strip()).resolve() == tmp_path.resolve()


def test_a_timeout_ends_the_whole_pipeline(tmp_path):
    began = time.perf_counter()
    with pytest.raises(subprocess.TimeoutExpired):
        run_shell("sleep 30 | cat", tmp_path, timeout=2)
    assert time.perf_counter() - began < 10
