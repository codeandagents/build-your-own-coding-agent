from datetime import date, datetime
from pathlib import Path

from petclinic.cli import main
from petclinic.notifications import cancelled_text, overdue_text, reminder_email, reminder_text

FIXTURE = str(Path(__file__).parent / "fixtures" / "clinic.json")
TAIL = ("It's quick to book: reply \"BOOK\" & we'll call you, or call Harbourside Vets on 09 555 0100. "
        "Txt STOP to opt out.")  # the wording agreed on 9 October (T-2302), not the first proposal


def test_one_pet():
    assert reminder_text("Mei Lin", ["Mochi"], ["FeLV"], date(2026, 10, 25)) == (
        "Kia ora Mei! Mochi is due for FeLV on Sun 25 Oct. " + TAIL)


def test_two_pets():
    assert reminder_text("Aroha Ngata", ["Kiwi", "Pip"], ["F3", "DHPP"], date(2026, 10, 28)) == (
        "Kia ora Aroha! Kiwi and Pip are due for DHPP and F3 on Wed 28 Oct. " + TAIL)


def test_three_pets():
    assert reminder_text("Ben Carter", ["Kiwi", "Pip", "Rocket"], ["RHDV", "F3", "DHPP"], date(2026, 11, 2)) == (
        "Kia ora Ben! Kiwi, Pip and Rocket are due for DHPP, F3 and RHDV on Mon 2 Nov. " + TAIL)


def test_the_reminders_command_sends_the_new_text(capsys):
    main(["--data", FIXTURE, "reminders", "--on", "2026-10-21"])
    lines = capsys.readouterr().out.splitlines()
    assert "022-555-0142: Kia ora Mei! Mochi is due for FeLV on Sun 25 Oct. " + TAIL in lines


def test_the_other_texts_are_unchanged():
    assert overdue_text("Ben Carter", ["Rocket"], ["RHDV"], date(2026, 9, 1)) == (
        "Kia ora Ben! Rocket is overdue for RHDV (due on Tue 1 Sep). Book online or call Harbourside Vets on "
        "09 555 0100.")
    assert cancelled_text("Ben Carter", "Rocket", datetime(2026, 10, 22, 10, 30)) == (
        "Kia ora Ben. Rocket's appointment on Thu 22 Oct at 10:30am is cancelled. Book online or call Harbourside "
        "Vets on 09 555 0100.")


def test_the_email_is_unchanged():
    subject, body = reminder_email("Mei Lin", ["Mochi"], ["FeLV"], date(2026, 10, 25))
    assert body.splitlines()[2] == "Mochi is due for FeLV on Sun 25 Oct."
    assert "call us on 09 555 0100 between 8:30 and 17:30" in body
    assert body.splitlines()[-2:] == ["Ngā mihi,", "The team at Harbourside Vets"]
