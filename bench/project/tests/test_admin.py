from datetime import date, datetime

import pytest

from petclinic.admin import merge_owners, merge_pets, possible_duplicates
from petclinic.errors import ValidationError


def test_merge_pets_moves_visits_and_vaccinations(clinic):
    duplicate = clinic.add_pet(1, "Kiwi", "dog", date(2019, 4, 12))
    clinic.book_visit(duplicate.id, datetime(2026, 10, 20, 9, 0), "booked online")
    clinic.add_vaccination(duplicate.id, "DHPP", date(2023, 10, 28))          # the same dose, recorded twice
    clinic.add_vaccination(duplicate.id, "Kennel cough", date(2024, 10, 30))  # not on file yet
    assert [v.id for v in clinic.visits_for_pet(duplicate.id)] == [9]
    assert merge_pets(clinic, 1, duplicate.id) == 1
    assert duplicate.id not in clinic.pets
    assert [v.id for v in clinic.visits_for_pet(1)] == [1, 5, 9]
    assert [(r.vaccine, r.given) for r in clinic.vaccinations_for(1)] == [
        ("DHPP", date(2023, 10, 28)), ("Kennel cough", date(2024, 10, 30)), ("Kennel cough", date(2025, 10, 30))]


def test_merge_pets_needs_the_same_species(clinic):
    with pytest.raises(ValidationError, match="^duplicate_id:"):
        merge_pets(clinic, 1, 2)  # Kiwi is a dog, Pip a cat


def test_merge_owners(clinic):
    duplicate = clinic.add_owner("mei lin", "022 555 0142")
    clinic.add_pet(duplicate.id, "Mochi", "cat", date(2021, 7, 8))
    clinic.add_pet(duplicate.id, "Bao", "cat", date(2024, 1, 15))
    assert merge_owners(clinic, 3, duplicate.id) == ["Mochi: merged into pet 4", "Bao: moved"]
    assert duplicate.id not in clinic.owners
    assert sorted(p.name for p in clinic.pets_of(3)) == ["Bao", "Mochi"]


def test_an_owner_cant_be_merged_into_themselves(clinic):
    with pytest.raises(ValidationError, match="^duplicate_id:"):
        merge_owners(clinic, 3, 3)


def test_possible_duplicates(clinic):
    clinic.add_owner(" AROHA  NGATA", "021 555 0101")
    assert possible_duplicates(clinic) == [(1, 6)]
