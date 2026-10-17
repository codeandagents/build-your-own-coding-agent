"""Weekly export of Devonport's clients for PetClinic Lite (runs Sunday 23:00 at Devonport).

Writes clinicmaster-YYYY-MM-DD.csv with the columns PetClinic Lite's importer reads:
owner_name, owner_phone, pet_name, species, birth_date, notes. One row per patient seen that week.

Usage: python export_clients.py cm4.db OUTDIR [--since YYYY-MM-DD]"""
import csv
import datetime
import os
import sys

from records import best_number, clients, connect, full_name, patients, seen_since

COLUMNS = ["owner_name", "owner_phone", "pet_name", "species", "birth_date", "notes"]


def birth_date_text(patient):
    """The birth date as ClinicMaster has it. It isn't reformatted: the export is a copy of the record.

    - Typed at Devonport since the 2019 PC upgrade: the PCs' regional format, day first ("03/11/2019").
    - Everything else: ISO ("2019-11-03")."""
    return (patient.dob_text or "").strip()


def rows_for(db, since):
    for client in clients(db, branch="DEV"):
        if not seen_since(db, client.client_no, since):
            continue
        for patient in patients(db, client.client_no):
            if patient.deceased:
                continue
            yield [full_name(client), best_number(client), patient.name, patient.species,
                   birth_date_text(patient), ""]


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    db = connect(argv[1])
    today = datetime.date.today()
    since = (today - datetime.timedelta(days=7)).isoformat()
    if "--since" in argv:
        since = argv[argv.index("--since") + 1]
    monday = today + datetime.timedelta(days=(7 - today.weekday()) % 7)
    path = os.path.join(argv[2], "clinicmaster-%s.csv" % monday.isoformat())
    count = 0
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        for row in rows_for(db, since):
            writer.writerow(row)
            count += 1
    print("%d rows written to %s" % (count, path))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
