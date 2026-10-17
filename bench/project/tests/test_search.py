from petclinic import audit
from petclinic.names import initials, normalise_name, same_name
from petclinic.phones import international, is_landline, looks_valid, same_number
from petclinic.search import Hit, describe, search
from petclinic.store import Store


def test_search_by_name(clinic):
    assert search(clinic, "lin") == [Hit(3, None, "name")]


def test_search_by_number(clinic):
    assert search(clinic, "0142") == [Hit(3, None, "number")]
    assert search(clinic, "555") == []  # too few digits to be a number


def test_search_by_pet_and_microchip(clinic):
    assert search(clinic, "kiwi") == [Hit(1, 1, "pet")]
    assert search(clinic, "985141000654321") == [Hit(3, 4, "microchip")]


def test_describe(clinic):
    line = describe(clinic, Hit(3, 4, "pet"))
    assert "Mei Lin" in line and "022-555-0142" in line and line.endswith("Mochi (cat)")


def test_names():
    assert normalise_name("  Ben   Carter ") == "Ben Carter"
    assert same_name("mei lin", " Mei  Lin")
    assert not same_name("Mei Lin", "Mei Ling")
    assert initials("Dr Hine Tane") == "HT"


def test_phones():
    assert looks_valid("022-555-0142") and not looks_valid("ring after 5") and not looks_valid("- -")
    assert is_landline("09 555 0100") and not is_landline("021 555 0101")
    assert same_number("022-555-0142", "022 555 0142")
    assert international("021 555 0101") == "+64215550101"


def test_audit_trail(tmp_path):
    from datetime import datetime
    store = Store()
    audit.record(store, "admin", "nothing to write to")  # no file: no trail
    assert audit.entries(store) == []
    store.path = tmp_path / "clinic.json"
    audit.record(store, "admin", "owner 6 merged into owner 3", when=datetime(2026, 10, 19, 9, 0))
    audit.record(store, "import", "pet 9 added", when=datetime(2026, 10, 20, 6, 0))
    assert audit.entries(store) == ["2026-10-19 09:00:00  admin        owner 6 merged into owner 3",
                                    "2026-10-20 06:00:00  import       pet 9 added"]
    assert audit.entries(store, since=datetime(2026, 10, 20)) == ["2026-10-20 06:00:00  import       pet 9 added"]
    assert len(audit.entries(store, who="admin")) == 1
