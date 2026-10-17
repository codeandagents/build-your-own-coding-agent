"""The tools the model can call. Episode 1 has one: a shell."""
import os
import re
import signal
import subprocess
import sys
from pathlib import Path

TOOLS = [{
    "name": "bash",
    "description": ("Run a shell command in the project directory and get its output (stdout and stderr). "
                    "Use it to list and read files, edit them, and run the tests. "
                    "Each command runs in a fresh shell and times out after 60 seconds."),
    "input_schema": {
        "type": "object",
        "properties": {"command": {"type": "string", "description": "The command to run."}},
        "required": ["command"],
        "additionalProperties": False,
    },
}]

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
    if name != "bash":
        return f"Unknown tool: {name}", True
    command = args.get("command", "")
    if any(re.search(pattern, command) for pattern in BLOCKED):
        return f"Blocked by the harness: {command}", True
    try:
        returncode, output = run_shell(command, cwd)
    except subprocess.TimeoutExpired:
        return f"Timed out after {TIMEOUT_S} s", True
    if len(output) > MAX_OUTPUT:
        output = output[:MAX_OUTPUT] + f"\n[... {len(output) - MAX_OUTPUT} more characters cut]"
    if returncode:
        output += f"\n[exit code {returncode}]"
    return output or "(no output)", False


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
