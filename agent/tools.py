"""The tools the model can call: a shell (episode 1), file tools modelled on Claude Code's Read, Write and Edit
(episode 2), search tools modelled on its Grep and Glob (episode 2 too), and Claude Code's limits on how much of a
tool's output reaches the model (episode 3: the context budget). The shell runs in a sandbox (episode 4). The file
tools may also use the agent's memory folder (episode 6), outside the project."""
import os
import re
import signal
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

from .sandbox import Sandbox


def schema(required: dict, optional: dict | None = None) -> dict:
    return {"type": "object", "properties": {**required, **(optional or {})}, "required": list(required),
            "additionalProperties": False}


PATH = {"path": {"type": "string", "description": "The file's path, relative to the project directory."}}
TEXT = {"type": "string"}
RANGE = {"offset": {"type": "integer", "description": "The first line to read (1 = the first)."},
         "limit": {"type": "integer", "description": "How many lines to read."}}
MODES = ("files_with_matches", "content", "count")  # search_files' output, as in Claude Code's Grep

BASH = ("Run a shell command in the project directory and get its output (stdout and stderr). "
        "Use it to run the tests and other programs. "
        # Claude Code's Bash tool steers the same way: without this sentence, 95% of the work stayed in bash
        "Don't use it to search, read or change files: search file contents with search_files (not grep "
        "or rg), find files by name with find_files (not find or ls), read with read_file (not cat, head, "
        "tail or sed -n), edit with edit_file (not sed -i or scripts) and create files with write_file "
        "(not echo or cat <<EOF). Each command runs in a fresh shell and times out after 60 seconds. "
        "Output over 30,000 characters is saved to a file: you get its path and the first 2,000 characters.")
# Claude Code's Bash tool tells the model about its sandbox too
WHERE = {True: (" Commands run in a sandbox: a Linux container with no network that shares only the project folder "
                "with the user's machine (its /tmp is its own)."),
         False: " There is no sandbox: the user approves each command before it runs."}


def bash_tool(sandboxed: bool = True) -> dict:
    return {"name": "bash", "description": BASH + WHERE[sandboxed],
            "input_schema": schema({"command": {"type": "string", "description": "The command to run."}})}


TOOLS = [bash_tool(), {
    "name": "read_file",
    "description": ("Read a text file, with line numbers: up to 2000 lines or 40,000 characters. A longer file "
                    "comes back as its first page, with a note on how to read on with offset and limit; a whole file "
                    "over 256 KB is refused (read a part, or search it)."),
    "input_schema": schema(PATH, RANGE),
}, {
    "name": "write_file",
    "description": "Create a file, or replace all of its content. To change part of a file, use edit_file.",
    "input_schema": schema({**PATH, "content": TEXT}),
}, {
    "name": "edit_file",
    "description": ("Replace text in a file. old_string must match the file exactly, indentation included, and occur "
                    "exactly once: if it occurs more often, add lines around it to make it unique, or set replace_all "
                    "to replace every occurrence. Read the file first."),
    "input_schema": schema({**PATH, "old_string": TEXT, "new_string": TEXT}, {"replace_all": {"type": "boolean"}}),
}, {
    "name": "search_files",
    "description": ("Search file contents for a regular expression (Python syntax). output_mode: files_with_matches "
                    "(the default) lists the files that match, content shows the matching lines as path:line:text "
                    "(context: lines around each), count gives the matches per file; up to 100 results, and offset "
                    "skips that many (the next page). Narrow it with path (a folder or one file) and glob (which "
                    "files: **/*.py; !tickets/** leaves them out)."),
    "input_schema": schema({"pattern": TEXT}, {"path": TEXT, "glob": TEXT,
                                               "output_mode": {"type": "string", "enum": list(MODES)},
                                               "ignore_case": {"type": "boolean"}, "context": {"type": "integer"},
                                               "offset": {"type": "integer"}}),
}, {
    "name": "find_files",
    "description": ("Find files by name with a glob pattern: **/*.py (any depth), docs/*.md, *.{json,csv}. Returns "
                    "their paths, sorted, up to 100."),
    "input_schema": schema({"pattern": TEXT}, {"path": TEXT}),
}]

READ_LIMIT = 2000  # lines per read_file call, as in Claude Code's Read
SEARCH_LIMIT = 100  # matches per search, files per find: the rest are counted, not shown
HIDDEN = re.compile(r"(^|/)(\.|__pycache__/)")  # .git, .pytest_cache, .env: not searched unless named as the path
TIMEOUT_S = 60
# The context budget (episode 3): Claude Code's limits (code.claude.com/docs/en/tools-reference, read 2026-10-18).
INLINE_MAX = 30_000     # characters of a result the model gets as is; a longer one is saved to a file
PREVIEW = 2_000         # ... and the model gets the file's path and this much of its start
FAILED_MAX = 10_000     # a failed command's output: its start and its end, this much in all, no file
PAGE_MAX = 40_000       # characters per read_file call: Claude Code's 25,000 tokens are an eighth of its 200k window;
                        # an eighth of our 80k ceiling (loop.PROMPT_CEILING) is 10,000 tokens, which we took to be
                        # 40,000 characters (4 a token). Measured in episode 5, this project's files run 1.7-2.4
                        # characters a token, so a full page is nearer 20,000 tokens: a quarter of the ceiling
WHOLE_MAX = 256 * 1024  # bytes: a whole file larger than this is refused (read a part, or search it), as in Claude Code
SAVED = ".outputs"      # long results go here, inside the project, where the file tools can read them
BENIGN = re.compile(r"(grep|rg|egrep|fgrep|find|diff|test|git\s+(diff|grep))\b|\[\s")  # exit 1 isn't a failure
# Episodes 1-3 refused commands that matched a list of patterns (curl, find /, .env...). The sandbox replaced them;
# bench/escape.py keeps the list, to show what it missed.
SECRET = re.compile(r"KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL", re.IGNORECASE)


def shell() -> list[str]:
    if os.name != "nt":
        return ["bash", "-c"]
    # On Windows, Git Bash. System32's bash.exe is WSL: a different machine.
    for candidate in (os.environ.get("BYOCA_BASH"), r"C:\Program Files\Git\bin\bash.exe",
                      r"C:\Program Files (x86)\Git\bin\bash.exe"):
        if candidate and Path(candidate).exists():
            return [candidate, "-c"]
    raise RuntimeError("Git Bash not found: install Git for Windows or set BYOCA_BASH")


def tool_env(home: Path | None = None) -> dict:
    """The agent's shell never sees API keys, and finds this environment's python and pytest first.
    HOME is the project folder, so `cd ~` lands there and not in the user's own files."""
    env = {k: v for k, v in os.environ.items() if not SECRET.search(k) and k != "OLDPWD"}  # ep02 runs: `cd "$OLDPWD"`
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    if home is not None:
        env["HOME"] = str(home)
    return env


def run_tool(name: str, args: dict, cwd: Path, box: Sandbox | None = None) -> tuple[str, bool]:
    """Returns (output, is_error)."""
    if name == "bash":
        return bash(args.get("command", ""), cwd, box)
    if name not in FILE_TOOLS:
        return f"Unknown tool: {name}", True
    try:
        output = FILE_TOOLS[name](cwd, **args) or "(no output)"
        return (output if name == "read_file" else fit(output, cwd, name)), False  # read_file pages itself
    except (OSError, ValueError, TypeError, re.error) as e:  # a refused edit, a missing file, a wrong argument or regex
        return f"Bad pattern: {e}" if isinstance(e, re.error) else str(e), True


def describe(name: str, args: dict) -> str:
    """The call as one log line: a command as typed, a file tool as a call."""
    if name == "bash":
        return f"$ {args.get('command', '')}"
    first = "pattern" if "pattern" in args else "path"
    options = [f"{k}={args[k]}" for k in ("path", "glob", "output_mode", "ignore_case", "context", "offset", "limit",
                                          "replace_all") if k in args and k != first]
    return f"> {name}({', '.join([str(args.get(first, ''))] + options)})"


def fit(output: str, cwd: Path, tool: str) -> str:
    """A result too long for the context goes to a file in the project, and the model gets its path and its start:
    Claude Code's way. It reads on with read_file or search_files."""
    if len(output) <= INLINE_MAX:
        return output
    folder = cwd / SAVED
    folder.mkdir(exist_ok=True)
    name = f"{SAVED}/{tool}-{len(list(folder.iterdir())) + 1:03}.txt"
    (cwd / name).write_text(output, encoding="utf-8", newline="")
    return (f"Output too large ({len(output.encode()) / 1024:.1f}KB). Full output saved to: {name}\n\n"
            f"Preview (first 2KB):\n{output[:PREVIEW]}\n...")


def ends(output: str) -> str:
    """A failed command's output: its start and its end (the error is often at the end), as in Claude Code."""
    if len(output) <= FAILED_MAX:
        return output
    half = FAILED_MAX // 2
    return f"{output[:half]}\n[... {len(output) - 2 * half} characters cut from the middle ...]\n{output[-half:]}"


def bash(command: str, cwd: Path, box: Sandbox | None = None) -> tuple[str, bool]:
    """In the sandbox every command runs: the container is the boundary. Without one, the user approves each."""
    if box is None and not approve(command):
        return "Not run: there is no sandbox, and the user didn't approve this command.", True
    try:
        returncode, output = box.run(command, TIMEOUT_S) if box else run_shell(command, cwd)
    except subprocess.TimeoutExpired:
        return f"Timed out after {TIMEOUT_S} s", True
    last = re.split(r"\|\||&&|[|;\n]", command.strip())[-1].strip()  # whose exit code the shell returns
    failed = returncode != 0 and not (returncode == 1 and BENIGN.match(last))  # grep: exit 1 = no match
    output = ends(output) if failed else fit(output, cwd, "bash")
    if returncode:
        output += f"\n[exit code {returncode}]"
    return output or "(no output)", False


def approve(command: str) -> bool:
    """The permission prompt for a command outside the sandbox. Nobody at the keyboard (a benchmark run) means no."""
    return sys.stdin.isatty() and input("Run it outside the sandbox? [y/N] ").strip().lower() == "y"


OUTSIDE: list[Path] = []  # folders outside the project the file tools may use too: the agent's memory (episode 6)


@contextmanager
def also(folder: Path | None):
    """While a session runs, the file tools may read and write this folder too (its memory)."""
    if folder is None:
        yield
        return
    OUTSIDE.append(folder.resolve())
    try:
        yield
    finally:
        OUTSIDE.remove(folder.resolve())


def resolve(cwd: Path, path: str) -> Path:
    """The model's path, kept to the project folder (and its memory folder) and away from .env files. The file tools
    run on this machine, outside the sandbox (as Claude Code's do): this check is their permission rule."""
    if os.name == "nt":
        path = re.sub(r"^/([a-zA-Z])/", r"\1:/", path)  # Git Bash's /c/... is C:/...
    full = (cwd / path).resolve()
    if not allowed(cwd, full):
        raise ValueError(f"Blocked by the harness: {path}")
    return full


def allowed(cwd: Path, full: Path) -> bool:
    inside = full.is_relative_to(cwd.resolve()) or any(full.is_relative_to(folder) for folder in OUTSIDE)
    return inside and not re.search(r"\.env\b", str(full), re.IGNORECASE)


def shown(cwd: Path, full: Path) -> str:
    """A path as the model sees it: relative in the project, in full outside it (the memory folder)."""
    root = cwd.resolve()
    return full.relative_to(root).as_posix() if full.is_relative_to(root) else full.as_posix()


def read_text(full: Path, path: str) -> str:
    if not full.is_file():
        raise ValueError(f"No such file: {path}")
    with open(full, encoding="utf-8", newline="") as f:  # newline="": the file's own line ends, \r\n kept
        return f.read()


def read_file(cwd: Path, path: str, offset: int | None = None, limit: int | None = None) -> str:
    """Up to READ_LIMIT lines and PAGE_MAX characters. A whole file that's longer comes back as its first page with
    Claude Code's PARTIAL notice; a range that's longer is refused, saying how many lines fit."""
    full, whole = resolve(cwd, path), offset is None and limit is None
    if whole and full.is_file() and full.stat().st_size > WHOLE_MAX:
        raise ValueError(f"{path} is {full.stat().st_size / 1024:.1f} KB, more than a whole read allows "
                         f"({WHOLE_MAX // 1024} KB): read a part with offset and limit, or search it with search_files")
    text = read_text(full, path)
    lines = text.removesuffix("\n").split("\n") if text else []
    first = max(int(offset or 1), 1)
    wanted = [line.removesuffix("\r") for line in lines[first - 1:first - 1 + int(limit or READ_LIMIT)]]
    if not wanted:
        return f"({path} has {len(lines)} lines)"
    page, size = [], -1
    for n, line in enumerate(wanted, first):
        size += len(row := f"{n:>6}\t{line}") + 1
        if size > PAGE_MAX:
            break
        page.append(row)
    last = first + len(page) - 1
    if len(page) == len(wanted) and (not whole or last == len(lines)):
        return "\n".join(page)
    if not page:
        raise ValueError(f"Line {first} of {path} alone is over {PAGE_MAX:,} characters: search it with search_files")
    if not whole:
        raise ValueError(f"Lines {first}-{first + len(wanted) - 1} of {path} are more than {PAGE_MAX:,} characters: "
                         f"read fewer (offset={first} limit={len(page)} fits), or search it with search_files")
    return "\n".join(page) + (
        f"\n\n[PARTIAL view of {path}: showing lines 1-{last} of {len(lines)} total ({len(text):,} characters, "
        f"cap {PAGE_MAX:,} per read). Call read_file with offset={last + 1} limit={last} for the next page, or "
        f"search_files to find a specific section. Do NOT answer from this page alone if the answer may be further "
        f"in the file.]")


def write_file(cwd: Path, path: str, content: str) -> str:
    full = resolve(cwd, path)
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8", newline="")  # UTF-8, and no \n -> \r\n on Windows
    return f"Wrote {path} ({len(content)} characters)"


def edit_file(cwd: Path, path: str, old_string: str, new_string: str, replace_all: bool = False) -> str:
    full = resolve(cwd, path)
    text = read_text(full, path)
    if not old_string or old_string == new_string:
        raise ValueError("old_string must be non-empty and differ from new_string (write_file creates a file)")
    count = text.count(old_string)
    if not count and "\r\n" in text:  # Windows line ends, which read_file doesn't show
        old_string, new_string = old_string.replace("\n", "\r\n"), new_string.replace("\n", "\r\n")
        count = text.count(old_string)
    if not count:
        raise ValueError(f"old_string not found in {path}: it must match the file exactly, indentation included")
    if count > 1 and not replace_all:
        raise ValueError(f"old_string occurs {count} times in {path}: add lines around it to make it unique, "
                         "or set replace_all to replace every occurrence")
    line = text[:text.index(old_string)].count("\n") + 1
    full.write_text(text.replace(old_string, new_string), encoding="utf-8", newline="")
    return f"Edited {path}: {count} replacement{'s' if count > 1 else ''}, from line {line}"


def search_files(cwd: Path, pattern: str, path: str = ".", glob: str = "**/*", output_mode: str = MODES[0],
                 ignore_case: bool = False, context: int = 0, offset: int = 0) -> str:
    if output_mode not in MODES:
        raise ValueError(f"output_mode must be one of: {', '.join(MODES)}")
    rx = re.compile(pattern, re.IGNORECASE if ignore_case else 0)
    bang, glob = ("!", glob[1:]) if glob.startswith("!") else ("", glob)
    targets = files(cwd, path, bang + (glob if "/" in glob else "**/" + glob))  # as in rg, *.py means at any depth
    hits = {}
    for name, full in targets:
        with open(full, encoding="utf-8", errors="replace", newline="") as f:
            text = f.read()
        lines = [line.removesuffix("\r") for line in text.split("\n")]
        if "\0" not in text and (found := [i for i, line in enumerate(lines) if rx.search(line)]):  # \0: binary
            hits[name] = lines, found
    total, skip = sum(len(found) for _, found in hits.values()), max(int(offset), 0)
    if not hits:
        return f"No matches in {len(targets)} files"
    if skip >= (total if output_mode == "content" else len(hits)):
        return "No entries at this offset"  # as in Claude Code's Grep: the pattern does match, earlier
    narrow = "the pattern, path or glob"
    if output_mode == "files_with_matches":
        return capped(list(hits), "files", narrow, skip)
    if output_mode == "count":
        counts = [f"{name}:{len(found)}" for name, (_, found) in hits.items()]
        return capped(counts, "files", narrow, skip) + f"\n{total} matches in {len(hits)} files"
    first, shown, left = skip, [], SEARCH_LIMIT
    for name, (lines, found) in hits.items():
        keep, skip = found[skip:][:max(left, 0)], max(skip - len(found), 0)
        keep, left = set(keep), left - len(keep)
        near = {j for i in keep for j in range(max(i - context, 0), min(i + context + 1, len(lines)))}
        for j in sorted(near):
            if context and shown and j - 1 not in near:
                shown.append("--")
            mark = ":" if j in keep else "-"  # path:line:text for a match, path-line-text around it
            shown.append(f"{name}{mark}{j + 1}{mark}{lines[j]}")
    rest = total - first - SEARCH_LIMIT
    more = f"\n[{rest} more matches not shown: narrow {narrow}, or offset={first + SEARCH_LIMIT} for the next page]"
    return "\n".join(shown) + (more if rest > 0 else "")


def find_files(cwd: Path, pattern: str, path: str = ".") -> str:
    found = [name for name, _ in files(cwd, path, pattern)]
    return capped(found, "files", "the pattern or path") if found else "No files found"


def capped(items: list[str], what: str, narrow: str, offset: int | None = None) -> str:
    """Up to SEARCH_LIMIT items from offset: search_files pages on with offset, find_files doesn't (Claude Code's Glob
    has no offset either)."""
    start = offset or 0
    rest = len(items) - start - SEARCH_LIMIT
    page = "" if offset is None else f", or offset={start + SEARCH_LIMIT} for the next page"
    more = f"\n[{rest} more {what} not shown: narrow {narrow}{page}]"
    return "\n".join(items[start:start + SEARCH_LIMIT]) + (more if rest > 0 else "")


def files(cwd: Path, path: str, pattern: str) -> list[tuple[str, Path]]:
    """The files under path that match a glob (!glob: all but those), as (path in the project, full path), sorted by
    path (Claude Code's Glob sorts by age; here every work copy is new). No hidden folders below path (named as the
    path, .outputs is searched); the file tools' rails."""
    base = resolve(cwd, path)
    if base.is_file():
        return [(shown(cwd, base), base)]
    if not base.is_dir():
        raise ValueError(f"No such file or folder: {path}")
    if re.match(r"!?([a-zA-Z]:)?[\\/]", pattern):
        raise ValueError(f"The pattern must be relative to path (the project by default): {pattern}")

    def matching(glob: str) -> set[tuple[str, Path]]:
        glob += "/*" if glob.endswith("**") else ""  # tickets/** = the files in it (Python 3.12's ** finds folders)
        return {(shown(cwd, full), full) for p in braces(glob)
                for full in map(Path.resolve, base.glob(p)) if full.is_file() and allowed(cwd, full)}

    found = matching("**/*") - matching(pattern[1:]) if pattern.startswith("!") else matching(pattern)
    return sorted(f for f in found if not HIDDEN.search(f[1].relative_to(base).as_posix()))


def braces(pattern: str) -> list[str]:
    """*.{json,csv} -> *.json, *.csv: pathlib's glob has no braces."""
    m = re.search(r"\{([^{}]*)\}", pattern)
    if not m:
        return [pattern]
    return [p for alt in m[1].split(",") for p in braces(pattern[:m.start()] + alt + pattern[m.end():])]


FILE_TOOLS = {"read_file": read_file, "write_file": write_file, "edit_file": edit_file,
              "search_files": search_files, "find_files": find_files}


def run_shell(command: str, cwd: Path, timeout: float = TIMEOUT_S) -> tuple[int, str]:
    """Run one command; on timeout, kill everything it started (a pipeline's processes hold its output open).
    Windows: a job object, since Git Bash's processes drop out of the Windows process tree."""
    flags = {"creationflags": CREATE_SUSPENDED} if os.name == "nt" else {"start_new_session": True}
    with subprocess.Popen(shell() + [command], cwd=cwd, env=tool_env(cwd), stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", **flags) as proc:
        job = _Job(proc) if os.name == "nt" else None
        try:
            out, err = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            if job:
                job.kill()
            else:
                os.killpg(proc.pid, signal.SIGKILL)
            proc.communicate()
            raise
        finally:
            if job:
                job.close()  # also ends anything the command left running in the background
    return proc.returncode, out + err


CREATE_SUSPENDED = 0x4

if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    class _Limits(ctypes.Structure):  # JOBOBJECT_EXTENDED_LIMIT_INFORMATION
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD), ("IoInfo", ctypes.c_ulonglong * 6),
                    ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

    class _Job:
        """The command's process goes into a job (started suspended, so nothing escapes before); every process it
        starts joins the job too. Closing the job kills them all."""
        KILL_ON_JOB_CLOSE = 0x2000
        EXTENDED_LIMITS = 9

        def __init__(self, proc: subprocess.Popen):
            k32, ntdll = ctypes.WinDLL("kernel32", use_last_error=True), ctypes.WinDLL("ntdll")
            k32.CreateJobObjectW.restype = wintypes.HANDLE
            self.k32, self.handle = k32, k32.CreateJobObjectW(None, None)
            limits = _Limits(LimitFlags=self.KILL_ON_JOB_CLOSE)
            ok = (self.handle
                  and k32.SetInformationJobObject(wintypes.HANDLE(self.handle), self.EXTENDED_LIMITS,
                                                  ctypes.byref(limits), ctypes.sizeof(limits))
                  and k32.AssignProcessToJobObject(wintypes.HANDLE(self.handle), wintypes.HANDLE(int(proc._handle))))
            ntdll.NtResumeProcess(wintypes.HANDLE(int(proc._handle)))  # resume even if the job failed
            if not ok:
                proc.kill()
                raise OSError(f"could not put the command in a job object (error {ctypes.get_last_error()})")

        def kill(self) -> None:
            self.k32.TerminateJobObject(wintypes.HANDLE(self.handle), 1)

        def close(self) -> None:
            if self.handle:
                self.k32.CloseHandle(wintypes.HANDLE(self.handle))
                self.handle = None
