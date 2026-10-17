import json
from datetime import date, datetime
from pathlib import Path

import pytest

from petclinic.booking import BookingRequest, find_client
from petclinic.cli import main
from petclinic.errors import ValidationError
from petclinic.importer import import_csv
from petclinic.search import describe, search
from petclinic.sms import Outbox, queue_for_owner
from petclinic.store import Store

FIXTURE = Path(__file__).parent / "fixtures" / "clinic.json"
OLD = {"owners": [{"id": 1, "name": "Mei Lin", "telephone": "022-555-0142"}], "pets": [], "visits": []}


def test_owner_has_a_phone():
    owner = Store().add_owner("Ann Lee", "021 555 0101")
    assert owner.phone == "021 555 0101"
    assert not hasattr(owner, "telephone")


def test_bad_number_messages_name_the_field():
    with pytest.raises(ValidationError, match="^phone:"):
        Store().add_owner("Ann Lee", "call me")
    store = Store()
    store.add_owner("Ann Lee", "021 555 0101")
    with pytest.raises(ValidationError, match="^phone:"):
        store.update_owner(1, phone="call me")


def test_update_owner_takes_phone():
    store = Store()
    store.add_owner("Ann Lee", "021 555 0101")
    assert store.update_owner(1, phone="021 555 0202").phone == "021 555 0202"


def test_old_files_still_load(tmp_path):
    path = tmp_path / "old.json"
    path.write_text(json.dumps(OLD), encoding="utf-8")
    assert Store.load(path).owners[1].phone == "022-555-0142"
    assert Store.load(FIXTURE).owners[3].phone == "022-555-0142"


def test_new_files_say_phone(tmp_path):
    path = tmp_path / "old.json"
    path.write_text(json.dumps(OLD), encoding="utf-8")
    Store.load(path).save()
    owner = json.loads(path.read_text(encoding="utf-8"))["owners"][0]
    assert owner["phone"] == "022-555-0142"
    assert "telephone" not in owner


def test_cli_commands_that_show_numbers(tmp_path, capsys):
    data = tmp_path / "clinic.json"
    data.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    for args in (["owners"], ["owner", "1"], ["search", "0142"], ["reminders", "--on", "2026-10-21"],
                 ["overdue", "--on", "2027-06-01"], ["add-owner", "Hemi Walker", "021 555 0876"]):
        assert main(["--data", str(data), *args]) == 0, args
    out = capsys.readouterr().out
    assert "021 555 0101" in out and "022-555-0142: Kia ora Mei!" in out


def test_other_modules_read_the_phone():
    store = Store.load(FIXTURE)
    owner, pet = find_client(store, BookingRequest("Mei Lin", "022 555 0142", "Mochi", datetime(2026, 10, 23, 9, 0), "x"))
    assert (owner.id, pet.id) == (3, 4)
    assert "022-555-0142" in describe(store, search(store, "0142")[0])


def test_texts_and_imports(tmp_path):
    store = Store.load(FIXTURE)
    outbox = Outbox(tmp_path / "outbox.json")
    queue_for_owner(outbox, store.owners[1], "hello")
    assert outbox.load()[0].to == "021 555 0101"
    store.path = tmp_path / "clinic.json"
    export = tmp_path / "export.csv"
    export.write_text("owner_name,owner_phone,pet_name,species,birth_date,notes\n"
                      "Hemi Walker,021 555 0876,Rua,dog,2022-08-01,\n", encoding="utf-8")
    assert import_csv(store, export).owners_added == 1
    assert store.owners[6].phone == "021 555 0876"
    assert date(2022, 8, 1) == store.pets[7].birth_date
