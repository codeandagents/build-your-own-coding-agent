from datetime import date

import pytest

from petclinic.errors import ValidationError
from petclinic.periods import Period


def test_a_period_is_half_open():
    period = Period(date(2026, 11, 2), date(2026, 11, 6))
    assert date(2026, 11, 2) in period
    assert date(2026, 11, 5) in period
    assert date(2026, 11, 6) not in period
    assert len(period) == 4


def test_inclusive_takes_the_last_day():
    period = Period.inclusive(date(2026, 11, 2), date(2026, 11, 6))
    assert period.end == date(2026, 11, 7)
    assert period.last_day == date(2026, 11, 6)
    assert date(2026, 11, 6) in period
    assert date(2026, 11, 7) not in period


def test_months():
    assert Period.month(2026, 12) == Period(date(2026, 12, 1), date(2027, 1, 1))
    assert Period.parse_month("2026-10") == Period(date(2026, 10, 1), date(2026, 11, 1))
    assert len(Period.month(2028, 2)) == 29
    with pytest.raises(ValidationError, match="^month:"):
        Period.parse_month("October")


def test_end_before_start():
    with pytest.raises(ValidationError, match="^end:"):
        Period(date(2026, 11, 6), date(2026, 11, 2))


def test_months_that_meet_dont_overlap():
    assert not Period.month(2026, 10).overlaps(Period.month(2026, 11))
    assert Period.month(2026, 10).overlaps(Period(date(2026, 10, 31), date(2026, 11, 3)))


def test_weekdays():
    days = list(Period(date(2026, 11, 2), date(2026, 11, 9)).weekdays())
    assert days == [date(2026, 11, d) for d in (2, 3, 4, 5, 6)]


def test_label_shows_the_last_day():
    assert Period(date(2026, 11, 2), date(2026, 11, 7)).label() == "Mon 2 Nov to Fri 6 Nov 2026"
    assert Period(date(2026, 12, 21), date(2027, 1, 9)).label() == "Mon 21 Dec 2026 to Fri 8 Jan 2027"
