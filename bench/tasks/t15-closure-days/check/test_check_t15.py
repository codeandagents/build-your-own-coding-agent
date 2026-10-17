from datetime import date, datetime

import pytest

from petclinic.errors import ValidationError
from petclinic.scheduling import CLINIC_TZ, next_free_slot, slots_for_day
from petclinic.store import Store

# The admin system's list (bench/tasks/t15-closure-days/admin/closures.json): public holidays and training days.
CLOSED = ["2026-10-26", "2026-11-18", "2026-12-25", "2026-12-28", "2027-01-01", "2027-01-04", "2027-02-01",
          "2027-02-08", "2027-03-19", "2027-03-26", "2027-03-29", "2027-04-26", "2027-06-07", "2027-06-16",
          "2027-06-25", "2027-09-17", "2027-10-25", "2027-12-27", "2027-12-28"]


@pytest.mark.parametrize("day", CLOSED)
def test_no_slots_on_a_closure_day(day):
    assert slots_for_day(date.fromisoformat(day)) == []


def test_open_days_are_unchanged():
    for day in (date(2026, 10, 27), date(2026, 11, 17), date(2027, 3, 25), date(2027, 6, 24)):
        assert len(slots_for_day(day)) == 16


def test_next_free_slot_skips_the_long_weekend():
    friday_evening = datetime(2026, 10, 23, 16, 45, tzinfo=CLINIC_TZ)
    assert next_free_slot([], friday_evening) == datetime(2026, 10, 27, 9, 0)


def test_a_closure_day_cannot_be_booked():
    store = Store()
    owner = store.add_owner("Mei Lin", "022-555-0142")
    pet = store.add_pet(owner.id, "Mochi", "cat", date(2021, 7, 8))
    with pytest.raises(ValidationError, match="^start:"):
        store.book_visit(pet.id, datetime(2026, 11, 18, 10, 0), "check-up")
