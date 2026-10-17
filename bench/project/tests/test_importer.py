from datetime import date

import pytest

from petclinic import audit
from petclinic.errors import ValidationError
from petclinic.importer import import_csv, parse_birth_date
from petclinic.store import Store

CSV = """owner_name,owner_phone,pet_name,species,birth_date,notes
Tama Wiremu,021 555 0177,Bella,dog,2020-03-14,
Tama Wiremu,021 555 0177,Rua,dog,2022-08-01,Bella's brother
Grace Kim,09 555 0123,Luna,cat,2023-01-09,
Liam Brown,ring after 5,Max,dog,2018-06-30,
Ana Lopez,027 555 0111,Coco,cat,unknown,
Ana Lopez,027 555 0111,Slinky,Lizard,2021-05-05,
"""


def export(tmp_path, text=CSV):
    path = tmp_path / "export.csv"
    path.write_text(text, encoding="utf-8")
    return path


def test_iso_birth_dates():
    assert parse_birth_date("2019-11-03") == date(2019, 11, 3)
    assert parse_birth_date(" 2019-11-03 ") == date(2019, 11, 3)


def test_import(tmp_path):
    store = Store()
    result = import_csv(store, export(tmp_path))
    assert (result.owners_added, result.pets_added, result.skipped) == (2, 3, 3)
    assert sorted(o.name for o in store.owners.values()) == ["Grace Kim", "Tama Wiremu"]
    tama = store.find_owners("Tama")[0]
    assert sorted(p.name for p in store.pets_of(tama.id)) == ["Bella", "Rua"]
    assert store.pets[1].birth_date == date(2020, 3, 14)


def test_a_pet_already_on_file_is_not_added_again(tmp_path):
    store = Store()
    owner = store.add_owner("Grace Kim", "09 555 0123")
    store.add_pet(owner.id, "Luna", "cat", date(2023, 1, 9))
    result = import_csv(store, export(tmp_path))
    assert (result.owners_added, result.pets_added) == (1, 2)
    assert [p.name for p in store.pets_of(owner.id)] == ["Luna"]


def test_species_the_clinic_doesnt_treat_are_skipped(tmp_path):
    store = Store()
    import_csv(store, export(tmp_path))
    assert "Slinky" not in {p.name for p in store.pets.values()}


def test_an_export_without_the_columns_is_refused(tmp_path):
    with pytest.raises(ValidationError, match="^columns:"):
        import_csv(Store(), export(tmp_path, "name,phone\nGrace Kim,09 555 0123\n"))


def test_the_import_is_in_the_audit_trail(tmp_path):
    store = Store()
    store.path = tmp_path / "clinic.json"
    import_csv(store, export(tmp_path))
    trail = audit.entries(store, who="import")
    assert len(trail) == 5  # 2 owners, 3 pets
    assert trail[0].endswith("owner 1 added: 'Tama Wiremu' (021 555 0177)")
