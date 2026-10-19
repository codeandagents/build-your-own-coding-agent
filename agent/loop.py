"""The agent loop: send the conversation, run the tools the model asks for, repeat until it stops. When the
conversation no longer fits the context window, it is compacted (episode 5: agent/compact.py)."""
from dataclasses import dataclass
from pathlib import Path

from . import compact
from .llm import Claude
from .sandbox import Sandbox
from .tools import TOOLS, bash_tool, describe, run_tool

SYSTEM = """You are a coding agent working in a software project on the user's machine.
Use the search tools (search_files, find_files) to look around, the file tools (read_file, write_file, edit_file) to
read and edit files, and the bash tool to run the tests. Work in small steps and check your work.
When the task is done, reply with a short summary of what you changed."""

MAX_TURNS = 25           # a task that isn't done by then is stopped (a looping agent is the main cost risk)
PROMPT_CEILING = 80_000  # tokens: no request is ever longer (Haiku 5.5's price is 5x above 100k)
WINDOW = 64_000          # tokens: the context window. Past it the conversation is compacted (episode 5); it sits
                         # below the ceiling, so the summary request still fits under it
THRASH = 3               # summaries in a row, each filled up again at once: stop (Claude Code: "after a few attempts")


@dataclass
class Result:
    stop: str            # done, max_turns, context_limit, compaction_thrash, refusal, ...
    turns: int
    clearings: int = 0   # times old tool outputs were cleared
    summaries: int = 0   # times the conversation was summarized and started again


def request(messages: list, sandboxed: bool = True) -> dict:
    """One turn's request. cache_control: the API caches the prompt so far; the next turn reads it at 1/10 price."""
    tools = TOOLS if sandboxed else [bash_tool(sandboxed=False), *TOOLS[1:]]
    return dict(system=SYSTEM, tools=tools, messages=messages, max_tokens=8000,
                cache_control={"type": "ephemeral"}, output_config={"effort": "low"})


def size(claude: Claude, messages: list, sandboxed: bool) -> int:
    """The next request's prompt in tokens, counted by the API (free) the way the model will see it."""
    params = request(messages, sandboxed)
    return claude.count_tokens(system=params["system"], tools=params["tools"], messages=messages)


def run(task: str, claude: Claude, cwd: Path, *, label: str = "", log=print, box: Sandbox | None = None,
        window: int = WINDOW, mode: str = "full") -> Result:
    """box: the sandbox the shell runs in. Without one, every command waits for the user's yes.
    window: the context window, in tokens. mode, what happens past it (compact.MODES): none ends the task; clear
    clears old tool outputs, and ends the task if that isn't enough; full clears, then summarizes if needed."""
    sandboxed = box is not None
    messages = [{"role": "user", "content": task}]
    clearings = summaries = streak = 0
    for turn in range(1, MAX_TURNS + 1):
        response = claude.create(task=label, **request(messages, sandboxed))
        messages.append({"role": "assistant", "content": response.content})
        for block in response.content:
            if block.type == "text" and block.text.strip():
                log(f"agent: {block.text.strip()}")
        calls = [block for block in response.content if block.type == "tool_use"]
        if response.stop_reason != "tool_use" or not calls:
            return Result("done" if response.stop_reason == "end_turn" else response.stop_reason, turn,
                          clearings, summaries)

        results = []
        for call in calls:
            log(describe(call.name, call.input))
            output, is_error = run_tool(call.name, call.input, cwd, box)
            log(output if len(output) < 1500 else output[:1500] + "\n...")
            results.append({"type": "tool_result", "tool_use_id": call.id, "content": output, "is_error": is_error})
        messages.append({"role": "user", "content": results})

        tokens = size(claude, messages, sandboxed)
        if tokens <= window:
            streak = 0
            continue
        log(f"[context: {tokens:,} tokens, past the {window:,}-token window]")
        if mode == "none":
            return Result("context_limit", turn, clearings, summaries)

        messages, cleared = compact.clear_old_outputs(messages)  # step 1: clear old tool outputs
        if cleared:
            clearings += 1
            tokens = size(claude, messages, sandboxed)
            log(f"[cleared {cleared} old tool output{'s' * (cleared > 1)}: {tokens:,} tokens]")
            if tokens <= window:
                streak = 0
                continue
        if mode == "clear":
            log("[still past the window, and clearing is all this harness does: stopping]")
            return Result("context_limit", turn, clearings, summaries)

        if streak == THRASH:  # the guard: the window filled up again straight after each of the last summaries
            log(f"[the window filled up again straight after {THRASH} summaries in a row: stopping]")
            return Result("compaction_thrash", turn, clearings, summaries)
        ask = compact.summary_request(messages)  # step 2: summarize, and start again from the summary
        if size(claude, ask, sandboxed) > PROMPT_CEILING:
            return Result("context_limit", turn, clearings, summaries)
        summary = compact.summary_text(claude.create(task=label, kind="summary", **request(ask, sandboxed)))
        if not summary:
            log("[the summary came back empty: stopping]")
            return Result("compaction_thrash", turn, clearings, summaries)
        messages, read, named = compact.restart(task, summary, cwd, compact.touched_files(messages, cwd), window)
        summaries, streak = summaries + 1, streak + 1
        tokens = size(claude, messages, sandboxed)
        files = f"; files read again: {', '.join(read)}" if read else ""
        files += f"; named only: {', '.join(named)}" if named else ""
        log(f"[summary: the conversation starts again from the task and the summary, {tokens:,} tokens{files}]")
        log(f"summary: {summary}")
        if tokens > window:
            log("[the summary alone doesn't fit the window: stopping]")
            return Result("compaction_thrash", turn, clearings, summaries)
    return Result("max_turns", MAX_TURNS, clearings, summaries)
