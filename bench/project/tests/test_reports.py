from datetime import date

from conftest import FIXTURES

from petclinic.exporter import HEADER, export_month, invoice_rows
from petclinic.periods import Period
from petclinic.reports import busiest_days, format_table, species_mix, vet_workload, visit_rows
from petclinic.staff import load_staff

OCTOBER = Period.month(2026, 10)


def test_rows_since_a_date_oldest_first(clinic):
    rows = visit_rows(clinic, date(2026, 10, 14))
    assert [(r["date"], r["pet"]) for r in rows] == [
        ("2026-10-14", "Biscuit"), ("2026-10-14", "Mochi"), ("2026-10-15", "Pip"), ("2026-10-16", "Kiwi"),
        ("2026-10-22", "Rocket")]
    assert rows[1] == {"date": "2026-10-14", "time": "16:00", "pet": "Mochi", "owner": "Mei Lin",
                       "reason": "vaccination"}


def test_rows_until_a_date(clinic):
    rows = visit_rows(clinic, date(2026, 10, 12), date(2026, 10, 14))
    assert [r["pet"] for r in rows] == ["Kiwi", "Rocket"]  # the 14th isn't included


def test_empty_report():
    assert format_table([]) == "No visits."


def test_table_has_a_header_and_one_line_per_visit(clinic):
    lines = format_table(visit_rows(clinic, date(2026, 10, 15), date(2026, 10, 17))).splitlines()
    assert lines[0].split() == ["date", "time", "pet", "owner", "reason"]
    assert len(lines) == 3


def test_busiest_days(clinic):
    assert busiest_days(clinic, OCTOBER, top=2) == [(date(2026, 10, 14), 2), (date(2026, 10, 12), 1)]


def test_species_mix(clinic):
    assert species_mix(clinic) == {"cat": 3, "dog": 2, "rabbit": 1}


def test_vet_workload(clinic):
    vets, _ = load_staff(FIXTURES / "staff.json")
    assert vet_workload(clinic, OCTOBER, vets) == [("Dr Priya Patel", 3), ("Dr Hine Tane", 2), ("Dr Sam Walker", 2)]


def test_accountants_export(clinic, tmp_path):
    rows = invoice_rows(clinic, OCTOBER)
    assert len(rows) == 7
    assert rows[0] == ["2026-10-12", 1, "Aroha Ngata", "Kiwi", 8500, 1275, 9775]
    assert ["2026-10-14", 6, "Kauri Aumua", "Biscuit", 7863, 1179, 9042] in rows
    assert export_month(clinic, OCTOBER, tmp_path / "out.csv") == 7
    assert (tmp_path / "out.csv").read_text(encoding="utf-8").splitlines()[0] == ",".join(HEADER)
