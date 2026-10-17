"""The archive: old visits leave clinic.json for data/archive.json after settings.ARCHIVE_AFTER_YEARS, which keeps
the data file small. They can be brought back when a pet's full history is needed (an insurance claim, a court case).

The archive is a plain JSON list of visits; ids stay the same, so a restored visit is the same visit."""
import json
import logging
from datetime import date, datetime
from pathlib import Path

from . import audit
from .models import Visit

log = logging.getLogger("petclinic.archive")


def _read(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def _write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")


def archive_visits(store, before: date, path: str | Path) -> int:
    """Move visits before `before` into the archive file. Returns how many moved."""
    path = Path(path)
    rows = _read(path)
    moving = [v for v in store.visits.values() if v.start.date() < before]
    for visit in moving:
        rows.append({"id": visit.id, "pet_id": visit.pet_id, "start": visit.start.isoformat(timespec="minutes"),
                     "reason": visit.reason, "vet_id": visit.vet_id})
        del store.visits[visit.id]
    _write(path, rows)
    audit.record(store, "archive", f"{len(moving)} visits before {before} archived")
    log.info("%d visits archived", len(moving))
    return len(moving)


def restore_visits(store, path: str | Path, pet_id: int | None = None) -> int:
    """Bring archived visits back into the store: all of them, or one pet's. Returns how many came back."""
    path = Path(path)
    rows, kept = _read(path), []
    restored = 0
    for row in rows:
        if pet_id is not None and row["pet_id"] != pet_id:
            kept.append(row)
            continue
        visit = Visit(row["id"], row["pet_id"], datetime.fromisoformat(row["start"]), row["reason"], row.get("vet_id"))
        store.visits[visit.id] = visit
        restored += 1
    _write(path, kept)
    audit.record(store, "archive", f"{restored} visits restored" + (f" for pet {pet_id}" if pet_id else ""))
    return restored


def archived_count(path: str | Path) -> int:
    return len(_read(Path(path)))
