"""Writes PetClinic Lite's data: clinic.json, data/*.json, data/exports/*.csv and logs/*.log in bench/project.

Deterministic (seeded): running it again writes the same files. The first three owners, their four pets, five
visits and seven vaccinations are the hand-written records the tests and tasks were built on; the rest is a year
of a small clinic's work around them. Run: .venv/Scripts/python -m bench.make_project_data"""
import csv
import io
import json
import random
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

PROJECT = Path(__file__).parent / "project"
sys.path.insert(0, str(PROJECT))

from petclinic.billing import consultation_invoice  # noqa: E402
from petclinic.billing.payments import surcharge  # noqa: E402
from petclinic.models import Owner, Pet, Vaccination, Visit  # noqa: E402
from petclinic.scheduling import slot_times  # noqa: E402
from petclinic.store import Store  # noqa: E402
from petclinic.vaccinations import SCHEDULES, add_months  # noqa: E402

SEED = 20261016
TODAY = date(2026, 10, 16)           # the data's "now": Friday 16 October 2026, end of day
FIRST_DAY = date(2025, 10, 1)        # visits on file from here (older ones are in the archive)
LAST_BOOKED = date(2026, 11, 13)     # bookings already made up to here

# Days the clinic was closed (it isn't in the app: that's task t15). Visits are never generated on them.
HOLIDAYS = {date(2025, 10, 27), date(2025, 12, 25), date(2025, 12, 26), date(2026, 1, 1), date(2026, 1, 2),
            date(2026, 1, 26), date(2026, 2, 6), date(2026, 4, 3), date(2026, 4, 6), date(2026, 4, 27),
            date(2026, 6, 1), date(2026, 7, 10), date(2026, 10, 26)}

FIRST = ["Hemi", "Olivia", "Noah", "Ava", "Wiremu", "Isla", "Jack", "Mia", "Leo", "Charlotte", "Mason", "Amelia",
         "Nikau", "Ruby", "Oliver", "Harper", "Kauri", "Zoe", "Lucas", "Ella", "Priya", "Sione", "Lupe", "Te Ao",
         "Ethan", "Lily", "Rangi", "Sophie", "Daniel", "Grace", "Manaia", "Chloe", "Hugo", "Anahera", "Sam", "Jade",
         "Tom", "Keri", "Raj", "Yuki", "Lena", "Pita", "Holly", "Marco", "Talia"]
LAST = ["Smith", "Wilson", "Taylor", "Chen", "Wang", "Williams", "Jones", "Parata", "Tuilagi", "Fale", "Nguyen",
        "Thompson", "Martin", "Clarke", "Young", "Harris", "King", "Wright", "Green", "Baker", "Robinson", "Te Whata",
        "Moana", "Kaur", "Sharma", "Ito", "Fischer", "Hohaia", "Ward", "Ferris", "Pomare", "Dunn", "Bishop", "Aumua"]
# names used by the tasks' own data: never generated
RESERVED = {"Tama Wiremu", "Grace Kim", "Liam O'Connor", "Sofia Rossi", "Ana Lopez", "Hana Lee", "Finn Scott",
            "Arjun Singh", "Maia Hall", "Liam Brown", "Ann Lee", "Big Clinic"}

PET_NAMES = ["Bella", "Max", "Luna", "Coco", "Milo", "Charlie", "Daisy", "Oscar", "Ruby", "Teddy", "Poppy",
             "Bailey", "Molly", "Tui", "Pepper", "Ziggy", "Nala", "Loki", "Willow", "Rosie", "Jasper", "Maple",
             "Hoki", "Sushi", "Olive", "Archie", "Frankie", "Honey", "Biscuit", "Winston", "Pickle", "Kowhai", "Bodhi",
             "Peaches", "Murphy", "Ivy", "Rata", "Pippa", "Basil", "Marlo", "Kumara", "Scout", "Ted", "Fig", "Juno"]
BREEDS = {"dog": ["Labrador", "Huntaway", "Border collie", "Cavoodle", "Staffy cross", "Jack Russell", "Spoodle",
                  "German shepherd", "Golden retriever", "Heading dog", "Schnauzer", "Beagle"],
          "cat": ["Domestic shorthair", "Domestic longhair", "Burmese", "Ragdoll", "Siamese", "British shorthair",
                  "Tonkinese"],
          "rabbit": ["Netherland dwarf", "Lop", "Lionhead"], "guinea pig": ["Abyssinian", "American"],
          "bird": ["Budgie", "Cockatiel"]}
SPECIES = ["dog"] * 8 + ["cat"] * 7 + ["rabbit"] * 2 + ["guinea pig", "bird"]
REASONS = {"any": ["annual check-up", "vaccination", "limping", "ear infection", "skin rash", "dental check",
                   "follow-up", "weight check", "vomiting", "eye discharge", "nail trim", "lump check",
                   "post-op check", "microchipping", "allergies", "not eating", "wound check", "behaviour consult"],
           "young": ["puppy check", "kitten check", "desexing consult"],
           "old": ["senior check", "arthritis review", "blood test results"]}

ORIGINAL_OWNERS = [Owner(1, "Aroha Ngata", "021 555 0101", "aroha.ngata@example.com"),
                   Owner(2, "Ben Carter", "027 555 0199"),
                   Owner(3, "Mei Lin", "022-555-0142", "mei.lin@example.net")]
ORIGINAL_PETS = [Pet(1, "Kiwi", "dog", date(2019, 4, 12), 1, "Huntaway", "985141000123456"),
                 Pet(2, "Pip", "cat", date(2022, 11, 3), 1, "Domestic shorthair"),
                 Pet(3, "Rocket", "rabbit", date(2024, 2, 29), 2, "Netherland dwarf"),
                 Pet(4, "Mochi", "cat", date(2021, 7, 8), 3, "Burmese", "985141000654321")]
ORIGINAL_VISITS = [(1, datetime(2026, 10, 12, 9, 0), "annual check-up", 1),
                   (3, datetime(2026, 10, 13, 11, 30), "teeth", 2),
                   (4, datetime(2026, 10, 14, 16, 0), "vaccination", 3),
                   (2, datetime(2026, 10, 15, 10, 0), "limping", 1),
                   (1, datetime(2026, 10, 16, 14, 30), "follow-up", 1)]
ORIGINAL_VACCINATIONS = [(1, "DHPP", "2023-10-28"), (1, "Kennel cough", "2025-10-30"), (2, "F3", "2023-11-02"),
                         (2, "FeLV", "2026-03-10"), (3, "RHDV", "2025-11-20"), (4, "F3", "2026-10-14"),
                         (4, "FeLV", "2025-10-25")]

VETS = [{"id": 1, "name": "Dr Priya Patel"}, {"id": 2, "name": "Dr Sam Walker"}, {"id": 3, "name": "Dr Hine Tane"}]
LEAVE = [{"vet_id": 2, "first_day": "2026-04-07", "last_day": "2026-04-17", "note": "school holidays"},
         {"vet_id": 3, "first_day": "2026-07-06", "last_day": "2026-07-17", "note": "school holidays"},
         {"vet_id": 1, "first_day": "2026-11-02", "last_day": "2026-11-06", "note": "conference, Wellington"},
         {"vet_id": "2", "first_day": "2026-12-21", "last_day": "2027-01-08", "note": "summer leave"},  # as text
         {"vet_id": 3, "first_day": "2027-01-11", "last_day": "2027-01-22", "note": "summer leave"}]
FORMER_VETS = [{"id": 4, "name": "Dr Alan Reid", "active": False}, {"id": 5, "name": "Dr Grace Moana", "active": False}]
EMPLOYED = {1: (2019, 2026), 2: (2021, 2026), 3: (2023, 2026), 4: (2019, 2023), 5: (2024, 2025)}  # vet id: years


def leave_history(rng: random.Random) -> list[dict]:
    """The spreadsheet's older rows, all before FIRST_DAY: summer and school holidays, conferences, training days and
    sick days since 2019 (so the visits on file never clash with them)."""
    rows = []

    def add(vet_id, first, days, note):
        last = first + timedelta(days=days - 1)
        if last < FIRST_DAY:
            rows.append({"vet_id": vet_id, "first_day": first.isoformat(), "last_day": last.isoformat(), "note": note})

    for vet_id, (first_year, last_year) in EMPLOYED.items():
        for year in range(first_year, last_year + 1):
            add(vet_id, date(year, 1, 5) + timedelta(days=rng.randrange(0, 10)), rng.choice([5, 10, 12]), "summer leave")
            for month in (4, 7, 10):
                if rng.random() < 0.45:
                    add(vet_id, date(year, month, 6) + timedelta(days=7 * rng.randrange(0, 2)), 5, "school holidays")
            if rng.random() < 0.6:
                add(vet_id, date(year, rng.choice([3, 5, 8, 9]), rng.randrange(1, 25)), rng.choice([2, 3]),
                    rng.choice(["conference, Wellington", "conference, Christchurch", "VetEd course", "NZVA conference"]))
            for _ in range(rng.randrange(1, 3)):
                add(vet_id, date(year, rng.randrange(2, 12), rng.randrange(1, 28)), 1, "training day")
            for _ in range(rng.randrange(3, 7)):
                add(vet_id, date(year, rng.randrange(1, 13), rng.randrange(1, 28)), rng.choice([1, 1, 2]), "sick")
    return rows


STOCK = [
    ("VAX-DHPP", "DHPP vaccine", 10, "pharmacy", [(8, "2027-03-31"), (4, "2026-09-30")], {}),
    ("VAX-F3", "F3 vaccine", 10, "pharmacy", [(15, "2027-06-30")], {}),
    ("VAX-FELV", "FeLV vaccine", 6, "pharmacy", [(9, "2027-02-28")], {}),
    ("VAX-RHDV", "RHDV vaccine", 4, "pharmacy", [(2, "2026-12-31"), (6, "2026-10-01")], {"on_order": 10}),
    ("VAX-KC", "Kennel cough vaccine", 8, "pharmacy", [(12, "2027-01-31")], {}),
    ("MED-MELOX", "Meloxicam oral 10 ml", 6, "pharmacy", [(3, "2027-01-31"), (2, "2026-10-10")], {}),
    ("MED-AMOX", "Amoxicillin 250 mg tablets", 100, "pharmacy", [(120, "2026-12-31")], {"pack_size": 100}),
    ("MED-CLAV", "Amoxyclav 500 mg tablets", 60, "pharmacy", [(40, "2027-05-31"), (30, "2026-11-30")], {}),
    ("MED-GABA", "Gabapentin 100 mg capsules", 50, "pharmacy", [(25, "2027-08-31")], {"on_order": 100}),
    ("MED-PRED", "Prednisolone 5 mg tablets", 100, "pharmacy", [(210, "2027-04-30")], {}),
    ("MED-OTIC", "Ear drops 15 ml", 10, "pharmacy", [(4, "2026-12-15"), (6, "2026-10-15")], {"pack_size": 4}),
    ("MED-EYE", "Eye ointment 5 g", 8, "pharmacy", [(9, "2027-02-28")], {}),
    ("MED-FLEA-S", "Flea treatment, small dog", 20, "front desk", [(14, "2027-09-30")], {}),
    ("MED-FLEA-L", "Flea treatment, large dog", 20, "front desk", [(31, "2027-09-30")], {}),
    ("MED-FLEA-C", "Flea treatment, cat", 20, "front desk", [(18, "2027-07-31"), (12, "2027-05-31", True)], {"pack_size": 6}),
    ("MED-WORM", "Allwormer tablets", 40, "front desk", [(55, "2028-01-31")], {}),
    ("MED-ACEP", "Acepromazine 10 mg tablets", 30, "pharmacy", [(12, "2026-11-30")], {"discontinued": True}),
    ("SUP-SYR3", "Syringes 3 ml", 200, "surgery", [(450, None)], {}),
    ("SUP-SYR10", "Syringes 10 ml", 100, "surgery", [(80, None)], {"pack_size": 50}),
    ("SUP-NEED", "Needles 23 G", 300, "surgery", [(700, None)], {}),
    ("SUP-BAND", "Bandage 7.5 cm", 20, "surgery", [(20, None)], {}),
    ("SUP-GAUZE", "Gauze swabs", 200, "surgery", [(150, None)], {"pack_size": 100}),
    ("SUP-GLOVE-M", "Examination gloves, medium (box)", 10, "surgery", [(6, None)], {}),
    ("SUP-SUTURE", "Sutures 3-0", 24, "surgery", [(30, "2028-06-30")], {}),
    ("SUP-CONE-S", "Recovery cone, small", 5, "front desk", [(7, None)], {}),
    ("SUP-CONE-L", "Recovery cone, large", 5, "front desk", [(2, None)], {}),
    ("SUP-CHIP", "Microchips", 20, "pharmacy", [(26, "2029-03-31")], {}),
    ("FOOD-RENAL", "Renal diet, cat, 1.5 kg", 6, "front desk", [(3, "2027-03-31"), (2, "2026-10-31")], {}),
    ("FOOD-GI", "Gastro diet, dog, 2 kg", 6, "front desk", [(8, "2027-05-31")], {}),
    ("FOOD-OLD", "Senior diet, dog, 3 kg", 4, "front desk", [(1, "2026-12-31")], {"discontinued": True}),
]

FEES = [
    ("CONSULT", "Standard consultation", 8500, "consult"),
    ("FOLLOWUP", "Follow-up consultation", 4245, "consult"),
    ("AFTERHOURS", "After-hours consultation", 16500, "consult"),
    ("VAX", "Vaccination (per vaccine)", 3850, "procedure"),
    ("CHIP", "Microchip and registration", 6900, "procedure"),
    ("NAILS", "Nail trim", 2500, "procedure"),
    ("DENTAL", "Dental procedure", 12000, "procedure"),
    ("XRAY", "X-ray (per view)", 14500, "procedure"),
    ("BLOODS", "Blood panel", 18900, "procedure"),
    ("DESEX-C", "Desexing, cat", 26500, "procedure"),
    ("DESEX-D", "Desexing, dog (up to 20 kg)", 48000, "procedure"),
    ("MED-MELOX", "Meloxicam oral 10 ml", 2380, "medicine"),
    ("MED-AMOX", "Amoxicillin 250 mg tablets", 120, "medicine"),
    ("MED-CLAV", "Amoxyclav 500 mg tablets", 260, "medicine"),
    ("MED-GABA", "Gabapentin 100 mg capsules", 140, "medicine"),
    ("MED-PRED", "Prednisolone 5 mg tablets", 60, "medicine"),
    ("MED-OTIC", "Ear drops 15 ml", 3120, "medicine"),
    ("MED-EYE", "Eye ointment 5 g", 2240, "medicine"),
    ("MED-CHLOR", "Chloramphenicol eye drops 10 ml", 2630, "medicine"),
    ("MED-SILV", "Silver sulfadiazine cream 50 g", 1890, "medicine"),
    ("MED-FLEA-S", "Flea treatment, small dog", 2860, "medicine"),
    ("MED-FLEA-L", "Flea treatment, large dog", 3480, "medicine"),
    ("MED-FLEA-C", "Flea treatment, cat", 2640, "medicine"),
    ("MED-WORM", "Allwormer tablets", 680, "medicine"),
    ("SUP-CONE-S", "Recovery cone, small", 1800, "medicine"),
    ("SUP-CONE-L", "Recovery cone, large", 2400, "medicine"),
]

# Weekly exports from the Devonport branch, imported every Monday at 06:00. Rows for clients already on file come
# with their name as the branch typed it: the importer recognises them. Index = position in the generated owners.
EXPORT_MONDAYS = [date(2026, 9, 7), date(2026, 9, 14), date(2026, 9, 21), date(2026, 9, 28), date(2026, 10, 5),
                  date(2026, 10, 12)]
NEWCOMERS = 4 * len(EXPORT_MONDAYS)
SAME_NAME = [(8, "sam.wilson@example.com"), (19, "")]  # both "Sam Wilson", same household and number
ARCHIVED = 40  # visits 1-40 (2017-2018) are in data/archive.json


def mobile(rng: random.Random, used: set) -> str:
    while True:
        prefix = rng.choice(["021", "022", "027"])
        number = f"{prefix} 555 0{rng.randrange(100, 1000)}"
        if rng.random() < 0.3:
            number = number.replace(" ", "-")
        if number.replace("-", " ") not in used:
            used.add(number.replace("-", " "))
            return number


def landline(rng: random.Random, used: set) -> str:
    while True:
        number = f"09 555 0{rng.randrange(100, 1000)}"
        if number not in used:
            used.add(number)
            return number


def build() -> tuple[Store, dict]:
    rng = random.Random(SEED)
    store = Store()
    used_numbers = {o.telephone.replace("-", " ") for o in ORIGINAL_OWNERS} | {"09 555 0100"}
    for o in ORIGINAL_OWNERS:
        store.owners[o.id] = o
    names = set(o.name for o in ORIGINAL_OWNERS) | RESERVED
    while len(store.owners) < 48:
        name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        if name in names:
            continue
        names.add(name)
        number = mobile(rng, used_numbers) if rng.random() < 0.78 else landline(rng, used_numbers)
        email = f"{name.lower().replace(' ', '.')}@example.{rng.choice(['com', 'net', 'org'])}" \
            if rng.random() < 0.6 else ""
        owner = Owner(len(store.owners) + 1, name, number, email)
        if rng.random() < 0.17:
            owner.insurer = "PetCover"
        store.owners[owner.id] = owner
    # two different clients with the same name (not duplicates: different people, numbers and pets)
    for owner_id, email in SAME_NAME:
        store.owners[owner_id].name, store.owners[owner_id].email = "Sam Wilson", email
    store.owners[SAME_NAME[1][0]].telephone = store.owners[SAME_NAME[0][0]].telephone  # father and son: one number

    for p in ORIGINAL_PETS:
        store.pets[p.id] = Pet(**p.__dict__)
    for owner_id in range(4, 49):
        for _ in range(rng.choice([1, 1, 1, 2, 2, 3])):
            species = rng.choice(SPECIES)
            taken = {p.name for p in store.pets.values() if p.owner_id == owner_id}
            name = rng.choice([n for n in PET_NAMES if n not in taken])
            if species in ("guinea pig", "bird", "rabbit"):
                born = TODAY - timedelta(days=rng.randrange(150, 2600))
            else:
                born = TODAY - timedelta(days=rng.randrange(60, 6200))
            chip = f"985141{rng.randrange(10**8, 10**9)}" if species in ("dog", "cat") and rng.random() < 0.8 else ""
            pet = Pet(len(store.pets) + 1, name, species, born, owner_id, rng.choice(BREEDS[species]), chip)
            store.pets[pet.id] = pet

    for pet_id, vaccine, given in ORIGINAL_VACCINATIONS:
        store.vaccinations.append(Vaccination(pet_id, vaccine, date.fromisoformat(given)))
    for pet in list(store.pets.values())[4:]:
        lapsed = rng.random() < 0.12
        for vaccine, months in SCHEDULES.get(pet.species, {}).items():
            given = pet.birth_date + timedelta(weeks=8, days=rng.randrange(0, 14))
            stop = TODAY - timedelta(days=rng.randrange(200, 600)) if lapsed else TODAY
            while given <= stop:
                store.vaccinations.append(Vaccination(pet.id, vaccine, given))
                given = add_months(given, months) + timedelta(days=rng.randrange(-5, 20))

    # visits: a year of weekdays, ids in date order after the archived ones (1-40)
    leave = [(int(x["vet_id"]), date.fromisoformat(x["first_day"]), date.fromisoformat(x["last_day"])) for x in LEAVE]
    originals = {start: (pet_id, reason, vet) for pet_id, start, reason, vet in ORIGINAL_VISITS}
    joined = joining_dates(store)
    planned = []
    day = FIRST_DAY
    pets = list(store.pets.values())
    while day <= LAST_BOOKED:
        if day.weekday() < 5 and day not in HOLIDAYS:
            working = [v["id"] for v in VETS if not any(vid == v["id"] and a <= day <= b for vid, a, b in leave)]
            busy = rng.randrange(2, 6) if day <= TODAY else rng.randrange(1, 5) if day <= TODAY + timedelta(14) \
                else rng.randrange(0, 3)
            fixed = [s for s in originals if s.date() == day]
            free = [t for t in slot_times() if datetime.combine(day, t) not in fixed]
            for t in sorted(rng.sample(free, max(0, busy - len(fixed)))):
                start = datetime.combine(day, t)
                pet = rng.choice([p for p in pets if p.birth_date < day and p.id > 4
                                  and joined.get(p.owner_id, FIRST_DAY) <= day])
                age = (day - pet.birth_date).days / 365.25
                pool = REASONS["any"] + (REASONS["young"] if age < 1 else REASONS["old"] if age >= 9 else [])
                vet = rng.choice(working) if rng.random() < 0.7 else None
                planned.append((start, pet.id, rng.choice(pool), vet))
            for start in fixed:
                pet_id, reason, vet = originals[start]
                planned.append((start, pet_id, reason, vet))
        day += timedelta(days=1)
    for number, (start, pet_id, reason, vet) in enumerate(sorted(planned), start=ARCHIVED + 1):
        store.visits[number] = Visit(number, pet_id, start, reason, vet)

    # payments for visits up to TODAY
    for visit in sorted(store.visits.values(), key=lambda v: v.start):
        if visit.start.date() > TODAY or visit.pet_id <= 4 and visit.start.date() >= date(2026, 10, 12):
            continue
        roll = rng.random()
        if roll < 0.05:
            continue  # not paid yet
        method = rng.choices(["eftpos", "credit", "cash"], [60, 25, 15])[0]
        paid = visit.start + timedelta(minutes=rng.randrange(35, 56))
        if roll > 0.9:
            later = visit.start.date() + timedelta(days=rng.randrange(1, 21))
            paid = datetime.combine(later, time(rng.randrange(9, 17), rng.randrange(0, 60)))
            if later > TODAY:
                continue
        total = consultation_invoice(store, visit.id).total()
        store.add_payment(visit.id, total + surcharge(total, method), method, paid)

    rng_archive = random.Random(SEED + 1)
    old_pets = [p.id for p in store.pets.values() if p.birth_date < date(2016, 6, 1)]
    starts = set()
    while len(starts) < ARCHIVED:
        start = datetime(2017, 3, 1, 9, 0) + timedelta(days=rng_archive.randrange(0, 650),
                                                       minutes=30 * rng_archive.randrange(0, 16))
        if start.weekday() < 5:
            starts.add(start)
    archive = [{"id": i, "pet_id": rng_archive.choice(old_pets), "start": start.isoformat(timespec="minutes"),
                "reason": rng_archive.choice(REASONS["any"]), "vet_id": None}
               for i, start in enumerate(sorted(starts), start=1)]
    return store, {"archive": archive}


def joining_dates(store: Store) -> dict[int, date]:
    """Owners who came in through a weekly export: their first day as the clinic's clients."""
    newcomers = [o.id for o in store.owners.values() if o.id > 3][-NEWCOMERS:]
    return {owner_id: EXPORT_MONDAYS[i // 4] for i, owner_id in enumerate(newcomers)}


def exports(store: Store) -> tuple[dict[date, str], dict[date, str], list[str]]:
    """The weekly CSVs, their import logs and the audit trail of those imports. Each week brings four new
    clients (the owners joining_dates names) and two clients already on file, typed the branch's way."""
    rng = random.Random(SEED + 2)
    files, logs, trail = {}, {}, []
    joined = joining_dates(store)
    regulars = [o for o in store.owners.values() if o.id > 3 and o.id not in joined and o.name != "Sam Wilson"]
    for monday in EXPORT_MONDAYS:
        rows = []
        for owner_id in [o for o, day in joined.items() if day == monday]:
            owner = store.owners[owner_id]
            for pet in store.pets_of(owner_id):
                rows.append((owner, pet, owner.name, "new"))
        for owner in rng.sample(regulars, 2):
            pet = store.pets_of(owner.id)[0]
            typed = rng.choice([owner.name.lower(), owner.name.upper(), " " + owner.name.replace(" ", "  "),
                                owner.name + " "])
            rows.append((owner, pet, typed, "seen at Devonport"))
        out = io.StringIO()
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(["owner_name", "owner_phone", "pet_name", "species", "birth_date", "notes"])
        clock = datetime.combine(monday, time(6, 0, 1))
        lines, seen, owners_added, pets_added = [], set(), 0, 0
        for number, (owner, pet, typed, note) in enumerate(rows, start=2):
            writer.writerow([typed, owner.telephone, pet.name, pet.species, pet.birth_date.isoformat(),
                             "" if note == "new" else note])
            clock += timedelta(milliseconds=rng.randrange(3, 40))
            stamp = clock.strftime("%Y-%m-%d %H:%M:%S") + f",{clock.microsecond // 1000:03d}"
            if note == "new":
                if owner.id not in seen:
                    seen.add(owner.id)
                    owners_added += 1
                    trail.append(f"{clock:%Y-%m-%d %H:%M:%S}  {'import':11}  owner {owner.id} added: "
                                 f"{owner.name!r} ({owner.telephone})")
                pets_added += 1
                trail.append(f"{clock:%Y-%m-%d %H:%M:%S}  {'import':11}  pet {pet.id} added: {pet.name} "
                             f"({pet.species}) for owner {owner.id}")
                lines.append(f"{stamp} INFO petclinic.importer: row {number}: {pet.name} ({pet.species}) for "
                             f"{owner.name}")
            else:
                lines.append(f"{stamp} INFO petclinic.importer: row {number}: {pet.name} already on file")
        clock += timedelta(milliseconds=5)
        stamp = clock.strftime("%Y-%m-%d %H:%M:%S") + f",{clock.microsecond // 1000:03d}"
        lines.append(f"{stamp} INFO petclinic.importer: import finished: {owners_added} owners and {pets_added} pets "
                     f"added, 0 rows skipped")
        files[monday] = out.getvalue()
        logs[monday] = "\n".join(lines) + "\n"
    return files, logs, trail


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")


def main() -> None:
    store, extra = build()
    write(PROJECT / "clinic.json", store.to_json())
    leave = sorted(leave_history(random.Random(SEED + 3)) + LEAVE, key=lambda x: (x["first_day"], str(x["vet_id"])))
    write(PROJECT / "data" / "staff.json", json.dumps({"vets": VETS + FORMER_VETS, "leave": leave}, indent=2) + "\n")
    items = []
    for code, name, level, location, batches, more in STOCK:
        item = {"code": code, "name": name, "reorder_level": level, "location": location,
                "batches": [{"quantity": b[0], **({"expiry": b[1]} if b[1] else {}),
                             **({"recalled": True} if len(b) > 2 else {})} for b in batches], **more}
        items.append(item)
    write(PROJECT / "data" / "stock.json", json.dumps({"items": items}, indent=2) + "\n")
    write(PROJECT / "data" / "fees.json", json.dumps(
        {"fees": [{"code": c, "description": d, "cents": cents, "kind": k} for c, d, cents, k in FEES]}, indent=2) + "\n")
    write(PROJECT / "data" / "archive.json", json.dumps(extra["archive"], indent=1) + "\n")
    files, logs, trail = exports(store)
    for monday, text in files.items():
        write(PROJECT / "data" / "exports" / f"clinicmaster-{monday}.csv", text)
        write(PROJECT / "logs" / f"import-{monday}.log", logs[monday])
    trail += [f"2026-03-02 17:41:09  {'archive':11}  {ARCHIVED} visits before 2019-03-01 archived"]
    rng = random.Random(SEED + 4)
    for owner in [o for o in store.owners.values() if o.id <= 24]:  # the desk registered the clients before the imports
        when = datetime(2023, 6, 12, 9) + timedelta(days=(owner.id - 1) * 40 + rng.randrange(0, 30),
                                                    minutes=rng.randrange(0, 480))
        trail.append(f"{when:%Y-%m-%d %H:%M:%S}  {'front desk':11}  owner {owner.id} added: {owner.name!r} "
                     f"({owner.telephone})")
        for pet in store.pets_of(owner.id):
            when += timedelta(minutes=rng.randrange(1, 4))
            trail.append(f"{when:%Y-%m-%d %H:%M:%S}  {'front desk':11}  pet {pet.id} added: {pet.name} ({pet.species}) "
                         f"for owner {owner.id}")
    write(PROJECT / "logs" / "audit.log", "\n".join(sorted(trail)) + "\n")
    print(f"{len(store.owners)} owners, {len(store.pets)} pets, {len(store.visits)} visits, "
          f"{len(store.vaccinations)} vaccinations, {len(store.payments)} payments")


if __name__ == "__main__":
    main()
