"""Memory (episode 6): what the agent knows when a session starts, and what it keeps for the next one. Claude Code has
two kinds (code.claude.com/docs/en/memory, read 2026-10-20): "CLAUDE.md files: instructions you write to give Claude
persistent context" and "Auto memory: notes Claude writes itself based on your corrections and preferences".

1. Project instructions: the project's CLAUDE.md files, or its AGENTS.md when it has none, go into the first message
   of every session. A subfolder's file joins the conversation the first time the agent reads a file in that folder.
2. Auto memory: a folder outside the project. Its index, MEMORY.md (the first 200 lines or 25KB), goes into the first
   message too; each memory is a file of its own, read when the agent needs it. The agent writes them with write_file
   and edit_file, and the system prompt says when: the one place outside the project the file tools may use. The
   sandbox shares the folder with the shell to read only: Claude Code's sandboxed shell reads "most of the machine"
   and writes only the project and a temp folder (code.claude.com/docs/en/sandboxing).

Both are context, not rules: the model reads them, and decides."""
from pathlib import Path

from .sandbox import inside

INDEX = "MEMORY.md"
INDEX_LINES, INDEX_BYTES = 200, 25 * 1024  # what of MEMORY.md is loaded: "the first 200 lines ... or the first 25KB"
CLAUDE_FILES = ("CLAUDE.md", ".claude/CLAUDE.md", "CLAUDE.local.md")  # any of these, and AGENTS.md isn't read
AGENTS_FILES = ("AGENTS.md", ".claude/AGENTS.md")

# The system prompt's memory section. Modelled on the docs: the four kinds of note ("user", "feedback", "project",
# "reference"), "Claude skips anything it can derive from the codebase ... It also skips anything your CLAUDE.md files
# already say", and the folder's layout ("a MEMORY.md index and one topic file per memory").
PROMPT = """
You have a memory that lasts from one session to the next: the folder {folder}. Its index, MEMORY.md, is in the \
first message of every session; each memory is a file of its own in that folder. Read a memory's file with read_file \
when its line in the index matters to your task.
Save a memory when the user corrects you or confirms an approach, or tells you something about the project that you \
couldn't learn from its code: a decision, a rule kept outside the repository, where to find something. Don't save \
what the code, its history or its instruction files already say, or what matters only to this session. Write one \
memory per file, starting with frontmatter (name, description, and type: user, feedback, project or reference), and \
give it one line in MEMORY.md: - [Title](file.md): what it's about. Save them with write_file and edit_file, using \
the folder's full path."""


def folder_files(folder: Path) -> list[Path]:
    """A folder's instruction files, as Claude Code picks them: its CLAUDE.md files, or else its AGENTS.md files."""
    claude = [folder / name for name in CLAUDE_FILES if (folder / name).is_file()]
    return claude or [folder / name for name in AGENTS_FILES if (folder / name).is_file()]


def read(path: Path) -> str:
    with open(path, encoding="utf-8", newline="") as f:
        return f.read().replace("\r\n", "\n")


def index(memory: Path) -> str:
    """MEMORY.md as a session sees it: the first 200 lines or 25KB, whichever comes first."""
    path = memory / INDEX
    if not path.is_file():
        return ""
    text = read(path)
    kept = "\n".join(text.split("\n")[:INDEX_LINES])
    kept = kept.encode("utf-8")[:INDEX_BYTES].decode("utf-8", errors="ignore")
    if len(kept) < len(text.rstrip("\n")):
        kept += f"\n[MEMORY.md goes on past {INDEX_LINES} lines or {INDEX_BYTES // 1024}KB: the rest isn't loaded]"
    return kept.rstrip("\n")


def name(path: Path, cwd: Path) -> str:
    return path.resolve().relative_to(cwd.resolve()).as_posix()


def where(memory: Path) -> str:
    """The memory folder's path as the agent sees it: the way the sandbox mounts it (C:\\work\\memory is
    /c/work/memory), which the file tools take too."""
    return inside(memory)


def context(cwd: Path, memory: Path | None) -> str:
    """What a session knows before the task: the project's instructions, and the memory's index."""
    parts = [f"Project instructions, from {name(path, cwd)}:\n{read(path).strip()}" for path in folder_files(cwd)]
    if memory is not None:
        saved, path = index(memory), f"{where(memory)}/{INDEX}"
        parts.append(f"Your memory's index, from {path}:\n{saved}" if saved else
                     f"Your memory's index, {path}, is empty: nothing has been saved yet.")
    return "\n\n".join(parts)


def report(cwd: Path, memory: Path | None) -> list[str]:
    """The harness's own lines, for the log: what the session starts with."""
    lines = [f"[project instructions: {name(path, cwd)}, {len(read(path)):,} characters]" for path in folder_files(cwd)]
    if memory is not None:
        saved = index(memory)
        count = len(saved.split("\n")) if saved else 0
        lines.append(f"[memory: {where(memory)}/{INDEX}, {count} line{'s' * (count != 1)}]" if saved
                     else f"[memory: {where(memory)}, empty]")
    return lines


def first_message(task: str, cwd: Path, memory: Path | None) -> dict:
    """The session's first message: the context (Claude Code sends it "as a user message after the system prompt"),
    then the task. With nothing to load, the task alone: episode 5's request, unchanged."""
    loaded = context(cwd, memory)
    if not loaded:
        return {"role": "user", "content": task}
    return {"role": "user", "content": [{"type": "text", "text": f"<context>\n{loaded}\n</context>"},
                                        {"type": "text", "text": task}]}


def nested(cwd: Path, path: Path, tool: str, loaded: set) -> list[Path]:
    """The instruction files of the folders between the project and a file the agent just used, not loaded yet.
    Claude Code loads a subfolder's CLAUDE.md "once Claude reads, writes, or edits another file in that subdirectory",
    and its AGENTS.md "when Claude opens a file there with the Read tool"."""
    root = cwd.resolve()
    try:
        inner = path.resolve().relative_to(root).parent
    except ValueError:  # outside the project (the memory folder)
        return []
    found = []
    for depth in range(1, len(inner.parts) + 1):
        folder = root.joinpath(*inner.parts[:depth])
        for file in folder_files(folder):
            agents = file.name == "AGENTS.md"
            if file.resolve() == path.resolve():  # it read the file itself: nothing to add, now or later
                loaded.add(file.resolve())
            elif file.resolve() not in loaded and (tool == "read_file" or not agents):
                loaded.add(file.resolve())
                found.append(file)
    return found


def attach(output: str, files: list[Path], cwd: Path) -> str:
    """A tool result with the subfolders' instructions after it."""
    for file in files:
        folder = name(file.parent, cwd) + "/"
        output += (f"\n\n<instructions from {name(file, cwd)}, which apply to the files in {folder}>\n"
                   f"{read(file).strip()}\n</instructions>")
    return output


def snapshot(memory: Path) -> dict[str, str]:
    """Every file in the memory folder, by name: to see what a session saved."""
    if not memory.is_dir():
        return {}
    return {p.relative_to(memory).as_posix(): read(p) for p in sorted(memory.rglob("*")) if p.is_file()}
