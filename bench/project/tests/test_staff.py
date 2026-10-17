import json
from datetime import date

from conftest import FIXTURES

from petclinic.periods import Period
from petclinic.staff import Vet, back_at_work, leave_in, load_staff, on_duty

STAFF = FIXTURES / "staff.json"


def test_load_staff():
    vets, leave = load_staff(STAFF)
    assert [v.name for v in vets] == ["Dr Priya Patel", "Dr Sam Walker", "Dr Hine Tane"]
    patel = [x for x in leave if x.vet_id == 1]
    assert [x.period.start for x in patel] == [date(2026, 11, 2)]
    assert patel[0].note == "conference, Wellington"


def test_everyone_on_duty_on_a_normal_weekday():
    vets, leave = load_staff(STAFF)
    assert on_duty(date(2026, 10, 21), vets, leave) == vets


def test_a_vet_on_leave_is_not_on_duty():
    vets, leave = load_staff(STAFF)
    assert [v.name for v in on_duty(date(2026, 11, 3), vets, leave)] == ["Dr Sam Walker", "Dr Hine Tane"]
    assert [v.name for v in on_duty(date(2027, 1, 5), vets, leave)] == ["Dr Priya Patel", "Dr Hine Tane"]


def test_nobody_on_duty_at_weekends():
    vets, leave = load_staff(STAFF)
    assert on_duty(date(2026, 11, 7), vets, leave) == []


def test_back_at_work_skips_the_weekend():
    vet = Vet(3, "Dr Hine Tane")
    assert back_at_work(vet, date(2026, 10, 23), []) == date(2026, 10, 26)
    assert back_at_work(vet, date(2026, 10, 21), []) == date(2026, 10, 22)


def test_leave_in_a_month():
    vets, leave = load_staff(STAFF)
    assert [x.vet_id for x in leave_in(Period.month(2026, 11), leave)] == [1]
    assert [x.vet_id for x in leave_in(Period.month(2027, 1), leave)] == [2, 3]


def test_leave_notes(tmp_path):
    path = tmp_path / "staff.json"
    path.write_text(json.dumps({"vets": [{"id": 1, "name": "Dr Priya Patel"}],
                                "leave": [{"vet_id": 1, "first_day": "2026-11-02", "last_day": "2026-11-03"}]}),
                    encoding="utf-8")
    assert load_staff(path)[1][0].note == ""


def test_initials():
    assert Vet(1, "Dr Priya Patel").initials == "PP"
