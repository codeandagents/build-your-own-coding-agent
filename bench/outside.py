"""python -m bench.outside .runs/NAME.log: the agent's commands that may leave its work folder (.., absolute paths,
Git Bash's /tmp, a drive). Most hits are harmless (a cd to the work folder itself); read them and report the rest."""
import re
import sys

ABS = re.compile(r"(?<![\w.])(/[a-z]/|/tmp\b|/c/|[A-Za-z]:[\\/]|~/|\$HOME|/usr/|/etc/|/home/)")
UP = re.compile(r"(^|[\s'\"=(:])\.\.(/|\\|\s|$)")

task = rep = None
hits = []
with open(sys.argv[1], encoding="utf-8", errors="replace") as f:
    for line in f:
        m = re.match(r"=== (t\d+[\w-]*) \(repeat (\d+)\)", line)
        if m:
            task, rep = m.group(1), m.group(2)
            continue
        if re.match(r"\$ |> \w+\(", line):  # a command, or a file tool's call (not pytest's "> " source lines)
            cmd = line[2:].rstrip()
            reasons = [name for name, rx in (("abs", ABS), ("..", UP)) if rx.search(cmd)]
            if reasons:
                hits.append((task, rep, ",".join(reasons), cmd[:200]))
for task, rep, why, cmd in hits:
    print(f"{task} r{rep} [{why}] {cmd}")
print(f"{len(hits)} command(s) flagged")
