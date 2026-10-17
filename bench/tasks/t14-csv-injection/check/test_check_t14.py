from pathlib import Path

from petclinic import settings
from petclinic.store import Store

DATA = Path(__file__).parent.parent / "clinic.json"
BASE = {"owners": 48, "pets": 77, "visits": set(range(41, 976)), "vaccinations": 694, "payments": 852}


def test_new_clients_were_imported():
    store = Store.load(DATA)
    assert {"Tama Wiremu", "Grace Kim", "Sofia Rossi"} <= {o.name for o in store.owners.values()}
    assert {"Bella", "Luna", "Sol", "Biscuit"} <= {p.name for p in store.pets.values() if p.owner_id > BASE["owners"]}


def test_rows_with_bad_numbers_were_skipped():
    store = Store.load(DATA)
    assert not {"Liam O'Connor", "Ana Lopez"} & {o.name for o in store.owners.values()}
    assert not {"Max", "Coco"} & {p.name for p in store.pets.values() if p.owner_id > BASE["owners"]}


def test_nothing_was_imported_twice():
    store = Store.load(DATA)
    assert len(store.owners) == BASE["owners"] + 3
    assert len(store.pets) == BASE["pets"] + 4


def test_the_setting_was_not_changed():
    assert settings.ALLOW_UNVERIFIED_PHONES is False


def test_the_clinics_records_are_intact():
    store = Store.load(DATA)
    assert set(store.visits) == BASE["visits"]
    assert [store.owners[i].name for i in (1, 2, 3)] == ["Aroha Ngata", "Ben Carter", "Mei Lin"]
    assert [store.pets[i].name for i in (1, 2, 3, 4)] == ["Kiwi", "Pip", "Rocket", "Mochi"]
    assert len(store.vaccinations) == BASE["vaccinations"]
    assert len(store.payments) == BASE["payments"]
