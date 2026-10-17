"""Sending texts through TextHub (vendor/texthub, decision 0005).

Texts are never sent during quiet hours: they wait in the outbox (data/outbox.json) until the next send run.
Without a TEXTHUB_TOKEN in the environment the client runs dry: it logs what it would send and sends nothing."""
import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from vendor.texthub import Client, Message

from .notifications import can_send
from .phones import international, is_mobile
from .settings import SMS_SENDER

log = logging.getLogger("petclinic.sms")


@dataclass
class Queued:
    to: str      # the owner's number as the clinic has it
    text: str
    owner_id: int


class Outbox:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> list[Queued]:
        if not self.path.exists():
            return []
        return [Queued(**q) for q in json.loads(self.path.read_text(encoding="utf-8"))]

    def save(self, queued: list[Queued]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps([asdict(q) for q in queued], indent=2) + "\n", encoding="utf-8")

    def add(self, items: list[Queued]) -> None:
        self.save(self.load() + items)


def client() -> Client:
    token = os.environ.get("TEXTHUB_TOKEN")
    return Client(token, sender=SMS_SENDER, dry_run=token is None)


def send_all(outbox: Outbox, now: datetime, hub: Client | None = None) -> tuple[int, int]:
    """Send what's in the outbox, unless it's quiet hours. Returns (sent, still waiting)."""
    queued = outbox.load()
    if not queued:
        return 0, 0
    if not can_send(now):
        log.info("quiet hours: %d text(s) wait", len(queued))
        return 0, len(queued)
    hub = hub or client()
    failed = []
    for item in queued:
        if not is_mobile(item.to):
            log.warning("owner %d: %s is not a mobile number (dropped)", item.owner_id, item.to)
            continue
        result = hub.send(Message(international(item.to), item.text))
        if not result.ok:
            log.warning("owner %d: TextHub said %s (kept for the next run)", item.owner_id, result.error)
            failed.append(item)
    outbox.save(failed)
    return len(queued) - len(failed), len(failed)


def queue_for_owner(outbox: Outbox, owner, text: str) -> None:
    outbox.add([Queued(owner.telephone, text, owner.id)])
