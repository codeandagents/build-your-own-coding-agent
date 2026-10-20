"""The agent loop: send the conversation, run the tools the model asks for, repeat until it stops. When the
conversation no longer fits the context window, it is compacted (episode 5: agent/compact.py). A session starts with
the project's instructions and the agent's memory (episode 6: agent/memory.py)."""
from dataclasses import dataclass
from pathlib import Path

from . import compact, memory as mem
from .llm import Claude
from .sandbox import Sandbox
from .tools import TOOLS, also, bash_tool, describe, resolve, run_tool

SYSTEM = """You are a coding agent working in a software project on the user's machine.
Use the search tools (search_files, find_files) to look around, the file tools (read_file, write_file, edit_file) to
read and edit files, and the bash tool to run the tests. Work in small steps and check your work.
When the task is done, reply with a short summary of what you changed."""

MAX_TURNS = 25           # per request from the user: a task that isn't done by then is stopped (a looping agent is
                         # the main cost risk)
PROMPT_CEILING = 80_000  # tokens: no request is ever longer (Haiku 5.5's price is 5x above 100k)
WINDOW = 64_000          # tokens: the context window. Past it the conversation is compacted (episode 5); it sits
                         # below the ceiling, so the summary request still fits under it
THRASH = 3               # summaries in a row, each filled up again at once: stop (Claude Code: "after a few attempts")
FILE_TOOLS = ("read_file", "write_file", "edit_file")


@dataclass
class Result:
    stop: str            # done, max_turns, context_limit, compaction_thrash, refusal, ...
    turns: int
    clearings: int = 0   # times old tool outputs were cleared
    summaries: int = 0   # times the conversation was summarized and started again


def system(memory: Path | None) -> str:
    """The system prompt; with a memory folder, it says where the folder is and when to save to it."""
    return SYSTEM if memory is None else SYSTEM + "\n" + mem.PROMPT.format(folder=mem.where(memory))


def request(messages: list, sandboxed: bool = True, memory: Path | None = None) -> dict:
    """One turn's request. cache_control: the API caches the prompt so far; the next turn reads it at 1/10 price.
    With a memory folder, bash's description says the sandbox shares it, to read only."""
    tools = [bash_tool(sandboxed, memory is not None), *TOOLS[1:]]
    return dict(system=system(memory), tools=tools, messages=messages, max_tokens=8000,
                cache_control={"type": "ephemeral"}, output_config={"effort": "low"})


def size(claude: Claude, messages: list, sandboxed: bool, memory: Path | None = None) -> int:
    """The next request's prompt in tokens, counted by the API (free) the way the model will see it."""
    params = request(messages, sandboxed, memory)
    return claude.count_tokens(system=params["system"], tools=params["tools"], messages=messages)


def run(task: str, claude: Claude, cwd: Path, *, label: str = "", log=print, box: Sandbox | None = None,
        window: int = WINDOW, mode: str = "full", memory: Path | None = None, replies: tuple = ()) -> Result:
    """box: the sandbox the shell runs in. Without one, every command waits for the user's yes.
    window: the context window, in tokens. mode, what happens past it (compact.MODES): none ends the task; clear
    clears old tool outputs, and ends the task if that isn't enough; full clears, then summarizes if needed.
    memory: the agent's memory folder (episode 6), or None for none. replies: what the user says each time the agent
    stops, in order (code review sending the work back, say); the session ends when there are none left."""
    sandboxed, replies, asked, loaded = box is not None, list(replies), [task], set()
    messages = [mem.first_message(task, cwd, memory)]
    for line in mem.report(cwd, memory):
        log(line)
    clearings = summaries = streak = turns = total = 0
    with also(memory):  # the file tools may use the memory folder too, while this session runs
        while turns < MAX_TURNS:
            turns, total = turns + 1, total + 1
            response = claude.create(task=label, **request(messages, sandboxed, memory))
            messages.append({"role": "assistant", "content": response.content})
            for block in response.content:
                if block.type == "text" and block.text.strip():
                    log(f"agent: {block.text.strip()}")
            calls = [block for block in response.content if block.type == "tool_use"]
            if response.stop_reason != "tool_use" or not calls:
                if response.stop_reason == "end_turn" and replies:  # the user answers, and the session goes on
                    asked.append(replies.pop(0))
                    log(f"user: {asked[-1]}")
                    messages.append({"role": "user", "content": asked[-1]})
                    turns = 0
                    continue
                return Result("done" if response.stop_reason == "end_turn" else response.stop_reason, total,
                              clearings, summaries)

            results = []
            for call in calls:
                log(describe(call.name, call.input))
                output, is_error = run_tool(call.name, call.input, cwd, box)
                log(output if len(output) < 1500 else output[:1500] + "\n...")
                if call.name in FILE_TOOLS and not is_error:  # a subfolder's instructions, the first time it's used
                    found = mem.nested(cwd, resolve(cwd, call.input["path"]), call.name, loaded)
                    if found:
                        output = mem.attach(output, found, cwd)
                        log(f"[loaded {', '.join(mem.name(f, cwd) for f in found)}: the instructions for that folder]")
                results.append({"type": "tool_result", "tool_use_id": call.id, "content": output,
                                "is_error": is_error})
            messages.append({"role": "user", "content": results})

            tokens = size(claude, messages, sandboxed, memory)
            if tokens <= window:
                streak = 0
                continue
            log(f"[context: {tokens:,} tokens, past the {window:,}-token window]")
            if mode == "none":
                return Result("context_limit", total, clearings, summaries)

            messages, cleared = compact.clear_old_outputs(messages)  # step 1: clear old tool outputs
            if cleared:
                clearings += 1
                tokens = size(claude, messages, sandboxed, memory)
                log(f"[cleared {cleared} old tool output{'s' * (cleared > 1)}: {tokens:,} tokens]")
                if tokens <= window:
                    streak = 0
                    continue
            if mode == "clear":
                log("[still past the window, and clearing is all this harness does: stopping]")
                return Result("context_limit", total, clearings, summaries)

            if streak == THRASH:  # the guard: the window filled up again straight after each of the last summaries
                log(f"[the window filled up again straight after {THRASH} summaries in a row: stopping]")
                return Result("compaction_thrash", total, clearings, summaries)
            ask = compact.summary_request(messages)  # step 2: summarize, and start again from the summary
            if size(claude, ask, sandboxed, memory) > PROMPT_CEILING:
                return Result("context_limit", total, clearings, summaries)
            summary = compact.summary_text(claude.create(task=label, kind="summary",
                                                         **request(ask, sandboxed, memory)))
            if not summary:
                log("[the summary came back empty: stopping]")
                return Result("compaction_thrash", total, clearings, summaries)
            # the fresh start reads the instructions and the memory again, from disk (Claude Code reloads them too)
            messages, read, named = compact.restart("\n\n".join(asked), summary, cwd,
                                                    compact.touched_files(messages, cwd), window,
                                                    context=mem.context(cwd, memory))
            summaries, streak = summaries + 1, streak + 1
            tokens = size(claude, messages, sandboxed, memory)
            files = f"; files read again: {', '.join(read)}" if read else ""
            files += f"; named only: {', '.join(named)}" if named else ""
            log(f"[summary: the conversation starts again from the task and the summary, {tokens:,} tokens{files}]")
            log(f"summary: {summary}")
            if tokens > window:
                log("[the summary alone doesn't fit the window: stopping]")
                return Result("compaction_thrash", total, clearings, summaries)
    return Result("max_turns", total, clearings, summaries)
