"""Writes t08's start/ and solution/ folders from the base project. Deterministic: running it again writes the same files.

The story: on Monday 19 October 06:00 the weekly import ran with the bug (importer.find_owner compares names exactly),
so clients the Devonport branch typed differently ("mei lin", "AROHA NGATA", "LENA CHEN", ...) became new owners
with copies of their pets. Wednesday's reminders then texted them twice. The solved state is that data after
`merge-owners` for each duplicate, keeping the original records.
Run from the repo root: .venv/Scripts/python bench/tasks/t08-duplicate-owners/make_start.py"""
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).parent
PROJECT = HERE.parent.parent / "project"
sys.path.insert(0, str(PROJECT))

from petclinic import admin, importer  # noqa: E402
from petclinic.store import Store  # noqa: E402

MONDAY = datetime(2026, 10, 19, 6, 0, 1, 37_000)
EXPORT = """owner_name,owner_phone,pet_name,species,birth_date,notes
Mere Ruakere,021 555 0390,Toby,dog,2025-12-01,
mei lin,022-555-0142,Mochi,cat,2021-07-08,seen at Devonport
AROHA NGATA,021 555 0101,Kiwi,dog,2019-04-12,seen at Devonport
AROHA NGATA,021 555 0101,Pip,cat,2022-11-03,seen at Devonport
Josh Tamati,027 555 0458,Nugget,guinea pig,2025-06-10,
Daniel  Te Whata,022 555 0763,Coco,cat,2016-01-15,seen at Devonport
LENA CHEN,027 555 0716,Sushi,cat,2020-01-24,seen at Devonport
nikau jones ,022-555-0804,Pickle,dog,2024-12-25,seen at Devonport
"""
DUPLICATES = {50: 3, 51: 1, 53: 14, 54: 6, 55: 20}  # duplicate owner id -> the original to keep
# Owners 8 and 19 are two different people called Sam Wilson (different numbers and pets): not duplicates.


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")


def main() -> None:
    work = HERE / "_build"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir()
    (work / "export.csv").write_text(EXPORT, encoding="utf-8", newline="")
    store = Store.load(PROJECT / "clinic.json")
    store.path = work / "clinic.json"
    numbers = {o.telephone.replace("-", " ") for o in store.owners.values()}
    assert "021 555 0390" not in numbers and "027 555 0458" not in numbers

    # the bug, as start.json puts it in importer.py
    exact = lambda store, name: next((o for o in store.owners.values() if o.name == name), None)  # noqa: E731
    importer.find_owner = exact
    result = importer.import_csv(store, work / "export.csv")
    assert (result.owners_added, result.pets_added, result.skipped) == (7, 8, 0), result
    assert sorted(o.id for o in store.owners.values() if o.id > 48) == [49, 50, 51, 52, 53, 54, 55]

    # the log and audit lines the 06:00 run wrote (the in-process run above stamped them with today's time)
    clock, log, trail = MONDAY, [], []
    owner_rows = {}
    for number, line in enumerate(EXPORT.splitlines()[1:], start=2):
        name, phone, pet, species, born, _ = line.split(",")
        clock += timedelta(milliseconds=7 + number * 3)
        stamp = clock.strftime("%Y-%m-%d %H:%M:%S") + f",{clock.microsecond // 1000:03d}"
        owner = next(o for o in store.owners.values() if o.id > 48 and o.name == name.strip())
        if owner.id not in owner_rows:
            owner_rows[owner.id] = number
            trail.append(f"{clock:%Y-%m-%d %H:%M:%S}  {'import':11}  owner {owner.id} added: {owner.name!r} "
                         f"({owner.telephone})")
        pet_id = next(p.id for p in store.pets_of(owner.id) if p.name == pet)
        trail.append(f"{clock:%Y-%m-%d %H:%M:%S}  {'import':11}  pet {pet_id} added: {pet} ({species}) for owner "
                     f"{owner.id}")
        log.append(f"{stamp} INFO petclinic.importer: row {number}: {pet} ({species}) for {owner.name}")
    clock += timedelta(milliseconds=4)
    log.append(f"{clock:%Y-%m-%d %H:%M:%S},{clock.microsecond // 1000:03d} INFO petclinic.importer: import finished: "
               f"7 owners and 8 pets added, 0 rows skipped")

    start = HERE / "start"
    write(start / "clinic.json", store.to_json())
    write(start / "data" / "exports" / "clinicmaster-2026-10-19.csv", EXPORT)
    write(start / "logs" / "import-2026-10-19.log", "\n".join(log) + "\n")
    base_trail = (PROJECT / "logs" / "audit.log").read_text(encoding="utf-8")
    write(start / "logs" / "audit.log", base_trail + "\n".join(trail) + "\n")

    for duplicate, keep in DUPLICATES.items():
        admin.merge_owners(store, keep, duplicate)
    write(HERE / "solution" / "clinic.json", store.to_json())
    shutil.rmtree(work)
    print(f"start: 55 owners; solved: {len(store.owners)} owners, {len(store.pets)} pets")


if __name__ == "__main__":
    main()
