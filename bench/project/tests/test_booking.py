from datetime import date, datetime, time

import pytest
from conftest import FIXTURES

from petclinic.booking import BookingRequest, available, book, find_client, week_ahead
from petclinic.errors import ValidationError
from petclinic.scheduling import slots_for_day
from petclinic.staff import load_staff

VETS, LEAVE = load_staff(FIXTURES / "staff.json")


def test_free_times_on_a_normal_day(clinic):
    offer = available(clinic, date(2026, 10, 22), VETS, LEAVE)
    assert offer.times == [t for t in slots_for_day(date(2026, 10, 22)) if t != time(10, 30)]  # Rocket's nail trim
    assert offer.times[:3] == [time(9, 0), time(9, 30), time(10, 0)]
    assert offer.vets == VETS


def test_a_vet_on_leave_is_not_offered(clinic):
    assert available(clinic, date(2026, 11, 4), VETS, LEAVE, vet_id=1).times == []
    assert available(clinic, date(2026, 11, 4), VETS, LEAVE, vet_id=2).times == slots_for_day(date(2026, 11, 4))


def test_weekends_are_not_offered(clinic):
    assert available(clinic, date(2026, 10, 24), VETS, LEAVE).times == []


def test_the_week_ahead(clinic):
    offers = week_ahead(clinic, VETS, LEAVE, today=date(2026, 10, 27))
    assert [o.day for o in offers] == [date(2026, 10, 28), date(2026, 10, 29), date(2026, 10, 30),
                                       date(2026, 11, 2), date(2026, 11, 3), date(2026, 11, 4), date(2026, 11, 5)]


def test_find_client_by_name_and_number(clinic):
    request = BookingRequest("mei lin", "022 555 0142", "mochi", datetime(2026, 10, 23, 9, 0), "check-up")
    owner, pet = find_client(clinic, request)
    assert (owner.id, pet.id) == (3, 4)


def test_unknown_clients_are_refused(clinic):
    request = BookingRequest("Mei Lin", "021 000 0000", "Mochi", datetime(2026, 10, 23, 9, 0), "check-up")
    with pytest.raises(ValidationError):
        find_client(clinic, request)
    request = BookingRequest("Mei Lin", "022-555-0142", "Bao", datetime(2026, 10, 23, 9, 0), "check-up")
    with pytest.raises(ValidationError, match="^pet_name:"):
        find_client(clinic, request)


def test_book_from_the_page(clinic):
    request = BookingRequest("Ben Carter", "027-555-0199", "Rocket", datetime(2026, 10, 22, 11, 0), "check-up", 3)
    visit = book(clinic, request, VETS, LEAVE)
    assert (visit.id, visit.pet_id, visit.vet_id) == (9, 3, 3)


def test_a_taken_time_is_refused(clinic):
    request = BookingRequest("Ben Carter", "027 555 0199", "Rocket", datetime(2026, 10, 22, 10, 30), "check-up")
    with pytest.raises(ValidationError, match="^start:"):
        book(clinic, request, VETS, LEAVE)


def test_a_vet_on_leave_cannot_be_booked(clinic):
    request = BookingRequest("Ben Carter", "027 555 0199", "Rocket", datetime(2026, 11, 4, 10, 0), "check-up", 1)
    with pytest.raises(ValidationError, match="^start:"):
        book(clinic, request, VETS, LEAVE)
