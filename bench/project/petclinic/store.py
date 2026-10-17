"""Owners, pets, visits, vaccinations and payments, kept in one JSON file (clinic.json, decision 0001)."""
import json
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path

from .errors import NotFound, ValidationError
from .models import Owner, Payment, Pet, Vaccination, Visit
from .scheduling import slots_for_day

SPECIES = ("dog", "cat", "rabbit", "guinea pig", "bird")
METHODS = ("eftpos", "credit", "cash")


class Store:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else None
        self.owners: dict[int, Owner] = {}
        self.pets: dict[int, Pet] = {}
        self.visits: dict[int, Visit] = {}
        self.vaccinations: list[Vaccination] = []
        self.payments: dict[int, Payment] = {}

    @staticmethod
    def _next_id(table: dict) -> int:
        return max(table, default=0) + 1

    # owners and pets

    def add_owner(self, name: str, telephone: str, email: str = "") -> Owner:
        if not name.strip():
            raise ValidationError("name: must not be empty")
        if not telephone.replace(" ", "").replace("-", "").isdigit():
            raise ValidationError("telephone: digits, spaces and dashes only")
        if email and "@" not in email:
            raise ValidationError("email: must contain @")
        owner = Owner(self._next_id(self.owners), name.strip(), telephone, email.strip())
        self.owners[owner.id] = owner
        return owner

    def update_owner(self, owner_id: int, *, name: str | None = None, telephone: str | None = None,
                     email: str | None = None) -> Owner:
        """Change an owner's details; arguments left as None keep their value."""
        owner = self.owner(owner_id)
        if name is not None:
            if not name.strip():
                raise ValidationError("name: must not be empty")
            owner.name = name.strip()
        if telephone is not None:
            if not telephone.replace(" ", "").replace("-", "").isdigit():
                raise ValidationError("telephone: digits, spaces and dashes only")
            owner.telephone = telephone
        if email is not None:
            if email and "@" not in email:
                raise ValidationError("email: must contain @")
            owner.email = email.strip()
        return owner

    def add_pet(self, owner_id: int, name: str, species: str, birth_date: date, breed: str = "",
                microchip: str = "") -> Pet:
        if owner_id not in self.owners:
            raise ValidationError(f"owner_id: no owner {owner_id}")
        if not name.strip():
            raise ValidationError("name: must not be empty")
        if microchip and not (microchip.isdigit() and len(microchip) == 15):
            raise ValidationError("microchip: 15 digits")
        pet = Pet(self._next_id(self.pets), name.strip(), species.strip().lower(), birth_date, owner_id,
                  breed.strip(), microchip)
        self.pets[pet.id] = pet
        return pet

    def owner(self, owner_id: int) -> Owner:
        if owner_id not in self.owners:
            raise NotFound(f"owner_id: no owner {owner_id}")
        return self.owners[owner_id]

    def pet(self, pet_id: int) -> Pet:
        if pet_id not in self.pets:
            raise NotFound(f"pet_id: no pet {pet_id}")
        return self.pets[pet_id]

    def visit(self, visit_id: int) -> Visit:
        if visit_id not in self.visits:
            raise NotFound(f"visit_id: no visit {visit_id}")
        return self.visits[visit_id]

    def find_owners(self, text: str) -> list[Owner]:
        text = text.lower()
        return [o for o in self.owners.values() if text in o.name.lower()]

    def pets_of(self, owner_id: int) -> list[Pet]:
        return [p for p in self.pets.values() if p.owner_id == owner_id]

    def owner_of(self, pet_id: int) -> Owner:
        return self.owners[self.pet(pet_id).owner_id]

    # visits

    def book_visit(self, pet_id: int, start: datetime, reason: str, vet_id: int | None = None) -> Visit:
        if pet_id not in self.pets:
            raise ValidationError(f"pet_id: no pet {pet_id}")
        if not reason.strip():
            raise ValidationError("reason: must not be empty")
        self._check_free(start)
        visit = Visit(self._next_id(self.visits), pet_id, start, reason.strip(), vet_id)
        self.visits[visit.id] = visit
        return visit

    def cancel_visit(self, visit_id: int) -> Visit:
        if visit_id not in self.visits:
            raise ValidationError(f"visit_id: no visit {visit_id}")
        return self.visits.pop(visit_id)

    def reschedule_visit(self, visit_id: int, start: datetime) -> Visit:
        if visit_id not in self.visits:
            raise ValidationError(f"visit_id: no visit {visit_id}")
        self._check_free(start)
        self.visits[visit_id].start = start
        return self.visits[visit_id]

    def purge_visits(self, before: date | None = None) -> int:
        """Delete visits before a date (all visits if `before` is None). Returns how many went."""
        gone = [v.id for v in self.visits.values() if before is None or v.start.date() < before]
        for visit_id in gone:
            del self.visits[visit_id]
        return len(gone)

    def _check_free(self, start: datetime) -> None:
        taken = [v.start for v in self.visits.values() if v.start.date() == start.date()]
        if start.time() not in slots_for_day(start.date(), taken):
            raise ValidationError(f"start: {start:%Y-%m-%d %H:%M} is not a free slot")

    def visits_for_pet(self, pet_id: int) -> list[Visit]:
        return sorted((v for v in self.visits.values() if v.pet_id == pet_id), key=lambda v: v.start)

    def visits_on(self, day: date) -> list[Visit]:
        return sorted((v for v in self.visits.values() if v.start.date() == day), key=lambda v: v.start)

    def visits_for_owner(self, owner_id: int) -> list[Visit]:
        pets = {p.id for p in self.pets_of(owner_id)}
        return sorted((v for v in self.visits.values() if v.pet_id in pets), key=lambda v: v.start)

    # vaccinations

    def add_vaccination(self, pet_id: int, vaccine: str, given: date) -> Vaccination:
        if pet_id not in self.pets:
            raise ValidationError(f"pet_id: no pet {pet_id}")
        record = Vaccination(pet_id, vaccine, given)
        self.vaccinations.append(record)
        return record

    def vaccinations_for(self, pet_id: int) -> list[Vaccination]:
        return sorted((r for r in self.vaccinations if r.pet_id == pet_id), key=lambda r: (r.given, r.vaccine))

    # payments

    def add_payment(self, visit_id: int, cents: int, method: str, paid: datetime) -> Payment:
        if visit_id not in self.visits:
            raise ValidationError(f"visit_id: no visit {visit_id}")
        if not isinstance(cents, int) or cents <= 0:
            raise ValidationError("cents: a positive whole number of cents")
        if method not in METHODS:
            raise ValidationError(f"method: one of {', '.join(METHODS)}")
        payment = Payment(self._next_id(self.payments), visit_id, cents, method, paid)
        self.payments[payment.id] = payment
        return payment

    def payments_for_visit(self, visit_id: int) -> list[Payment]:
        return [p for p in self.payments.values() if p.visit_id == visit_id]

    # the data file

    def to_json(self) -> str:
        """One record per line, so a diff of clinic.json shows exactly what changed."""
        tables = {
            "owners": [_compact(asdict(o)) for o in self.owners.values()],
            "pets": [_compact({**asdict(p), "birth_date": p.birth_date.isoformat()}) for p in self.pets.values()],
            "visits": [_compact({**asdict(v), "start": v.start.isoformat(timespec="minutes")})
                       for v in self.visits.values()],
            "vaccinations": [{**asdict(r), "given": r.given.isoformat()} for r in self.vaccinations],
            "payments": [{**asdict(p), "paid": p.paid.isoformat(timespec="minutes")} for p in self.payments.values()],
        }
        parts = []
        for name, rows in tables.items():
            body = ",\n".join("    " + json.dumps(row, ensure_ascii=False) for row in rows)
            parts.append(f'  "{name}": [\n{body}\n  ]' if rows else f'  "{name}": []')
        return "{\n" + ",\n".join(parts) + "\n}\n"

    def save(self) -> None:
        self.path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "Store":
        store = cls(path)
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        for o in data["owners"]:
            store.owners[o["id"]] = Owner(**o)
        for p in data["pets"]:
            store.pets[p["id"]] = Pet(**{**p, "birth_date": date.fromisoformat(p["birth_date"])})
        for v in data["visits"]:
            store.visits[v["id"]] = Visit(**{**v, "start": datetime.fromisoformat(v["start"])})
        for r in data.get("vaccinations", []):
            store.vaccinations.append(Vaccination(**{**r, "given": date.fromisoformat(r["given"])}))
        for p in data.get("payments", []):
            store.payments[p["id"]] = Payment(**{**p, "paid": datetime.fromisoformat(p["paid"])})
        return store


def _compact(row: dict) -> dict:
    """Leave out optional fields that are empty, to keep clinic.json short."""
    return {k: v for k, v in row.items() if v not in ("", None)}
