from datetime import date

from petclinic.store import Store
from petclinic.vaccinations import add_months, due_within, history, next_due, overdue


def small_clinic():
    store = Store()
    owner = store.add_owner("Aroha Ngata", "021 555 0101")
    kiwi = store.add_pet(owner.id, "Kiwi", "dog", date(2019, 4, 12))
    pip = store.add_pet(owner.id, "Pip", "cat", date(2022, 11, 3))
    store.add_vaccination(kiwi.id, "DHPP", date(2023, 10, 28))
    store.add_vaccination(kiwi.id, "Kennel cough", date(2024, 10, 30))
    store.add_vaccination(kiwi.id, "Kennel cough", date(2025, 10, 30))
    store.add_vaccination(pip.id, "F3", date(2023, 11, 2))
    store.add_vaccination(pip.id, "FeLV", date(2026, 3, 10))
    return store


def test_add_months():
    assert add_months(date(2026, 10, 28), 12) == date(2027, 10, 28)
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2027, 12, 15), 2) == date(2028, 2, 15)
    assert add_months(date(2024, 2, 29), 36) == date(2027, 2, 28)


def test_next_dose_counts_from_the_latest_one():
    store = small_clinic()
    assert next_due(store, store.pets[1]) == {"DHPP": date(2026, 10, 28), "Kennel cough": date(2026, 10, 30)}


def test_first_dose_at_eight_weeks():
    store = Store()
    owner = store.add_owner("Ben Carter", "027 555 0199")
    rocket = store.add_pet(owner.id, "Rocket", "rabbit", date(2024, 2, 29))
    assert next_due(store, rocket) == {"RHDV": date(2024, 4, 25)}


def test_no_schedule_for_birds():
    store = Store()
    owner = store.add_owner("Ben Carter", "027 555 0199")
    assert next_due(store, store.add_pet(owner.id, "Tui", "bird", date(2024, 2, 1))) == {}


def test_due_within_a_window_soonest_first():
    due = due_within(small_clinic(), date(2026, 10, 21), 14)
    assert [(pet.name, vaccine, day) for pet, vaccine, day in due] == [
        ("Kiwi", "DHPP", date(2026, 10, 28)),
        ("Kiwi", "Kennel cough", date(2026, 10, 30)),
        ("Pip", "F3", date(2026, 11, 2)),
    ]


def test_nothing_due_in_a_quiet_window():
    assert due_within(small_clinic(), date(2026, 6, 1), 14) == []


def test_overdue_by_more_than_a_month():
    late = overdue(small_clinic(), date(2026, 12, 15), 30)
    assert [(pet.name, vaccine) for pet, vaccine, _ in late] == [
        ("Kiwi", "DHPP"), ("Kiwi", "Kennel cough"), ("Pip", "F3")]
    assert overdue(small_clinic(), date(2026, 11, 20), 30) == []


def test_history():
    store = small_clinic()
    assert history(store, store.pets[2]) == ["2023-11-02  F3", "2026-03-10  FeLV"]
