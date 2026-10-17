"""Reports for the front desk."""
from collections import Counter
from datetime import date

from .periods import Period


def visit_rows(store, since: date, until: date | None = None) -> list[dict]:
    """One row per visit from `since` up to, but not including, `until` (no end if None), oldest first:
    date, time, pet, owner, reason."""
    period = Period(since, until or date.max)
    rows = []
    for v in sorted(store.visits.values(), key=lambda v: v.start):
        if v.start.date() not in period:
            continue
        pet = store.pets[v.pet_id]
        owner = store.owners[pet.owner_id]
        rows.append({"date": v.start.date().isoformat(), "time": v.start.strftime("%H:%M"),
                     "pet": pet.name, "owner": owner.name, "reason": v.reason})
    return rows


def format_table(rows: list[dict]) -> str:
    if not rows:
        return "No visits."
    lines = [f"{'date':10}  {'time':5}  {'pet':10}  {'owner':16}  reason"]
    for r in rows:
        lines.append(f"{r['date']:10}  {r['time']:5}  {r['pet'][:10]:10}  {r['owner'][:16]:16}  {r['reason']}")
    return "\n".join(lines)


def busiest_days(store, period: Period, top: int = 5) -> list[tuple[date, int]]:
    """The days with the most visits in a period, busiest first (ties: earliest first)."""
    counts = Counter(v.start.date() for v in store.visits.values() if v.start.date() in period)
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:top]


def species_mix(store) -> dict[str, int]:
    """How many pets of each species are on file."""
    return dict(sorted(Counter(p.species for p in store.pets.values()).items()))


def vet_workload(store, period: Period, vets) -> list[tuple[str, int]]:
    """Visits per vet in a period; visits booked with no vet are counted as "any vet"."""
    names = {v.id: v.name for v in vets}
    counts = Counter(names.get(v.vet_id, "any vet") for v in store.visits.values() if v.start.date() in period)
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))
