from collections import Counter
from datetime import date
from pathlib import Path

from petclinic.admin import possible_duplicates
from petclinic.cli import main
from petclinic.importer import import_csv
from petclinic.store import Store

DATA = Path(__file__).parent.parent / "clinic.json"
CSV = """owner_name,owner_phone,pet_name,species,birth_date,notes
mei lin,022-555-0142,Mochi,cat,2021-07-08,
Mei Lin ,022-555-0142,Bao,cat,2024-01-15,new kitten
 Ben  Carter,027 555 0199,Rocket,rabbit,2024-02-29,
BEN CARTER,027 555 0199,Comet,rabbit,2025-03-01,
Tama Wiremu ,021 555 0177,Bella,dog,2020-03-14,
"""


def small_clinic():
    store = Store()
    mei = store.add_owner("Mei Lin", "022-555-0142")
    store.add_pet(mei.id, "Mochi", "cat", date(2021, 7, 8))
    ben = store.add_owner("Ben Carter", "027 555 0199")
    store.add_pet(ben.id, "Rocket", "rabbit", date(2024, 2, 29))
    return store


def export(tmp_path):
    path = tmp_path / "export.csv"
    path.write_text(CSV, encoding="utf-8")
    return path


# the cause: the import must recognise clients typed in another case or spacing

def test_case_and_spaces_dont_make_a_new_owner(tmp_path):
    store = small_clinic()
    result = import_csv(store, export(tmp_path))
    assert result.owners_added == 1
    assert sorted(o.name for o in store.owners.values()) == ["Ben Carter", "Mei Lin", "Tama Wiremu"]
    assert sorted(p.name for p in store.pets_of(1)) == ["Bao", "Mochi"]
    assert sorted(p.name for p in store.pets_of(2)) == ["Comet", "Rocket"]


def test_importing_twice_adds_nothing(tmp_path):
    store = small_clinic()
    import_csv(store, export(tmp_path))
    again = import_csv(store, export(tmp_path))
    assert (again.owners_added, again.pets_added) == (0, 0)
    assert (len(store.owners), len(store.pets)) == (3, 5)


# the clean-up: the duplicates merged into the original records, the genuinely new clients kept

def test_no_duplicate_owners_are_left():
    store = Store.load(DATA)
    assert possible_duplicates(store) == [(8, 19)]  # two different people called Sam Wilson
    assert set(store.owners) == set(range(1, 50)) | {52}  # 49 and 52 are new clients from that import
    assert [store.owners[i].name for i in (1, 3, 6, 14, 20)] == [
        "Aroha Ngata", "Mei Lin", "Lena Chen", "Daniel Te Whata", "Nikau Jones"]


def test_different_people_with_the_same_name_are_kept_apart():
    store = Store.load(DATA)
    assert [store.owners[8].email, store.owners[19].email] == ["sam.wilson@example.com", ""]
    assert [p.name for p in store.pets_of(8)] == ["Loki"]
    assert [p.name for p in store.pets_of(19)] == ["Poppy"]


def test_the_pets_were_merged_not_lost():
    store = Store.load(DATA)
    assert len(store.pets) == 79
    assert sorted(p.name for p in store.pets_of(1)) == ["Kiwi", "Pip"]
    assert [p.id for p in store.pets_of(3)] == [4]
    assert {(r.vaccine, r.given) for r in store.vaccinations if r.pet_id == 4} == {
        ("F3", date(2026, 10, 14)), ("FeLV", date(2025, 10, 25))}
    assert sorted(p.name for p in store.pets_of(52)) == ["Nugget"]


def test_one_text_per_number(capsys):
    main(["--data", str(DATA), "reminders", "--on", "2026-10-21"])
    lines = [line for line in capsys.readouterr().out.splitlines() if not line.startswith("(")]
    numbers = Counter(line.split(": ", 1)[0] for line in lines)
    assert max(numbers.values()) == 1
    assert ("021 555 0101: Kia ora Aroha! Kiwi and Pip are due for DHPP, F3 and Kennel cough on Wed 28 Oct. Book online "
            "or call Harbourside Vets on 09 555 0100.") in lines
