from datetime import date, datetime

import pytest

from petclinic.errors import NotFound, ValidationError
from petclinic.store import Store


def small_clinic():
    store = Store()
    owner = store.add_owner("Aroha Ngata", "021 555 0101")
    store.add_pet(owner.id, "Kiwi", "dog", date(2019, 4, 12))
    return store


def test_find_owners_ignores_case():
    store = small_clinic()
    store.add_owner("Ben Carter", "027 555 0199")
    assert [o.name for o in store.find_owners("aroha")] == ["Aroha Ngata"]


def test_owner_needs_a_name():
    with pytest.raises(ValidationError, match="^name:"):
        Store().add_owner("  ", "021 555 0101")


def test_owner_number_takes_digits_only():
    with pytest.raises(ValidationError):
        Store().add_owner("Ben Carter", "call me")


def test_email_needs_an_at():
    with pytest.raises(ValidationError, match="^email:"):
        Store().add_owner("Ben Carter", "027 555 0199", "ben.carter")


def test_update_owner():
    store = small_clinic()
    owner = store.update_owner(1, name="Aroha Ngata-Smith ", email="aroha@example.com")
    assert (owner.name, owner.email) == ("Aroha Ngata-Smith", "aroha@example.com")
    with pytest.raises(ValidationError, match="^name:"):
        store.update_owner(1, name=" ")


def test_pet_needs_an_owner():
    with pytest.raises(ValidationError, match="^owner_id:"):
        Store().add_pet(42, "Kiwi", "dog", date(2019, 4, 12))


def test_species_is_stored_in_lower_case():
    store = small_clinic()
    assert store.add_pet(1, "Rua", " Dog ", date(2022, 8, 1)).species == "dog"


def test_microchip_has_15_digits():
    with pytest.raises(ValidationError, match="^microchip:"):
        small_clinic().add_pet(1, "Rua", "dog", date(2022, 8, 1), microchip="98514")


def test_missing_records():
    store = small_clinic()
    with pytest.raises(NotFound, match="^visit_id:"):
        store.visit(99)
    with pytest.raises(NotFound, match="^owner_id:"):
        store.owner(7)


def test_a_slot_can_be_booked_once():
    store = small_clinic()
    start = datetime(2026, 10, 21, 10, 0)
    store.book_visit(1, start, "check-up")
    with pytest.raises(ValidationError, match="^start:"):
        store.book_visit(1, start, "again")


def test_visits_for_pet_oldest_first():
    store = small_clinic()
    store.book_visit(1, datetime(2026, 10, 22, 9, 0), "second")
    store.book_visit(1, datetime(2026, 10, 21, 9, 0), "first")
    assert [v.reason for v in store.visits_for_pet(1)] == ["first", "second"]


def test_cancel_and_reschedule():
    store = small_clinic()
    first = store.book_visit(1, datetime(2026, 10, 21, 9, 0), "first")
    second = store.book_visit(1, datetime(2026, 10, 21, 9, 30), "second")
    store.cancel_visit(first.id)
    store.reschedule_visit(second.id, datetime(2026, 10, 23, 11, 0))
    assert store.visits_on(date(2026, 10, 21)) == []
    assert [v.id for v in store.visits_on(date(2026, 10, 23))] == [second.id]
    with pytest.raises(ValidationError, match="^visit_id:"):
        store.cancel_visit(first.id)


def test_purge_before_a_date(clinic):
    assert clinic.purge_visits(date(2026, 10, 13)) == 2
    assert sorted(clinic.visits) == [2, 3, 4, 5, 6, 8]


def test_visits_for_owner(clinic):
    assert [v.id for v in clinic.visits_for_owner(1)] == [1, 4, 5]


def test_payments_are_checked(clinic):
    with pytest.raises(ValidationError, match="^method:"):
        clinic.add_payment(5, 9775, "cheque", datetime(2026, 10, 16, 15, 0))
    with pytest.raises(ValidationError, match="^cents:"):
        clinic.add_payment(5, 97.75, "cash", datetime(2026, 10, 16, 15, 0))
    assert clinic.add_payment(5, 9775, "cash", datetime(2026, 10, 16, 15, 0)).id == 5


def test_the_fixture_loads(clinic):
    counts = (len(clinic.owners), len(clinic.pets), len(clinic.visits), len(clinic.vaccinations), len(clinic.payments))
    assert counts == (5, 6, 8, 11, 4)
    assert clinic.owners[5].insurer == "PetCover"
    assert clinic.visits[7].vet_id is None


def test_save_and_load(tmp_path):
    store = small_clinic()
    store.path = tmp_path / "clinic.json"
    store.book_visit(1, datetime(2026, 10, 21, 9, 30), "check-up", vet_id=2)
    store.add_payment(1, 9775, "eftpos", datetime(2026, 10, 21, 10, 5))
    store.save()
    again = Store.load(store.path)
    assert again.pets[1].birth_date == date(2019, 4, 12)
    assert again.visits[1].start == datetime(2026, 10, 21, 9, 30)
    assert again.visits[1].vet_id == 2
    assert again.payments[1].paid == datetime(2026, 10, 21, 10, 5)
    assert again.owners[1].name == "Aroha Ngata"


def test_saved_file_has_one_record_per_line(tmp_path):
    store = small_clinic()
    store.path = tmp_path / "clinic.json"
    store.save()
    lines = store.path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "{"
    assert any(line.strip().startswith('{"id": 1, "name": "Kiwi"') for line in lines)
    assert '"email"' not in store.path.read_text(encoding="utf-8")  # empty optional fields are left out
