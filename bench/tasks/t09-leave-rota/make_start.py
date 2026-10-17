"""Writes t09's start/ folder: the booking page's log for 1-16 October and the two bookings it took with vets on leave.

The web host's script logs every page view (the day, the vet asked for, how many times were offered) and every
booking. With the two bugs (staff.load_staff drops the last day of each leave, and leaves Walker's December leave,
written with a text id, matching no vet), the page offered Dr Patel on Fri 6 Nov all along, and Dr Walker over
Christmas once clients started looking at December (from 12 October). Two clients booked them: visit 976 (Patel,
6 Nov, booked 5 Oct) and visit 977 (Walker, 22 Dec, booked 15 Oct). Deterministic.
Run from the repo root: .venv/Scripts/python bench/tasks/t09-leave-rota/make_start.py"""
import random
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

HERE = Path(__file__).parent
PROJECT = HERE.parent.parent / "project"
sys.path.insert(0, str(PROJECT))

from petclinic.models import Visit  # noqa: E402
from petclinic.scheduling import slot_times  # noqa: E402
from petclinic.store import Store  # noqa: E402

CLOSED = {date(2026, 10, 26), date(2026, 11, 18), date(2026, 12, 25), date(2026, 12, 28), date(2027, 1, 1),
          date(2027, 1, 4)}  # the clinic doesn't open (t15); nobody views them here
BAD = [(976, 4, datetime(2026, 11, 6, 11, 0), "vaccination", 1, datetime(2026, 10, 5, 20, 41, 7)),
       (977, 15, datetime(2026, 12, 22, 9, 30), "annual check-up", 2, datetime(2026, 10, 15, 21, 12, 55))]


def away(vet: int, day: date) -> bool:
    """Leave as the buggy loader sees it: Patel 2-5 Nov (6 Nov dropped), Walker never (his id is text), Tane 11-21 Jan."""
    return (vet == 1 and date(2026, 11, 2) <= day < date(2026, 11, 6)) or \
        (vet == 3 and date(2027, 1, 11) <= day < date(2027, 1, 22))


def main() -> None:
    rng = random.Random(20261016)
    store = Store.load(PROJECT / "clinic.json")
    for visit_id, pet_id, start, reason, vet, _ in BAD:
        assert visit_id not in store.visits and start not in {v.start for v in store.visits.values()}
        store.visits[visit_id] = Visit(visit_id, pet_id, start, reason, vet)
    lines = []
    booked_online = [v for v in store.visits.values() if v.id < 976 and v.vet_id and v.id % 2 == 0
                     and date(2026, 10, 2) <= v.start.date() <= date(2026, 11, 13)]
    bookings = {}
    for visit in booked_online:  # booked on the page between 1 October and the day before the visit
        latest = min(datetime(2026, 10, 16, 22), datetime.combine(visit.start.date(), time(7)) - timedelta(days=1))
        span = int((latest - datetime(2026, 10, 1, 7)).total_seconds() // 60)
        bookings[datetime(2026, 10, 1, 7) + timedelta(minutes=rng.randrange(0, max(span, 1)))] = visit
    for *_, when in BAD:
        bookings[when] = store.visits[_[0]]
    day = date(2026, 10, 1)
    while day <= date(2026, 10, 16):
        for _ in range(rng.randrange(140, 220)):
            stamp = datetime.combine(day, time(rng.randrange(6, 23), rng.randrange(60), rng.randrange(60)))
            ahead = rng.choice([1, 2, 3, 5, 7, 9, 12, 14, 18, 21, 25, 28, 35, 45, 60, 70, 80])
            if day < date(2026, 10, 12) and ahead > 40:
                ahead = rng.randrange(20, 40)
            wanted = day + timedelta(days=ahead)
            if wanted.weekday() >= 5 or wanted in CLOSED:
                continue
            vet = rng.choice(["any", "any", "any", 1, 2, 3])
            taken = sum(1 for v in store.visits.values() if v.start.date() == wanted)
            free = len(slot_times()) - taken
            offered = 0 if vet != "any" and away(vet, wanted) else free
            lines.append((stamp, f"view    day={wanted} vet={vet:<3} offered={offered}"))
            if rng.random() < 0.04:
                lines.append((stamp + timedelta(seconds=40), "refuse  telephone: no client with that name and number"))
        day += timedelta(days=1)
    for when, visit in bookings.items():
        pet = store.pets[visit.pet_id]
        owner = store.owners[pet.owner_id]
        lines.append((when, f"book    visit={visit.id} day={visit.start.date()} time={visit.start:%H:%M} "
                            f"vet={visit.vet_id} pet={pet.name} owner={owner.name}"))
    text = "".join(f"{stamp:%Y-%m-%d %H:%M:%S} {message}\n" for stamp, message in sorted(lines))
    out = HERE / "start"
    (out / "logs").mkdir(parents=True, exist_ok=True)
    (out / "logs" / "booking-2026-10.log").write_text(text, encoding="utf-8", newline="")
    (out / "clinic.json").write_text(store.to_json(), encoding="utf-8", newline="")
    staff = (PROJECT / "data" / "staff.json").read_text(encoding="utf-8")
    assert '"vet_id": "2"' in staff
    print(f"booking-2026-10.log: {len(lines)} lines, {len(text):,} characters, {len(bookings)} bookings")


if __name__ == "__main__":
    main()
