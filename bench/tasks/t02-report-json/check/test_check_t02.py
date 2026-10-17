import json
from pathlib import Path

from petclinic.cli import main

FIXTURE = str(Path(__file__).parent / "fixtures" / "clinic.json")
PIP = {"date": "2026-10-15", "time": "10:00", "pet": "Pip", "owner": "Aroha Ngata", "reason": "limping"}
KIWI = {"date": "2026-10-16", "time": "14:30", "pet": "Kiwi", "owner": "Aroha Ngata", "reason": "follow-up"}
ROCKET = {"date": "2026-10-22", "time": "10:30", "pet": "Rocket", "owner": "Ben Carter", "reason": "nail trim"}


def report(capsys, *args):
    capsys.readouterr()
    assert main(["--data", FIXTURE, "report", *args]) in (0, None)
    return capsys.readouterr().out


def test_report_as_json(capsys):
    assert json.loads(report(capsys, "--since", "2026-10-15", "--json")) == [PIP, KIWI, ROCKET]


def test_json_with_until(capsys):
    assert json.loads(report(capsys, "--since", "2026-10-15", "--until", "2026-10-17", "--json")) == [PIP, KIWI]


def test_no_visits_is_an_empty_array(capsys):
    assert json.loads(report(capsys, "--since", "2027-01-01", "--json")) == []


def test_report_without_json_is_still_a_table(capsys):
    lines = report(capsys, "--since", "2026-10-15").splitlines()
    assert lines[0].split() == ["date", "time", "pet", "owner", "reason"]
    assert len(lines) == 4
