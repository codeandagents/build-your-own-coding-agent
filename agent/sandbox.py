"""The sandbox (episode 4): each task's shell runs in a Linux container that shares one folder with this machine, the
project, and has no network. Leaving the folder, reaching the network or reading this machine's secrets isn't refused
by a rule that matches the command's text: from inside the container, there is nothing to reach.

Build the image once: docker build -t byoca-sandbox sandbox"""
import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path

IMAGE = "byoca-sandbox"
TIMED_OUT = 124  # the exit code of coreutils' `timeout` when it had to stop the command


def available() -> str | None:
    """None when the sandbox can start; otherwise, why not."""
    if not shutil.which("docker"):
        return "Docker isn't installed"
    done = subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True, text=True, errors="replace")
    if "No such image" in done.stderr:
        return f"the {IMAGE} image isn't built: docker build -t {IMAGE} sandbox"
    return f"Docker isn't running ({done.stderr.strip().splitlines()[0]})" if done.returncode else None


def inside(folder: Path) -> str:
    """The folder's path in the container: the same path, written the Git Bash way on Windows (C:\\work\\t01 is
    /c/work/t01), so a path the agent sees in `pwd` works in the file tools too."""
    return re.sub(r"^([A-Za-z]):", lambda m: "/" + m[1].lower(), folder.resolve().as_posix())


class Sandbox:
    """One container per task; each command runs in it in a fresh bash (docker exec).
    memory (episode 6): the agent's memory folder, shared read-only, as Claude Code's sandboxed shell can read its
    memory but not write it (the file tools write it)."""

    def __init__(self, folder: Path, memory: Path | None = None):
        self.name, self.workdir = f"byoca-{uuid.uuid4().hex[:8]}", inside(folder)
        shared = ["--volume", f"{memory.resolve()}:{inside(memory)}:ro"] if memory else []
        docker("run", "--detach", "--rm", "--name", self.name,
               "--network", "none",                                # no network at all
               "--read-only", "--tmpfs", "/tmp:exec,mode=1777",    # nothing is writable but the project and /tmp
               "--volume", f"{folder.resolve()}:{self.workdir}",   # the one folder it shares with this machine
               *shared,                                            # and the memory, to read only
               "--workdir", self.workdir, "--env", f"HOME={self.workdir}",
               "--user", user(), "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
               "--pids-limit", "512", "--memory", "2g",            # a runaway command can't take the machine down
               IMAGE, "sleep", "infinity")

    def run(self, command: str, timeout: float) -> tuple[int, str]:
        """Run one command; at the timeout, `timeout` stops it and everything it started."""
        done = subprocess.run(["docker", "exec", self.name, "timeout", "--kill-after=5", str(timeout),
                               "bash", "-c", command],
                              capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout + 30)
        if done.returncode == TIMED_OUT:
            raise subprocess.TimeoutExpired(command, timeout)
        return done.returncode, done.stdout + done.stderr

    def close(self) -> None:
        subprocess.run(["docker", "rm", "--force", self.name], capture_output=True)

    def __enter__(self) -> "Sandbox":
        return self

    def __exit__(self, *_) -> None:
        self.close()


def user() -> str:
    """Your own user id on Linux and macOS, so the files the agent writes are yours; any user on Windows."""
    return f"{os.getuid()}:{os.getgid()}" if hasattr(os, "getuid") else "1000:1000"


def docker(*args: str) -> str:
    done = subprocess.run(["docker", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if done.returncode:
        raise RuntimeError(f"docker {args[0]} failed: {done.stderr.strip()}")
    return done.stdout
