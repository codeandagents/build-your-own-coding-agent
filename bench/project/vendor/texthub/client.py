"""The TextHub REST client. Only the parts Harbourside Vets uses are kept: send, status and balance.

API reference: https://docs.texthub.example/v2 (the gateway is not reachable from the clinic's test machines;
use dry_run=True there)."""
import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from .errors import RateLimited, TextHubError
from .segments import encoding_of, segments

log = logging.getLogger("texthub")

API = "https://api.texthub.example/v2"
MAX_SEGMENTS = 3
SENDER_MAX = 11


@dataclass
class Message:
    to: str               # E.164: +64215550101
    text: str
    reference: str = ""   # echoed back in delivery reports


@dataclass
class Result:
    ok: bool
    message_id: str = ""
    segments: int = 0
    error: str = ""
    dry_run: bool = False


@dataclass
class Client:
    token: str | None
    sender: str = ""
    dry_run: bool = False
    timeout: float = 10.0
    retries: int = 2
    sent: list[Message] = field(default_factory=list)  # dry runs keep what they would have sent

    def __post_init__(self):
        if len(self.sender) > SENDER_MAX:
            raise ValueError(f"sender: at most {SENDER_MAX} characters")
        if not self.dry_run and not self.token:
            raise ValueError("token: needed unless dry_run")

    def send(self, message: Message) -> Result:
        """Send one text. Never raises for a refused message: the Result says why."""
        if not message.to.startswith("+"):
            return Result(False, error="to: E.164 number expected (+64...)")
        count = segments(message.text)
        if count > MAX_SEGMENTS:
            return Result(False, segments=count, error=f"text: {count} segments, the account allows {MAX_SEGMENTS}")
        if self.dry_run:
            self.sent.append(message)
            log.info("dry run: %s, %d segment(s) %s", message.to, count, encoding_of(message.text))
            return Result(True, message_id=f"dry-{len(self.sent)}", segments=count, dry_run=True)
        body = {"to": message.to, "text": message.text, "from": self.sender, "reference": message.reference}
        try:
            reply = self._post("/messages", body)
        except TextHubError as e:
            return Result(False, segments=count, error=str(e))
        return Result(True, message_id=reply["id"], segments=reply.get("segments", count))

    def balance(self) -> int:
        """Prepaid segments left on the account."""
        if self.dry_run:
            return 0
        return int(self._get("/account")["segments_left"])

    def status(self, message_id: str) -> str:
        """queued, sent, delivered, failed or expired."""
        if self.dry_run:
            return "delivered"
        return self._get(f"/messages/{message_id}")["status"]

    # HTTP

    def _post(self, path: str, body: dict) -> dict:
        return self._request("POST", path, json.dumps(body).encode())

    def _get(self, path: str) -> dict:
        return self._request("GET", path, None)

    def _request(self, method: str, path: str, data: bytes | None) -> dict:
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        for attempt in range(self.retries + 1):
            request = urllib.request.Request(API + path, data=data, headers=headers, method=method)
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    return json.loads(response.read())
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < self.retries:
                    wait = float(e.headers.get("Retry-After", "1"))
                    log.warning("rate limited, waiting %.1f s", wait)
                    time.sleep(wait)
                    continue
                if e.code == 429:
                    raise RateLimited(float(e.headers.get("Retry-After", "1"))) from None
                detail = json.loads(e.read() or b"{}")
                raise TextHubError(detail.get("code", str(e.code)), detail.get("message", e.reason)) from None
            except urllib.error.URLError as e:
                if attempt < self.retries:
                    time.sleep(2 ** attempt)
                    continue
                raise TextHubError("network", str(e.reason)) from None
        raise TextHubError("network", "no response")
