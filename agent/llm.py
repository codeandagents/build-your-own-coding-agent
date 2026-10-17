"""The Claude client, wrapped in spend guards. Every request that can cost money goes through `Claude.create()`.

- Budget: refuses before sending once the ledger's total reaches budget_usd (or a run reaches its own cap).
- Ledger: one JSON line per request in .runs/ledger.jsonl, with its usage and its price in dollars.
- Record/replay: each response is saved to .runs/cassettes/ under a hash of the request. The same request again
  is read from disk: free, and identical (re-running a recorded demo shows exactly what happened the first time).
"""
import hashlib
import json
import os
import time
from pathlib import Path

import anthropic
from anthropic.types import Message

# $ per million tokens for prompts up to 100k tokens (platform.claude.com/docs/en/about-claude/pricing, 2026-10-16).
PRICES = {"claude-haiku-5-5": {"input": 0.10, "output": 0.50, "cache_write": 0.125, "cache_read": 0.01}}
LONG_PROMPT = 100_000  # Haiku 5.5: a request whose prompt is longer pays 5x on every line
LONG_FACTOR = 5.0
RUNS = Path(os.environ.get("BYOCA_RUNS", Path(__file__).parent.parent / ".runs"))


class SpendRefused(RuntimeError):
    """Stopped before spending anything."""


def settings(runs: Path = RUNS) -> dict:
    """This machine's settings in .runs/config.json (budget_usd, warn_usd, work_root); environment variables win."""
    path = runs / "config.json"
    config = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    for key in ("budget_usd", "warn_usd", "work_root"):
        if f"BYOCA_{key.upper()}" in os.environ:
            config[key] = os.environ[f"BYOCA_{key.upper()}"]
    return config


def prompt_tokens(usage) -> int:
    return usage.input_tokens + (usage.cache_creation_input_tokens or 0) + (usage.cache_read_input_tokens or 0)


def price(model: str, usage) -> float:
    p = PRICES[model]
    dollars = (usage.input_tokens * p["input"] + (usage.cache_creation_input_tokens or 0) * p["cache_write"]
               + (usage.cache_read_input_tokens or 0) * p["cache_read"] + usage.output_tokens * p["output"]) / 1e6
    return dollars * (LONG_FACTOR if prompt_tokens(usage) > LONG_PROMPT else 1.0)


def _plain(obj):
    """JSON form of SDK objects inside a request, for hashing."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json", exclude_none=True)
    raise TypeError(f"can't hash {type(obj).__name__}")


class Ledger:
    def __init__(self, path: Path):
        self.path = path

    def entries(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def total(self, run: str | None = None) -> float:
        return sum(e["usd"] for e in self.entries() if run is None or e["run"] == run)

    def add(self, entry: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")


class Claude:
    def __init__(self, model: str = "claude-haiku-5-5", *, run: str = "adhoc", salt: str = "",
                 budget_usd: float | None = None, run_budget_usd: float | None = None,
                 replay_only: bool = False, client=None, runs: Path = RUNS):
        if model not in PRICES:
            raise ValueError(f"no price for {model}: add it to PRICES first")
        self.model, self.run, self.salt, self.replay_only = model, run, salt, replay_only
        config = settings(runs)
        self.budget = float(config.get("budget_usd", 5)) if budget_usd is None else budget_usd
        self.run_budget = run_budget_usd
        self.warn_at = float(config.get("warn_usd", 0))
        self.ledger = Ledger(runs / "ledger.jsonl")
        self.cassettes = runs / "cassettes"
        self._client = client

    def client(self):
        if self._client is None:
            key = os.environ.get("BYOCA_API_KEY")  # our own name first; else the SDK's lookup (ANTHROPIC_API_KEY, ...)
            self._client = anthropic.Anthropic(api_key=key) if key else anthropic.Anthropic()
        return self._client

    def key(self, params: dict) -> str:
        body = json.dumps({**params, "_salt": self.salt}, sort_keys=True, default=_plain)
        return hashlib.sha256(body.encode("utf-8")).hexdigest()[:32]

    def recorded(self, **params) -> bool:
        return (self.cassettes / f"{self.key({'model': self.model, **params})}.json").exists()

    def create(self, task: str = "", **params) -> Message:
        params = {"model": self.model, **params}
        path = self.cassettes / f"{self.key(params)}.json"
        if path.exists():
            message = Message.model_validate_json(path.read_text(encoding="utf-8"))
            self._log(task, message, usd=0.0, replayed=True)
            return message
        if self.replay_only:
            raise SpendRefused("this request was never recorded, and replay-only is on")
        spent = self.ledger.total()
        if spent >= self.budget:
            raise SpendRefused(f"budget used up: ${spent:.4f} of ${self.budget:.2f} (budget_usd)")
        if self.run_budget is not None and self.ledger.total(self.run) >= self.run_budget:
            raise SpendRefused(f"this run's cap is reached: ${self.run_budget:.2f}")
        try:
            message = self.client().messages.create(**params)
        except anthropic.BadRequestError as e:
            if "credit balance" in str(e).lower():
                raise SpendRefused("the account's credit balance is too low: top up in the Claude Console") from e
            raise
        self.cassettes.mkdir(parents=True, exist_ok=True)
        path.write_text(message.model_dump_json(), encoding="utf-8")  # saved before use: never bought twice
        usd = price(self.model, message.usage)
        self._log(task, message, usd=usd, replayed=False)
        if self.warn_at and spent < self.warn_at <= spent + usd:
            print(f"\n*** API spend has reached ${spent + usd:.2f} (warn_usd ${self.warn_at:.2f}): time to top up ***\n")
        return message

    def _log(self, task: str, message: Message, *, usd: float, replayed: bool) -> None:
        u = message.usage
        self.ledger.add({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "run": self.run, "task": task, "model": self.model,
                         "input": u.input_tokens, "cache_write": u.cache_creation_input_tokens or 0,
                         "cache_read": u.cache_read_input_tokens or 0, "output": u.output_tokens,
                         "usd": round(usd, 6), "replayed": replayed, "id": message.id})

    def count_tokens(self, **params) -> int:
        """Free (Anthropic doesn't bill token counting)."""
        return self.client().messages.count_tokens(model=self.model, **params).input_tokens
