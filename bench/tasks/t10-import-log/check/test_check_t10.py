from datetime import date

import pytest

from petclinic.importer import import_csv, parse_birth_date
from petclinic.store import Store

CSV = """owner_name,owner_phone,pet_name,species,birth_date,notes
Hana Lee,021 555 0188,Ziggy,cat,03/11/2019,
Hana Lee,021 555 0188,Fern,rabbit,23/07/2017,
Finn Scott,027 555 0135,Bear,dog,2018-05-30,
Arjun Singh,phone him,Taco,dog,14/02/2020,
Maia Hall,022 555 0161,Olive,cat,31/02/2019,
Maia Hall,022 555 0161,Rex,canine,2015-06-14,
Maia Hall,022 555 0161,Tom,feline,2012-09-30,
Maia Hall,022 555 0161,Slinky,reptile,2019-04-01,
Maia Hall,022 555 0161,Bandit,ferret,2021-02-11,
"""


def imported(tmp_path):
    path = tmp_path / "export.csv"
    path.write_text(CSV, encoding="utf-8")
    store = Store()
    return store, import_csv(store, path)


def test_day_first_dates():
    assert parse_birth_date("03/11/2019") == date(2019, 11, 3)
    assert parse_birth_date("23/07/2017") == date(2017, 7, 23)


def test_iso_dates_still_work():
    assert parse_birth_date("2019-11-03") == date(2019, 11, 3)


def test_impossible_dates_are_rejected():
    with pytest.raises(ValueError):
        parse_birth_date("31/02/2019")
    with pytest.raises(ValueError):
        parse_birth_date("unknown")


def test_import_keeps_the_good_rows(tmp_path):
    store, result = imported(tmp_path)
    assert (result.pets_added, result.skipped) == (5, 4)
    born = {p.name: p.birth_date for p in store.pets.values()}
    assert born == {"Ziggy": date(2019, 11, 3), "Fern": date(2017, 7, 23), "Bear": date(2018, 5, 30),
                    "Rex": date(2015, 6, 14), "Tom": date(2012, 9, 30)}


def test_clinicmaster_3_species_names(tmp_path):
    store, _ = imported(tmp_path)
    species = {p.name: p.species for p in store.pets.values()}
    assert (species["Rex"], species["Tom"]) == ("dog", "cat")


def test_rows_skipped_for_a_good_reason_still_are(tmp_path):
    store, _ = imported(tmp_path)
    names = {p.name for p in store.pets.values()}
    assert not names & {"Taco", "Olive", "Slinky", "Bandit"}
    assert "Arjun Singh" not in {o.name for o in store.owners.values()}
