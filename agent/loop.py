"""The agent loop: send the conversation, run the tools the model asks for, repeat until it stops."""
from dataclasses import dataclass
from pathlib import Path

from .llm import Claude, prompt_tokens
from .tools import TOOLS, run_tool

SYSTEM = """You are a coding agent working in a software project on the user's machine.
Use the bash tool to look around, read and edit files, and run the tests. Work in small steps and check your work.
When the task is done, reply with a short summary of what you changed."""

MAX_TURNS = 25           # a task that isn't done by then is stopped (a looping agent is the main cost risk)
PROMPT_CEILING = 80_000  # tokens: stop before a request gets near Haiku 5.5's 5x price above 100k


@dataclass
class Result:
    stop: str    # done, max_turns, context_limit, refusal, ...
    turns: int


def request(messages: list) -> dict:
    """One turn's request. cache_control: the API caches the prompt so far; the next turn reads it at 1/10 price."""
    return dict(system=SYSTEM, tools=TOOLS, messages=messages, max_tokens=8000,
                cache_control={"type": "ephemeral"}, output_config={"effort": "low"})


def run(task: str, claude: Claude, cwd: Path, *, label: str = "", log=print) -> Result:
    messages = [{"role": "user", "content": task}]
    for turn in range(1, MAX_TURNS + 1):
        response = claude.create(task=label, **request(messages))
        messages.append({"role": "assistant", "content": response.content})
        for block in response.content:
            if block.type == "text" and block.text.strip():
                log(f"agent: {block.text.strip()}")
        calls = [block for block in response.content if block.type == "tool_use"]
        if response.stop_reason != "tool_use" or not calls:
            return Result("done" if response.stop_reason == "end_turn" else response.stop_reason, turn)

        results = []
        for call in calls:
            log(f"$ {call.input.get('command', '')}")
            output, is_error = run_tool(call.name, call.input, cwd)
            log(output if len(output) < 1500 else output[:1500] + "\n...")
            results.append({"type": "tool_result", "tool_use_id": call.id, "content": output, "is_error": is_error})
        messages.append({"role": "user", "content": results})

        next_prompt = prompt_tokens(response.usage) + response.usage.output_tokens + len(str(results)) // 3
        if next_prompt > PROMPT_CEILING:
            return Result("context_limit", turn)
    return Result("max_turns", MAX_TURNS)
