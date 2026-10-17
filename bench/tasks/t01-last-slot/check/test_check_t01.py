from datetime import date, datetime, time

from petclinic.scheduling import slots_for_day
from petclinic.store import Store


def test_last_slot_is_16_30():
    slots = slots_for_day(date(2026, 10, 21))
    assert slots[-1] == time(16, 30)
    assert len(slots) == 16


def test_16_30_can_be_booked():
    store = Store()
    owner = store.add_owner("Ben Carter", "027 555 0199")
    pet = store.add_pet(owner.id, "Rocket", "rabbit", date(2024, 2, 29))
    assert store.book_visit(pet.id, datetime(2026, 10, 21, 16, 30), "teeth").id == 1
