"""Writes start/logs/import-2026-10-15.log: what `python -m petclinic import` logged for a big catch-up export from
ClinicMaster (Devonport's whole client list, 5,980 rows).

Two kinds of good rows were skipped, among hundreds of rows skipped for good reasons:
- 37 birth dates written day first (DD/MM/YYYY), as Devonport's PCs type them;
- 14 species written the ClinicMaster 3 way, "canine" and "feline" (records migrated in 2009, near the end).
Skipped for good reasons: 250 numbers that aren't phone numbers, 30 species the clinic doesn't treat (reptile,
ferret, horse, goat) and 7 dates that aren't dates. So `grep WARNING` is ~27,000 characters, more than one tool
output shows. Deterministic: running it again writes the same file. Run: python make_log.py"""
import random
from datetime import date, datetime, timedelta
from pathlib import Path

ROWS = 5_980
DAY_FIRST = 37
OLD_SPECIES = ["canine"] * 8 + ["feline"] * 6
UNTREATED = ["reptile"] * 12 + ["ferret"] * 9 + ["horse"] * 5 + ["goat"] * 4
NOT_DATES = ["31/02/2019", "30/02/2020", "unknown", "unknown", "unknown", "", ""]
BAD_PHONES = 250
MIGRATED_FROM_ROW = 5_400  # the old species names come in the export's last ~600 rows
OUT =Path(__file__).parent / "start" / "logs" / "import-2026-10-15.log"

FIRST = ["Aroha", "Ben", "Mei", "Tama", "Grace", "Liam", "Sofia", "Ana", "Hemi", "Olivia", "Noah", "Ava", "Wiremu",
         "Isla", "Jack", "Mia", "Leo", "Charlotte", "Mason", "Amelia", "Nikau", "Ruby", "Oliver", "Harper", "Kauri",
         "Zoe", "Lucas", "Ella", "Arjun", "Priya", "Hana", "Sione", "Lupe", "Finn", "Maia", "Te Ao", "Ethan", "Lily"]
LAST = ["Ngata", "Carter", "Lin", "Wiremu", "Kim", "Brown", "Rossi", "Lopez", "Smith", "Wilson", "Taylor", "Patel",
        "Singh", "Chen", "Wang", "Williams", "Jones", "Walker", "Tane", "Parata", "Tuilagi", "Fale", "Nguyen", "Lee",
        "Thompson", "Martin", "Clarke", "Young", "Harris", "King", "Wright", "Scott", "Green", "Baker", "Hall"]
PETS = ["Kiwi", "Pip", "Rocket", "Mochi", "Bella", "Max", "Luna", "Coco", "Milo", "Charlie", "Daisy", "Oscar",
        "Ruby", "Teddy", "Poppy", "Bailey", "Molly", "Tui", "Pepper", "Ziggy", "Biscuit", "Nala", "Loki", "Sol",
        "Willow", "Bear", "Rosie", "Jasper", "Maple", "Fern", "Kowhai", "Potiki", "Hoki", "Sushi", "Taco", "Olive"]
SPECIES = ["dog"] * 5 + ["cat"] * 4 + ["rabbit"]


def main() -> None:
    rng = random.Random(20261015)
    rows = list(range(2, ROWS + 2))
    # ClinicMaster numbered the clients it migrated from version 3 from 50000 up, and the export is in client
    # number order: the old species names are all in the last rows
    migrated = rng.sample(rows[MIGRATED_FROM_ROW:], len(OLD_SPECIES))
    special = rng.sample([r for r in rows if r not in migrated],
                         DAY_FIRST + len(UNTREATED) + len(NOT_DATES) + BAD_PHONES)
    kinds = {row: ("old_species", value) for row, value in zip(migrated, OLD_SPECIES)}
    cursor = 0
    for kind, values in (("day_first", [None] * DAY_FIRST), ("untreated", UNTREATED), ("not_date", NOT_DATES),
                         ("bad_phone", [None] * BAD_PHONES)):
        for value in values:
            kinds[special[cursor]] = (kind, value)
            cursor += 1
    first_day_first = min(row for row, (kind, _) in kinds.items() if kind == "day_first")
    clock = datetime(2026, 10, 15, 18, 2, 11, 482_000)
    owners: dict[str, set] = {}
    added_owners = added_pets = skipped = 0
    lines = []

    def log(level: str, message: str) -> None:
        nonlocal clock
        clock += timedelta(microseconds=rng.randrange(300, 2_500))
        stamp = clock.strftime("%Y-%m-%d %H:%M:%S") + f",{clock.microsecond // 1000:03d}"
        lines.append(f"{stamp} {level} petclinic.importer: {message}")

    for row in rows:
        kind, value = kinds.get(row, (None, None))
        if owners and rng.random() < 0.35 and kind != "bad_phone":
            owner = rng.choice(sorted(owners))
        else:  # a new owner (only new owners' numbers are checked)
            owner = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
            while kind == "bad_phone" and owner in owners:
                owner = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        pet, species = rng.choice(PETS), rng.choice(SPECIES)
        born = date(2008, 1, 1) + timedelta(days=rng.randrange(0, 6_500))
        if kind == "day_first":
            text = "03/11/2019" if row == first_day_first else born.strftime("%d/%m/%Y")
            log("WARNING", f"row {row}: birth_date {text!r} is not a date (skipped)")
            skipped += 1
        elif kind == "not_date":
            log("WARNING", f"row {row}: birth_date {value!r} is not a date (skipped)")
            skipped += 1
        elif kind in ("old_species", "untreated"):
            log("WARNING", f"row {row}: species {value!r}: the clinic doesn't treat it (skipped)")
            skipped += 1
        elif kind == "bad_phone":
            log("WARNING", f"row {row}: telephone: digits, spaces and dashes only (skipped)")
            skipped += 1
        else:
            if owner not in owners:
                owners[owner] = set()
                added_owners += 1
            if pet in owners[owner]:
                log("INFO", f"row {row}: {pet} already on file")
            else:
                owners[owner].add(pet)
                added_pets += 1
                log("INFO", f"row {row}: {pet} ({species}) for {owner}")
    log("INFO", f"import finished: {added_owners} owners and {added_pets} pets added, {skipped} rows skipped")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="")
    warnings = "".join(line + "\n" for line in lines if " WARNING " in line)
    print(f"{OUT.name}: {len(lines)} lines, {skipped} rows skipped, WARNING lines {len(warnings):,} characters")


if __name__ == "__main__":
    main()
