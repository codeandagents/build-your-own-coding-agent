from datetime import date, datetime, timezone

from petclinic.scheduling import clinic_today, next_free_slot

# 23:30 UTC on Tuesday 20 October is 12:30 on Wednesday 21 October in Auckland (NZDT, UTC+13).
SERVER_NOW = datetime(2026, 10, 20, 23, 30, tzinfo=timezone.utc)


def test_today_is_the_clinics_date():
    assert clinic_today(SERVER_NOW) == date(2026, 10, 21)


def test_next_slot_from_a_utc_server():
    assert next_free_slot([], SERVER_NOW) == datetime(2026, 10, 21, 13, 0)


def test_next_slot_skips_booked_times_from_a_utc_server():
    assert next_free_slot([datetime(2026, 10, 21, 13, 0)], SERVER_NOW) == datetime(2026, 10, 21, 13, 30)
