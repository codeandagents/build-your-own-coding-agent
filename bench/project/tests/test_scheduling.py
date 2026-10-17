from datetime import date, datetime, time

import pytest

from petclinic.errors import ValidationError
from petclinic.scheduling import CLINIC_TZ, is_open, next_free_slot, parse_start, slot_times, slots_for_day

WEDNESDAY = date(2026, 10, 21)


def test_first_slot_is_at_nine():
    assert slots_for_day(WEDNESDAY)[0] == time(9, 0)


def test_a_day_has_sixteen_appointment_times():
    assert len(slot_times()) == 16
    assert slot_times()[1] == time(9, 30)


def test_closed_at_weekends():
    assert slots_for_day(date(2026, 10, 24)) == []
    assert slots_for_day(date(2026, 10, 25)) == []
    assert not is_open(date(2026, 10, 24))
    assert is_open(WEDNESDAY)


def test_taken_slots_are_not_free():
    free = slots_for_day(WEDNESDAY, [datetime(2026, 10, 21, 9, 30)])
    assert time(9, 0) in free
    assert time(9, 30) not in free


def test_next_free_slot_skips_the_past():
    now = datetime(2026, 10, 21, 12, 10, tzinfo=CLINIC_TZ)
    assert next_free_slot([], now) == datetime(2026, 10, 21, 12, 30)


def test_next_free_slot_skips_booked_times():
    now = datetime(2026, 10, 21, 12, 10, tzinfo=CLINIC_TZ)
    assert next_free_slot([datetime(2026, 10, 21, 12, 30)], now) == datetime(2026, 10, 21, 13, 0)


def test_parse_start():
    assert parse_start("2026-10-21 14:30") == datetime(2026, 10, 21, 14, 30)
    assert parse_start("2026-10-21T09:00") == datetime(2026, 10, 21, 9, 0)
    with pytest.raises(ValidationError, match="^start:"):
        parse_start("tomorrow at 2")
