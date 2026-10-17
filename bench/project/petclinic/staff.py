"""Vets, their leave, and who is on duty. The staff file (data/staff.json) comes from the practice manager's
spreadsheet: leave is written as a first and a last day away, both included."""
import json
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from .names import initials
from .periods import Period

log = logging.getLogger("petclinic.staff")


@dataclass
class Vet:
    id: int
    name: str
    active: bool = True  # former vets and locums stay in the file, with their leave, for the records

    @property
    def initials(self) -> str:
        return initials(self.name)


@dataclass
class Leave:
    vet_id: int
    period: Period  # the days away
    note: str = ""


def load_staff(path: str | Path) -> tuple[list[Vet], list[Leave]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    vets = [Vet(**v) for v in data["vets"]]
    leave = []
    for x in data["leave"]:
        first, last = date.fromisoformat(x["first_day"]), date.fromisoformat(x["last_day"])
        vet_id = int(x["vet_id"])  # the spreadsheet's export writes some ids as text
        leave.append(Leave(vet_id, Period.inclusive(first, last), x.get("note", "")))
    log.info("%d vets, %d leave periods", len(vets), len(leave))
    return vets, leave


def away(vet: Vet, day: date, leave: list[Leave]) -> bool:
    """True if `day` falls in one of the vet's leave periods."""
    return any(x.vet_id == vet.id and day in x.period for x in leave)


def on_duty(day: date, vets: list[Vet], leave: list[Leave]) -> list[Vet]:
    """Vets working on `day`: weekdays only, current vets only, nobody on leave."""
    if day.weekday() >= 5:
        return []
    return [v for v in vets if v.active and not away(v, day, leave)]


def back_at_work(vet: Vet, after: date, leave: list[Leave]) -> date:
    """The first weekday after `after` when the vet isn't on leave."""
    day = after + timedelta(days=1)
    while day.weekday() >= 5 or away(vet, day, leave):
        day += timedelta(days=1)
    return day


def leave_in(period: Period, leave: list[Leave]) -> list[Leave]:
    """Leave that overlaps a period, earliest first."""
    return sorted((x for x in leave if x.period.overlaps(period)), key=lambda x: x.period.start)


def vet_by_id(vets: list[Vet], vet_id: int) -> Vet:
    from .errors import NotFound
    for vet in vets:
        if vet.id == vet_id:
            return vet
    raise NotFound(f"vet_id: no vet {vet_id}")
