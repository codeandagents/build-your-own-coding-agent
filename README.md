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
| [`ep02`](../../tree/ep02) | 2. Claude Code's tools | `read_file`, `write_file`, `edit_file`, `search_files` (a regex search: the files that match by default, or their lines, or counts) and `find_files` (files that match a glob) next to `bash`, modelled on Claude Code's Read, Write, Edit, Grep and Glob, and bash's description steering file work and searches to them. Its steps: [`ep02-tools-only`](../../tree/ep02-tools-only) (the file tools alone), [`ep02-steer`](../../tree/ep02-steer) (plus the steering sentence), [`ep02-search-lines`](../../tree/ep02-search-lines) (plus a search that always printed the matching lines) |
| [`ep03`](../../tree/ep03) | 3. The context budget | Claude Code's limits on how much of a tool's output reaches the model, and how it gets the rest: a result over 30,000 characters is saved to a file in the project's `.outputs/` folder (the model gets its path and the first 2,000 characters), a failed command keeps its first and last 5,000 characters, `read_file` reads up to 40,000 characters a call and returns a longer file as pages with a "PARTIAL view" notice, and `search_files` pages on with `offset` |
| [`ep04`](../../tree/ep04) | 4. A sandbox | the shell runs in a Docker container per task, with no network and one folder shared with your machine: the project; without Docker, every command waits for your yes. It replaces episodes 1-3's list of blocked patterns (`bench.escape` compares the two) |

Each episode's follow-along notes (every command the video runs, and what to look for) are in
[`docs/follow-along/`](docs/follow-along/): [episode 1](docs/follow-along/ep01.md),
[episode 2](docs/follow-along/ep02.md), [episode 3](docs/follow-along/ep03.md).

## What's in it

```
agent/loop.py       the agent loop: send the conversation, run the tools the model asks for, repeat
agent/tools.py      the tools: bash, read_file, write_file, edit_file, search_files and find_files, and the context
                    budget (how much of their output the model sees)
agent/sandbox.py    the sandbox bash runs in: one Docker container per task (see Safety below)
sandbox/Dockerfile  its image: Python, pytest, git, curl
agent/llm.py        the model client, wrapped in spend guards: budget, ledger, record/replay
bench/project/      PetClinic Lite, the app the agent works on (a vet clinic in Auckland: 115 files, 153 tests)
bench/tasks/        15 tasks; each has a prompt (task.md) and hidden tests (check/), added only to score it
bench/run.py        run the agent on the tasks and score it
bench/board.py      print a run's scoreboard
results/            the scoreboards the videos show (ep01.jsonl = the episode-1 baseline; ep02-tools-only.jsonl,
                    ep02-steer.jsonl, ep02-search-lines.jsonl and ep02.jsonl = episode 2's steps, the last one
                    its final harness; the -r4-6 files add tries 4-6 to three of them; ep03.jsonl = episode 3;
                    ep04.jsonl = episode 4)
bench/escape.py     commands agents ran that reached past their folder: what the old rails did with them, and the
                    sandbox
```

## Run it

You need [uv](https://docs.astral.sh/uv/), Python 3.12 or newer and, from episode 4 on,
[Docker](https://docs.docker.com/get-started/get-docker/) (Docker Desktop on Windows and macOS) for the sandbox.
Without Docker the agent still runs, but asks before every command, and the benchmark refuses to start. Developed and
run on Windows 11 with Python 3.14 and Docker Desktop.

```bash
uv sync
docker build -t byoca-sandbox sandbox     # once: the sandbox's image
uv run pytest -q                          # the harness's own tests: offline, no key needed
uv run python -m bench.selfcheck          # every task is fair: tests pass at the start, the hidden check fails
uv run python -m bench.escape             # what the sandbox contains, next to episodes 1-3's rails
uv run python -m bench.board results/ep02.jsonl   # an episode's scoreboard, no key needed
uv run python -m bench.board results/ep02.jsonl results/ep02-r4-6.jsonl   # one board over 6 tries
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

On 2026-10-19, the whole benchmark (15 tasks, 3 tries) cost $0.29 with episode 4's harness, about $0.007 a try. Prices change
with every model release: check your provider's pricing page. The guards in `agent/llm.py`:
- a total budget (`budget_usd` in `.runs/config.json`, default $5) and a cap per run (`--run-budget`, default $0.50),
  both checked before every request;
- a ledger of every request's tokens and cost, `.runs/ledger.jsonl`;
- record/replay: every response is saved in `.runs/cassettes/`, and the same request again is read from disk, free;
- 25 turns per task, and a stop before a prompt grows past 80,000 tokens.

## Safety: read this before you run it

**The agent runs shell commands.** From episode 4 on, they run in a sandbox (`agent/sandbox.py`): a Docker container
per task that shares one folder with your computer, the project, and has no network. Everything else in it is
read-only except its own `/tmp`; it gets none of your environment variables; a command stops after 60 seconds, with
everything it started. The file and search tools run on your computer and refuse paths outside the project folder
and `.env` files. Long outputs are saved inside the project, in `.outputs/`, where both sides can read them. Without
Docker, `python -m agent` asks you before every command, and the benchmark doesn't run.

What the sandbox doesn't cover:
- **the project folder itself**: the agent can still break the project, or follow instructions planted in its files
  (task t14 has one). The benchmark gives it a fresh copy for every task; with your own code, commit first;
- **what the agent reads goes to the model's API**, sandbox or not;
- **the container is the boundary, and it holds as well as Docker does**: a container shares the kernel of the
  Linux VM Docker runs in; a virtual machine of its own is a stronger wall.

Episodes 1-3 had placeholder rails instead (a list of command patterns: `curl`, `find /`, `.env`...). In our first
baseline the agent listed the home folder and then searched the whole disk, unprompted; `bench/escape.py` shows what
those patterns missed.

## License

[MIT](LICENSE).
