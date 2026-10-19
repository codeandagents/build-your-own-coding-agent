"""Compaction (episode 5): what the loop does when the conversation no longer fits its context window. Claude Code's
way (code.claude.com/docs/en/how-claude-code-works, "When context fills up", read 2026-10-19): "It clears older tool
outputs first, then summarizes the conversation if needed."

1. Clear: every tool result but the newest KEEP becomes a one-line note of what it was. The model's own words stay.
2. Summarize, if that wasn't enough: one more request asks the model to summarize its work under the headings Claude
   Code's docs list, and the conversation starts again from the task, that summary, and the files it touched last.
3. A guard (in loop.py): when the window fills up again straight after each summary, the task stops instead of looping.

The functions here only rebuild the conversation; loop.py decides when, and sends the requests."""
from pathlib import Path

from .tools import describe, read_file, resolve

MODES = ("none", "clear", "full")  # no compaction (a full window ends the task), clearing only, clearing + summary
KEEP = 3              # the newest tool results stay whole (the API's own tool-result clearing keeps 3 by default)
CLEAR_MIN = 500       # characters: a shorter result stays (its note would be about as long)
CLEARED = "[Cleared to save context"
REREAD_FILES = 5      # after a summary, up to five files read or edited come back, the most recently modified first
REREAD_SHARE = 8      # ... within an eighth of the window (Claude Code: 5 files of up to 5,000 tokens each)
CHARS_PER_TOKEN = 2   # measured on the benchmark's files (1.7-2.4): only to choose which files fit

# The headings are the six things Claude Code's docs say its summary keeps (code.claude.com/docs/en/context-window).
SUMMARY = """Your context window is full. Everything above will be replaced by a summary that you write now, so write \
it now and don't call any tools: it is all you will have of this work. Use these headings:
1. Request and intent: what the user asked for, with every requirement.
2. Key technical concepts: how the code involved works.
3. Files and code: each file you examined or changed and why, with the exact snippets, values and wording the task \
depends on (quote them).
4. Errors and fixes: what went wrong, and how you fixed it.
5. Pending tasks: what is left to do.
6. Current work: what you were doing just now, and your next step."""

RESTART = ("This conversation was compacted to fit the context window. What came before is replaced by the summary "
           "below, which you wrote. Carry on with the task from where you left off.")


def kind(block) -> str:
    return block["type"] if isinstance(block, dict) else block.type


def tool_results(messages: list) -> list[tuple[int, int]]:
    """Where each tool result is: (message index, block index), oldest first."""
    return [(i, j) for i, m in enumerate(messages) if m["role"] == "user" and isinstance(m["content"], list)
            for j, block in enumerate(m["content"]) if kind(block) == "tool_result"]


def tool_calls(messages: list) -> dict:
    """Each tool call's (name, input), by its id."""
    return {block.id: (block.name, block.input) for m in messages if m["role"] == "assistant"
            for block in m["content"] if not isinstance(block, dict) and block.type == "tool_use"}


def clear_old_outputs(messages: list) -> tuple[list, int]:
    """Step 1: a new conversation in which the old tool results are notes. Returns it and how many were cleared.

    Editing an earlier turn invalidates the thinking blocks that come after it (Haiku 5.5's preserved thinking: a
    block is valid only while everything before it is unchanged), so those are dropped; the model's text and tool
    calls stay."""
    calls, new, cleared, first = tool_calls(messages), list(messages), 0, None
    for i, j in tool_results(messages)[:-KEEP]:
        block = new[i]["content"][j]
        text = block["content"]
        if text.startswith(CLEARED) or len(text) < CLEAR_MIN:
            continue
        name, args = calls.get(block["tool_use_id"], ("a tool", {}))
        call = describe(name, args).removeprefix("$ ").removeprefix("> ")
        call = call if len(call) <= 200 else call[:200] + "..."
        note = f"{CLEARED}: the output of {call}, {len(text):,} characters. Run it again if you need it.]"
        content = list(new[i]["content"])
        content[j] = {**block, "content": note}
        new[i] = {**new[i], "content": content}
        cleared += 1
        first = i if first is None else first
    if first is not None:
        new = [m if k < first or m["role"] != "assistant" else
               {**m, "content": [b for b in m["content"] if kind(b) not in ("thinking", "redacted_thinking")]}
               for k, m in enumerate(new)]
    return new, cleared


def summary_request(messages: list) -> list:
    """Step 2's request: the conversation as it is, and the summary instruction after the last tool results (nothing
    earlier changes, so the cache and the thinking blocks stay valid)."""
    last = messages[-1]
    content = last["content"] if isinstance(last["content"], list) else [{"type": "text", "text": last["content"]}]
    return messages[:-1] + [{**last, "content": [*content, {"type": "text", "text": SUMMARY}]}]


def summary_text(response) -> str:
    return "\n".join(block.text for block in response.content if block.type == "text").strip()


def touched_files(messages: list, cwd: Path) -> list[str]:
    """The files the model read or edited with the file tools, the most recently modified first."""
    found = {}
    for name, args in tool_calls(messages).values():
        if name in ("read_file", "write_file", "edit_file") and args.get("path"):
            try:
                full = resolve(cwd, args["path"])
            except ValueError:  # a path outside the project: the tool refused it
                continue
            if full.is_file():
                found[full.relative_to(cwd.resolve()).as_posix()] = full.stat().st_mtime
    return sorted(found, key=found.get, reverse=True)


def restart(task: str, summary: str, cwd: Path, files: list[str], window: int) -> tuple[list, list[str], list[str]]:
    """The new conversation: the task in the user's words, the summary, and the files the model touched last, read
    again as they are now. A file that doesn't fit what's left of the re-read share is named, not read.
    Returns the conversation, the files read again, and the files only named."""
    room, read, named, parts = window // REREAD_SHARE, [], [], []
    for path in files[:REREAD_FILES]:
        try:
            text = read_file(cwd, path)
        except (OSError, ValueError):
            continue
        if len(text) // CHARS_PER_TOKEN <= room:
            room -= len(text) // CHARS_PER_TOKEN
            read.append(path)
            parts.append(f"\n{path}:\n{text}")
        else:
            named.append(path)
            parts.append(f"\n{path}: too long to include, read it again if you need it.")
    text = f"{task}\n\n{RESTART}\n\n<summary>\n{summary}\n</summary>"
    if parts:
        text += "\n\nThe files you read or edited most recently, as they are now:\n" + "\n".join(parts)
    return [{"role": "user", "content": text}], read, named
