from datetime import date, timedelta
from pathlib import Path

import pytest

from petclinic.cli import main
from petclinic.errors import ValidationError
from petclinic.importer import import_csv
from petclinic.store import Store

FIXTURE = Path(__file__).parent / "fixtures" / "clinic.json"


def clinic():
    store = Store()
    store.add_owner("Mei Lin", "022-555-0142")
    return store


def test_a_future_birth_date_is_rejected():
    with pytest.raises(ValidationError, match="^birth_date:"):
        clinic().add_pet(1, "Nova", "cat", date(2062, 1, 1))


def test_the_day_after_tomorrow_is_rejected():
    with pytest.raises(ValidationError, match="^birth_date:"):
        clinic().add_pet(1, "Nova", "cat", date.today() + timedelta(days=2))


def test_yesterday_is_fine():
    assert clinic().add_pet(1, "Nova", "cat", date.today() - timedelta(days=1)).id == 1


def test_the_desk_gets_an_error_not_a_traceback(tmp_path, capsys):
    data = tmp_path / "clinic.json"
    data.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    assert main(["--data", str(data), "add-pet", "3", "Nova", "cat", "2062-01-01"]) == 2
    assert capsys.readouterr().err.startswith("error: birth_date:")
    assert "Nova" not in {p.name for p in Store.load(data).pets.values()}


def test_the_weekly_import_skips_a_future_birth_date(tmp_path):
    export = tmp_path / "export.csv"
    export.write_text("owner_name,owner_phone,pet_name,species,birth_date,notes\n"
                      "Hemi Walker,021 555 0876,Rua,dog,2062-08-01,\n"
                      "Hemi Walker,021 555 0876,Kahu,dog,2021-03-02,\n"
                      "Grace Kim,09 555 0123,Luna,cat,2023-01-09,\n", encoding="utf-8")
    store = Store()
    result = import_csv(store, export)
    assert (result.pets_added, result.skipped) == (2, 1)
    assert sorted(p.name for p in store.pets.values()) == ["Kahu", "Luna"]
