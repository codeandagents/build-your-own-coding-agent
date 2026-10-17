import json
import random
import time
from datetime import date, datetime, timedelta

from petclinic.admin import merge_owners, merge_pets
from petclinic.archive import archive_visits, restore_visits
from petclinic.store import Store

PETS = 2_000
VISITS = 200_000


def expected(store, pet_id):
    return [v.id for v in sorted((v for v in store.visits.values() if v.pet_id == pet_id), key=lambda v: v.start)]


def on_day(store, day):
    return [v.id for v in sorted((v for v in store.visits.values() if v.start.date() == day), key=lambda v: v.start)]


def check_all(store):
    for pet_id in list(store.pets) + [999]:
        assert [v.id for v in store.visits_for_pet(pet_id)] == expected(store, pet_id), f"pet {pet_id}"
    for day in {v.start.date() for v in store.visits.values()} | {date(2030, 1, 1)}:
        assert [v.id for v in store.visits_on(day)] == on_day(store, day), f"day {day}"


def big_file(tmp_path):
    rng = random.Random(13)
    start = datetime(2015, 1, 5, 9, 0)
    slots = rng.sample(range(VISITS * 4), VISITS)  # every visit at its own time
    data = {
        "owners": [{"id": 1, "name": "Big Clinic", "telephone": "09 555 0100"}],
        "pets": [{"id": i, "name": f"Pet {i}", "species": "dog", "birth_date": "2015-01-01", "owner_id": 1}
                 for i in range(1, PETS + 1)],
        "visits": [{"id": i, "pet_id": rng.randint(1, PETS),
                    "start": (start + timedelta(minutes=30 * slot)).isoformat(timespec="minutes"),
                    "reason": "check-up"} for i, slot in enumerate(slots, start=1)],
    }
    path = tmp_path / "big.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_a_thousand_lookups_on_200k_visits(tmp_path):
    store = Store.load(big_file(tmp_path))
    rng = random.Random(1)
    began = time.perf_counter()
    for _ in range(1_000):
        store.visits_for_pet(rng.randint(1, PETS))
        assert time.perf_counter() - began < 2.0, "too slow"
    for pet_id in (1, 777, PETS):
        assert [v.id for v in store.visits_for_pet(pet_id)] == expected(store, pet_id)


def test_two_thousand_bookings_on_200k_visits(tmp_path):
    store = Store.load(big_file(tmp_path))
    day, booked = date(2062, 1, 2), []  # after the last visit in the big file (2060)
    began = time.perf_counter()
    while len(booked) < 2_000:
        if day.weekday() < 5:
            for slot in range(16):
                start = datetime.combine(day, datetime.min.time()) + timedelta(hours=9, minutes=30 * slot)
                booked.append(store.book_visit(1 + len(booked) % PETS, start, "history import").id)
        day += timedelta(days=1)
        assert time.perf_counter() - began < 2.0, "too slow"
    assert len(store.visits) == VISITS + len(booked)
    assert [v.id for v in store.visits_on(date(2062, 1, 2))] == booked[:16]
    assert store.visits_for_pet(1)[-1].start.year == 2062


def clinic():
    store = Store()
    owner = store.add_owner("Aroha Ngata", "021 555 0101")
    for name in ("Kiwi", "Pip", "Rocket"):
        store.add_pet(owner.id, name, "dog", date(2019, 4, 12))
    day = date(2026, 10, 19)
    for i in range(30):
        store.book_visit(1 + i % 3, datetime.combine(day + timedelta(days=i // 6), datetime.min.time())
                         + timedelta(hours=9, minutes=30 * (5 - i % 6)), f"visit {i}")
    return store


def test_right_after_booking_and_cancelling():
    store = clinic()
    check_all(store)
    store.cancel_visit(4)
    store.cancel_visit(5)
    check_all(store)
    store.book_visit(2, datetime(2026, 10, 19, 15, 0), "new")
    check_all(store)


def test_right_after_rescheduling():
    store = clinic()
    first = store.visits_for_pet(1)[0]
    old_start = first.start
    store.visits_on(old_start.date())
    store.reschedule_visit(first.id, datetime(2026, 11, 20, 16, 0))
    check_all(store)
    assert store.visits_for_pet(1)[-1].id == first.id
    assert [v.id for v in store.visits_on(date(2026, 11, 20))] == [first.id]
    store.book_visit(2, old_start, "the freed slot")  # the old slot is free again
    check_all(store)


def test_right_after_purging():
    store = clinic()
    store.visits_for_pet(1)
    assert store.purge_visits(date(2026, 10, 21)) == 12
    check_all(store)
    store.purge_visits()
    assert store.visits_for_pet(1) == []


def test_right_after_saving_and_loading(tmp_path):
    store = clinic()
    store.path = tmp_path / "clinic.json"
    store.cancel_visit(7)
    store.save()
    again = Store.load(store.path)
    check_all(again)
    again.book_visit(3, datetime(2026, 10, 19, 15, 30), "after loading")
    check_all(again)


def test_right_after_merging_pets():
    store = clinic()
    check_all(store)
    merge_pets(store, 1, 3)
    check_all(store)
    assert len(store.visits_for_pet(1)) == 20 and store.visits_for_pet(3) == []


def test_right_after_merging_owners():
    store = clinic()
    duplicate = store.add_owner("AROHA NGATA", "021 555 0101")
    twin = store.add_pet(duplicate.id, "Kiwi", "dog", date(2019, 4, 12))
    store.book_visit(twin.id, datetime(2026, 10, 30, 9, 0), "booked by the duplicate")
    check_all(store)
    merge_owners(store, 1, duplicate.id)
    check_all(store)
    assert store.visits_for_pet(1)[-1].reason == "booked by the duplicate"


def test_right_after_archiving_and_restoring(tmp_path):
    store = clinic()
    check_all(store)
    archive_visits(store, date(2026, 10, 22), tmp_path / "archive.json")
    check_all(store)
    restore_visits(store, tmp_path / "archive.json", pet_id=2)
    check_all(store)
    restore_visits(store, tmp_path / "archive.json")
    check_all(store)
    assert len(store.visits_for_pet(1)) == 10
