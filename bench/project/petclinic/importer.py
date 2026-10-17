"""Import the legacy system's CSV export (owner_name, owner_phone, pet_name, species, birth_date, notes).

ClinicMaster 4, the clinic's old system, still runs at the Devonport branch until it moves over. Every Monday at
06:00 its weekly export of new clients is imported (docs/runbooks/weekly-import.md). The import must be safe to
run twice: owners and pets already on file are never added again."""
import csv
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from . import audit, settings
from .errors import ValidationError
from .names import same_name
from .store import SPECIES

log = logging.getLogger("petclinic.importer")

COLUMNS = ("owner_name", "owner_phone", "pet_name", "species", "birth_date", "notes")


@dataclass
class ImportResult:
    owners_added: int = 0
    pets_added: int = 0
    skipped: int = 0


def parse_birth_date(text: str) -> date:
    return date.fromisoformat(text.strip())


def find_owner(store, name: str):
    return next((o for o in store.owners.values() if same_name(o.name, name)), None)


def check_columns(fieldnames) -> None:
    missing = [c for c in COLUMNS if c not in (fieldnames or [])]
    if missing:
        raise ValidationError(f"columns: the export has no {', '.join(missing)} column")


def import_csv(store, path: str | Path) -> ImportResult:
    result = ImportResult()
    with open(path, newline="", encoding="utf-8") as f:
        rows = csv.DictReader(f)
        check_columns(rows.fieldnames)
        for row_number, row in enumerate(rows, start=2):
            try:
                born = parse_birth_date(row["birth_date"])
            except ValueError:
                log.warning("row %d: birth_date %r is not a date (skipped)", row_number, row["birth_date"])
                result.skipped += 1
                continue
            species = row["species"].strip().lower()
            if species not in SPECIES:
                log.warning("row %d: species %r: the clinic doesn't treat it (skipped)", row_number, row["species"])
                result.skipped += 1
                continue
            owner = find_owner(store, row["owner_name"])
            if owner is None:
                try:
                    owner = store.add_owner(row["owner_name"], row["owner_phone"])
                except ValidationError as e:
                    if not settings.ALLOW_UNVERIFIED_PHONES:
                        log.warning("row %d: %s (skipped)", row_number, e)
                        result.skipped += 1
                        continue
                    owner = store.add_owner(row["owner_name"], "0")
                result.owners_added += 1
                audit.record(store, "import", f"owner {owner.id} added: {owner.name!r} ({owner.telephone})")
            if any(same_name(p.name, row["pet_name"]) for p in store.pets_of(owner.id)):
                log.info("row %d: %s already on file", row_number, row["pet_name"])
                continue
            pet = store.add_pet(owner.id, row["pet_name"], species, born)
            result.pets_added += 1
            audit.record(store, "import", f"pet {pet.id} added: {pet.name} ({species}) for owner {owner.id}")
            log.info("row %d: %s (%s) for %s", row_number, row["pet_name"], species, owner.name)
    log.info("import finished: %d owners and %d pets added, %d rows skipped",
             result.owners_added, result.pets_added, result.skipped)
    return result
