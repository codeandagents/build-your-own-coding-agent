"""The tools the model can call: a shell (episode 1), and file tools modelled on Claude Code's Read, Write and Edit
(episode 2)."""
import os
import re
import signal
import subprocess
import sys
from pathlib import Path


def schema(required: dict, optional: dict | None = None) -> dict:
    return {"type": "object", "properties": {**required, **(optional or {})}, "required": list(required),
            "additionalProperties": False}


PATH = {"path": {"type": "string", "description": "The file's path, relative to the project directory."}}
TEXT = {"type": "string"}
RANGE = {"offset": {"type": "integer", "description": "The first line to read (1 = the first)."},
         "limit": {"type": "integer", "description": "How many lines to read."}}

TOOLS = [{
    "name": "bash",
    "description": ("Run a shell command in the project directory and get its output (stdout and stderr). "
                    "Use it to look around and run the tests; read and edit files with the file tools. "
                    "Each command runs in a fresh shell and times out after 60 seconds."),
    "input_schema": schema({"command": {"type": "string", "description": "The command to run."}}),
}, {
    "name": "read_file",
    "description": ("Read a text file, with line numbers. Reads up to 2000 lines from the start; "
                    "read a long file in ranges with offset and limit."),
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
}]

READ_LIMIT = 2000  # lines per read_file call, as in Claude Code's Read
TIMEOUT_S = 60
MAX_OUTPUT = 20_000  # characters: a guard against one command filling the context (episode 5 does it properly)
# Placeholders until episode 4 builds a real sandbox: refuse the obviously dangerous, and keep the agent off the rest
# of the machine (in the first baseline, 2026-10-16, Haiku ran `cd ~` and then `find /` when it felt lost).
ROOT = r"(/|/[a-zA-Z]|[a-zA-Z]:[\\/]?)(?=$|[\s;&|)])"  # a filesystem or drive root: / /c C:\ C:
BLOCKED = [r"\brm\s+-\w*r\w*\s+(/|~|\.\.)", r"\bgit\s+push\b", r"\b(curl|wget)\b", r"\bpip\s+install\b",
           r"\.env\b",
           r"\b(find|ls|du|tree|cd)\s+(-\S+\s+)*" + ROOT,      # whole-disk scans, or a cd to the root
           r"\b(grep|rg)\b[^|;&]*\s" + ROOT,                  # a search over the whole disk
           r"(?i)(/[a-z]/Users\b|[a-z]:[\\/]+Users\b|/home/)"]  # people's home folders
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
    env = {k: v for k, v in os.environ.items() if not SECRET.search(k)}
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    if home is not None:
        env["HOME"] = str(home)
    return env


def run_tool(name: str, args: dict, cwd: Path) -> tuple[str, bool]:
    """Returns (output, is_error)."""
    if name == "bash":
        return bash(args.get("command", ""), cwd)
    if name not in FILE_TOOLS:
        return f"Unknown tool: {name}", True
    try:
        return FILE_TOOLS[name](cwd, **args) or "(no output)", False
    except (OSError, ValueError, TypeError) as e:  # a refused edit, a missing file, a wrong argument
        return str(e), True


def describe(name: str, args: dict) -> str:
    """The call as one log line: a command as typed, a file tool as a call."""
    if name == "bash":
        return f"$ {args.get('command', '')}"
    options = [f"{k}={args[k]}" for k in ("offset", "limit", "replace_all") if k in args]
    return f"> {name}({', '.join([str(args.get('path', ''))] + options)})"


def cut(output: str) -> str:
    if len(output) <= MAX_OUTPUT:
        return output
    return output[:MAX_OUTPUT] + f"\n[... {len(output) - MAX_OUTPUT} more characters cut]"


def bash(command: str, cwd: Path) -> tuple[str, bool]:
    if any(re.search(pattern, command) for pattern in BLOCKED):
        return f"Blocked by the harness: {command}", True
    try:
        returncode, output = run_shell(command, cwd)
    except subprocess.TimeoutExpired:
        return f"Timed out after {TIMEOUT_S} s", True
    output = cut(output)
    if returncode:
        output += f"\n[exit code {returncode}]"
    return output or "(no output)", False


def resolve(cwd: Path, path: str) -> Path:
    """The model's path, kept to the project folder (the same rails as bash: no other folders, no .env)."""
    if os.name == "nt":
        path = re.sub(r"^/([a-zA-Z])/", r"\1:/", path)  # Git Bash's /c/... is C:/...
    full = (cwd / path).resolve()
    if not full.is_relative_to(cwd.resolve()) or re.search(r"\.env\b", str(full), re.IGNORECASE):
        raise ValueError(f"Blocked by the harness: {path}")
    return full


def read_text(full: Path, path: str) -> str:
    if not full.is_file():
        raise ValueError(f"No such file: {path}")
    with open(full, encoding="utf-8", newline="") as f:  # newline="": the file's own line ends, \r\n kept
        return f.read()


def read_file(cwd: Path, path: str, offset: int = 1, limit: int = READ_LIMIT) -> str:
    text = read_text(resolve(cwd, path), path)
    lines = text.removesuffix("\n").split("\n") if text else []
    first = max(int(offset), 1)
    shown = [line.removesuffix("\r") for line in lines[first - 1:first - 1 + int(limit)]]
    if not shown:
        return f"({path} has {len(lines)} lines)"
    return cut("\n".join(f"{n:>6}\t{line}" for n, line in enumerate(shown, first)))


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


FILE_TOOLS = {"read_file": read_file, "write_file": write_file, "edit_file": edit_file}


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
