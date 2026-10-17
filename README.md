# Build Your Own Claude Code: a coding agent from scratch, in Python

The code behind the series **Build Your Own Claude Code** on the
[Code & Agents](https://www.youtube.com/@CodeAndAgents) YouTube channel. Each episode adds one part of a coding
agent's *harness* (the loop, tools, the sandbox, context, memory, planning, verification, subagents...) and
re-runs the same benchmark with the same small model, so you can see what each part is worth. Every run in the
videos was made with this code; the terminal output on screen is real.

Not affiliated with Anthropic. "Claude Code" describes the kind of tool built here.

| Tag | Episode | What the harness has |
|---|---|---|
| [`ep01`](../../tree/ep01) | 1. A coding agent is a loop | the agent loop and one tool, `bash`; the benchmark and its baseline |

## What's in it

```
agent/loop.py       the agent loop: send the conversation, run the tools the model asks for, repeat
agent/tools.py      the one tool: bash, with placeholder safety rails (see below)
agent/llm.py        the model client, wrapped in spend guards: budget, ledger, record/replay
bench/project/      PetClinic Lite, the app the agent works on (a vet clinic in Auckland: 115 files, 153 tests)
bench/tasks/        15 tasks; each has a prompt (task.md) and hidden tests (check/), added only to score it
bench/run.py        run the agent on the tasks and score it
bench/board.py      print a run's scoreboard
results/            the scoreboards the videos show (ep01.jsonl = the episode-1 baseline)
```

## Run it

You need [uv](https://docs.astral.sh/uv/) and Python 3.12 or newer. On Windows, the agent's shell is Git Bash
(Git for Windows); elsewhere, bash. Developed and run on Windows 11 with Python 3.14.

```bash
uv sync
uv run pytest -q                          # the harness's own tests: offline, no key needed
uv run python -m bench.selfcheck          # every task is fair: tests pass at the start, the hidden check fails
uv run python -m bench.board results/ep01.jsonl   # the episode-1 scoreboard, no key needed
```

With an Anthropic API key (`BYOCA_API_KEY`, or the usual `ANTHROPIC_API_KEY`):

```bash
uv run python -m bench.run --plan                     # free: counts the first request's tokens, estimates the cost
uv run python -m bench.run --tasks t01 --brief        # one task, in short, coloured output
uv run python -m bench.run --repeat 3 --label mine    # the whole benchmark, 3 tries per task
uv run python -m agent "your task" --cwd path/to/a/project
```

The model is Claude Haiku 5.5 with effort `low`, fixed for the whole series: only the harness changes. The loop has
the same shape on any provider whose API has tool calling; this code talks to Anthropic's Messages API
(`agent/llm.py` and `agent/loop.py`).

## What it costs

On 2026-10-17, one try of a task cost about $0.006 and the whole benchmark (15 tasks, 3 tries) $0.28. Prices change
with every model release: check your provider's pricing page. The guards in `agent/llm.py`:
- a total budget (`budget_usd` in `.runs/config.json`, default $5) and a cap per run (`--run-budget`, default $0.50),
  both checked before every request;
- a ledger of every request's tokens and cost, `.runs/ledger.jsonl`;
- record/replay: every response is saved in `.runs/cassettes/`, and the same request again is read from disk, free;
- 25 turns per task, and a stop before a prompt grows past 80,000 tokens.

## Safety: read this before you run it

**The agent runs shell commands on your computer.** Episode 1's harness has placeholder rails only, until episode 4
builds a sandbox: it refuses a few obviously dangerous commands (`rm -r` on a root, `git push`, `curl`, `pip install`,
anything that mentions `.env`, whole-disk scans, paths into home folders), sets `HOME` to the folder it works in,
removes variables whose names look like keys or tokens from its environment, and stops a command after 60 seconds.
The benchmark gives it a fresh copy of the project for every task. That is not a sandbox. In our first baseline the agent listed the home folder
and then searched the whole disk, unprompted. If you're unsure, run it in a virtual machine or a container.

## License

[MIT](LICENSE).
