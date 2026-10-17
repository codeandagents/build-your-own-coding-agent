"""Devonport's vaccination reminder letters and texts (ClinicMaster 4). Runs on Mondays at Devonport.

The wording is the 2016 version; Harbourside's texts come from PetClinic Lite (petclinic/messages.py)."""
import datetime

from records import clients, connect, full_name, patients

LETTER = """Dear %(owner)s,

Our records show that %(pet)s is due for %(vaccine)s on %(date)s.

Please call Harbourside Vets Devonport on 09 555 0188 to book an appointment.

Yours sincerely,
Harbourside Vets"""

TEXT = "Hi %(owner)s, %(pet)s is due for %(vaccine)s on %(date)s. Book online or call Harbourside Vets on 09 555 0188."

INTERVAL_MONTHS = {"DHPP": 36, "KC": 12, "F3": 36, "FELV": 12, "RHD": 12}


def add_months(day, months):
    month = day.month - 1 + months
    year = day.year + month // 12
    month = month % 12 + 1
    for d in (day.day, 30, 29, 28):
        try:
            return datetime.date(year, month, d)
        except ValueError:
            continue


def due_list(db, today, window_days=21):
    until = today + datetime.timedelta(days=window_days)
    for client in clients(db, branch="DEV"):
        for patient in patients(db, client.client_no):
            for vaccine, last_given in last_doses(db, patient.patient_no):
                due = add_months(last_given, INTERVAL_MONTHS.get(vaccine, 12))
                if today <= due <= until:
                    yield client, patient, vaccine, due


def last_doses(db, patient_no):
    sql = "SELECT vaccine, MAX(given) FROM vaccinations WHERE patient_no = ? GROUP BY vaccine"
    for vaccine, given in db.execute(sql, (patient_no,)):
        yield vaccine, datetime.datetime.strptime(given, "%d/%m/%Y").date()


def texts(db, today):
    for client, patient, vaccine, due in due_list(db, today):
        number = (client.mobile or "").strip()
        if not number:
            continue
        yield number, TEXT % {"owner": full_name(client).split()[0], "pet": patient.name, "vaccine": vaccine,
                              "date": due.strftime("%d/%m/%Y")}


if __name__ == "__main__":
    for number, text in texts(connect(), datetime.date.today()):
        print(number, text)
