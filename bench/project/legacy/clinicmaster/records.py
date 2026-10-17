"""ClinicMaster's client and patient records, as its database export gives them.

ClinicMaster 4 kept every date as text, the way it was typed. Records migrated from ClinicMaster 3 (before 2009)
were converted by the vendor's tool, which wrote full timestamps."""
import sqlite3
from collections import namedtuple

Client = namedtuple("Client", "client_no surname given_names telephone mobile email branch")
Patient = namedtuple("Patient", "patient_no client_no name species breed dob_text source deceased")

SPECIES_CODES = {"K9": "dog", "FEL": "cat", "LAG": "rabbit", "CAV": "guinea pig", "AVI": "bird", "REP": "reptile"}
# Patients migrated from ClinicMaster 3 (client numbers from 50000) kept CM3's species text instead of a code:
# "canine", "feline". Anything not in SPECIES_CODES is exported as it is.


def connect(path="cm4.db"):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    return db


def clients(db, branch=None):
    sql = "SELECT client_no, surname, given_names, telephone, mobile, email, branch FROM clients"
    args = ()
    if branch:
        sql += " WHERE branch = ?"
        args = (branch,)
    for row in db.execute(sql, args):
        yield Client(*row)


def patients(db, client_no):
    sql = ("SELECT patient_no, client_no, name, species_code, breed, dob, source, deceased "
           "FROM patients WHERE client_no = ? ORDER BY patient_no")
    for row in db.execute(sql, (client_no,)):
        yield Patient(row[0], row[1], row[2], SPECIES_CODES.get(row[3], row[3]), row[4], row[5], row[6], row[7])


def full_name(client):
    """ClinicMaster stored given names and surname apart; the desk often typed both into one of them."""
    given = (client.given_names or "").strip()
    surname = (client.surname or "").strip()
    if not given:
        return surname
    if not surname:
        return given
    return given + " " + surname


def best_number(client):
    """The number to give PetClinic Lite: the mobile if there is one, else the landline."""
    return (client.mobile or client.telephone or "").strip()


def same_client(a, b):
    """ClinicMaster's duplicate check: names compared after strip() and lower()."""
    return full_name(a).strip().lower() == full_name(b).strip().lower()


def seen_since(db, client_no, since_text):
    """True if the client had a consult on or after `since_text` (YYYY-MM-DD)."""
    sql = "SELECT COUNT(*) FROM consults WHERE client_no = ? AND consult_date >= ?"
    return db.execute(sql, (client_no, since_text)).fetchone()[0] > 0
