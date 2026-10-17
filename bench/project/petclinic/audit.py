"""The audit trail: who added, changed or removed a record, and when (logs/audit.log next to the data file).

One line per change: "2026-10-12 06:00:03  import       owner 41 added: 'Mei Lin' (022-555-0142)".
A store without a file (tests) keeps no trail."""
from datetime import datetime
from pathlib import Path

from .scheduling import clinic_now

WHO_WIDTH = 11


def trail_path(store) -> Path | None:
    if store.path is None:
        return None
    return Path(store.path).parent / "logs" / "audit.log"


def record(store, who: str, what: str, when: datetime | None = None) -> None:
    path = trail_path(store)
    if path is None:
        return
    path.parent.mkdir(exist_ok=True)
    stamp = (when or clinic_now()).strftime("%Y-%m-%d %H:%M:%S")
    with path.open("a", encoding="utf-8", newline="") as f:
        f.write(f"{stamp}  {who:{WHO_WIDTH}}  {what}\n")


def entries(store, since: datetime | None = None, who: str | None = None) -> list[str]:
    """Trail lines, oldest first; optionally only from `since` on, or only by `who`."""
    path = trail_path(store)
    if path is None or not path.exists():
        return []
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        stamp = datetime.strptime(line[:19], "%Y-%m-%d %H:%M:%S")
        if since and stamp < since:
            continue
        if who and line[21:21 + WHO_WIDTH].strip() != who:
            continue
        lines.append(line)
    return lines
