import json
from datetime import date, datetime
from pathlib import Path

import pytest

from petclinic.booking import BookingRequest, available, book
from petclinic.cli import main
from petclinic.errors import ValidationError
from petclinic.periods import Period
from petclinic.reports import visit_rows
from petclinic.staff import back_at_work, load_staff, on_duty
from petclinic.store import Store

FIXTURES = Path(__file__).parent / "fixtures"
CLINIC = FIXTURES / "clinic.json"
STAFF = FIXTURES / "staff.json"  # the practice manager's file: Patel away 2-6 Nov, Walker 21 Dec-8 Jan
LIVE_STAFF = Path(__file__).parent.parent / "data" / "staff.json"


def spreadsheet_export(tmp_path):
    """The same staff file as the spreadsheet writes it: Walker's December leave with its id as text."""
    data = json.loads(STAFF.read_text(encoding="utf-8"))
    for x in data["leave"]:
        if x["vet_id"] == 2 and x["first_day"] == "2026-12-21":
            x["vet_id"] = "2"
    path = tmp_path / "staff.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def names(vets):
    return [v.name for v in vets]


def test_the_booking_page_doesnt_offer_her_last_day():
    clinic = Store.load(CLINIC)
    vets, leave = load_staff(STAFF)
    assert available(clinic, date(2026, 11, 6), vets, leave, vet_id=1).times == []
    assert len(available(clinic, date(2026, 11, 9), vets, leave, vet_id=1).times) == 16
    assert names(available(clinic, date(2026, 11, 6), vets, leave).vets) == ["Dr Sam Walker", "Dr Hine Tane"]
    request = BookingRequest("Ben Carter", "027 555 0199", "Rocket", datetime(2026, 11, 6, 10, 0), "check-up", 1)
    with pytest.raises(ValidationError, match="^start:"):
        book(clinic, request, vets, leave)


def test_the_online_slots_command(capsys):
    main(["--data", str(CLINIC), "online-slots", "--date", "2026-11-06", "--vet", "1", "--staff", str(STAFF)])
    assert capsys.readouterr().out.strip() == "Nothing free on Fri 06 Nov."


def test_away_on_the_last_day_of_leave():
    vets, leave = load_staff(STAFF)
    assert names(on_duty(date(2026, 11, 6), vets, leave)) == ["Dr Sam Walker", "Dr Hine Tane"]
    assert names(on_duty(date(2027, 1, 8), vets, leave)) == ["Dr Priya Patel", "Dr Hine Tane"]


def test_back_on_the_next_working_day():
    vets, leave = load_staff(STAFF)
    patel, walker = vets[0], vets[1]
    assert back_at_work(patel, date(2026, 11, 2), leave) == date(2026, 11, 9)
    assert back_at_work(walker, date(2026, 12, 21), leave) == date(2027, 1, 11)
    assert names(on_duty(date(2026, 11, 9), vets, leave)) == names(vets)


def test_one_day_of_leave(tmp_path):
    path = tmp_path / "staff.json"
    path.write_text(json.dumps({"vets": [{"id": 3, "name": "Dr Hine Tane"}],
                                "leave": [{"vet_id": 3, "first_day": "2026-11-11", "last_day": "2026-11-11"}]}),
                    encoding="utf-8")
    vets, leave = load_staff(path)
    assert on_duty(date(2026, 11, 11), vets, leave) == []
    assert back_at_work(vets[0], date(2026, 11, 10), leave) == date(2026, 11, 12)


def test_the_rota_command(capsys):
    main(["--data", str(CLINIC), "rota", "--date", "2026-11-06", "--staff", str(STAFF)])
    assert capsys.readouterr().out.splitlines() == [
        "On duty Fri 06 Nov: Dr Sam Walker, Dr Hine Tane",
        "  Dr Priya Patel is away, back Mon 09 Nov",
    ]


def test_periods_are_still_half_open():
    assert date(2026, 11, 6) not in Period(date(2026, 11, 2), date(2026, 11, 6))
    assert date(2026, 11, 1) not in Period.month(2026, 10)
    assert [r["pet"] for r in visit_rows(Store.load(CLINIC), date(2026, 10, 12), date(2026, 10, 14))] == ["Kiwi",
                                                                                                         "Rocket"]


def test_leave_with_a_text_id(tmp_path):
    vets, leave = load_staff(spreadsheet_export(tmp_path))
    assert names(on_duty(date(2026, 12, 22), vets, leave)) == ["Dr Priya Patel", "Dr Hine Tane"]
    assert names(on_duty(date(2027, 1, 8), vets, leave)) == ["Dr Priya Patel", "Dr Hine Tane"]
    assert back_at_work(vets[1], date(2026, 12, 21), leave) == date(2027, 1, 11)
    assert names(on_duty(date(2026, 11, 6), vets, leave)) == ["Dr Sam Walker", "Dr Hine Tane"]


def test_the_booking_page_doesnt_offer_walker_at_christmas(tmp_path):
    clinic = Store.load(CLINIC)
    vets, leave = load_staff(spreadsheet_export(tmp_path))
    assert available(clinic, date(2026, 12, 22), vets, leave, vet_id=2).times == []
    request = BookingRequest("Mei Lin", "022-555-0142", "Mochi", datetime(2026, 12, 22, 9, 30), "check-up", 2)
    with pytest.raises(ValidationError, match="^start:"):
        book(clinic, request, vets, leave)


def test_the_staff_file_was_not_edited():
    text = LIVE_STAFF.read_text(encoding="utf-8")
    assert '"vet_id": "2"' in text and '"last_day": "2026-11-06"' in text
