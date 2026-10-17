from conftest import FIXTURES

from petclinic.cli import main
from petclinic.store import Store

STAFF = str(FIXTURES / "staff.json")
FEES = str(FIXTURES / "fees.json")


def run(clinic_file, capsys, *args):
    code = main(["--data", str(clinic_file), *args])
    out, err = capsys.readouterr()
    return code, out, err


def test_owners_sorted_by_name(clinic_file, capsys):
    code, out, _ = run(clinic_file, capsys, "owners")
    lines = out.splitlines()
    names = [line[5:25].strip() for line in lines]
    assert code == 0
    assert names == sorted(names)
    assert {"Aroha Ngata", "Ben Carter", "Mei Lin"} <= set(names)
    assert any("Aroha Ngata" in line and "021 555 0101" in line for line in lines)


def test_report_since(clinic_file, capsys):
    _, out, _ = run(clinic_file, capsys, "report", "--since", "2026-10-16")
    assert "follow-up" in out and "nail trim" in out
    assert "vaccination" not in out


def test_invoice_for_a_visit(clinic_file, capsys):
    code, out, _ = run(clinic_file, capsys, "invoice", "1")
    assert code == 0
    assert "Consultation: annual check-up" in out
    assert out.splitlines()[-1].split() == ["Total", "$97.75"]


def test_invoice_with_fees_from_the_price_list(clinic_file, capsys):
    _, out, _ = run(clinic_file, capsys, "invoice", "1", "--add", "MED-MELOX", "--add", "MED-AMOX*10", "--fees", FEES)
    lines = out.splitlines()
    assert lines[2].split()[-2:] == ["10", "$12.00"]
    assert lines[-1].split() == ["Total", "$138.92"]


def test_one_reminder_per_owner(clinic_file, capsys):
    code, out, _ = run(clinic_file, capsys, "reminders", "--on", "2026-10-21")
    lines = out.splitlines()
    aroha = [line for line in lines if line.startswith("021 555 0101: ")]
    mei = [line for line in lines if line.startswith("022-555-0142: ")]
    assert code == 0
    assert len(aroha) == 1 and len(mei) == 1
    assert "Kiwi and Pip" in aroha[0] and "Wed 28 Oct" in aroha[0]
    assert "Mochi" in mei[0] and "FeLV" in mei[0]
    assert not any(line.startswith("027 555 0199") for line in lines)  # Rocket isn't due yet


def test_rota_while_a_vet_is_on_leave(clinic_file, capsys):
    code, out, _ = run(clinic_file, capsys, "rota", "--date", "2026-11-04", "--staff", STAFF)
    assert code == 0
    assert out.splitlines()[0] == "On duty Wed 04 Nov: Dr Sam Walker, Dr Hine Tane"


def test_nobody_on_duty_at_weekends(clinic_file, capsys):
    _, out, _ = run(clinic_file, capsys, "rota", "--date", "2026-10-24", "--staff", STAFF)
    assert out.splitlines() == ["On duty Sat 24 Oct: nobody"]


def test_online_slots(clinic_file, capsys):
    _, out, _ = run(clinic_file, capsys, "online-slots", "--date", "2026-10-22", "--staff", STAFF)
    lines = out.splitlines()
    assert lines[0] == "Thu 22 Oct with Dr Priya Patel, Dr Sam Walker, Dr Hine Tane:"
    assert "10:00 11:00" in lines[1]  # 10:30 is taken
    _, out, _ = run(clinic_file, capsys, "online-slots", "--date", "2026-11-04", "--vet", "1", "--staff", STAFF)
    assert out.strip() == "Nothing free on Wed 04 Nov."


def test_book_and_cancel(clinic_file, capsys):
    _, out, _ = run(clinic_file, capsys, "book", "2", "2026-10-23 09:00", "check-up")
    assert out.strip() == "Visit 9 booked: Fri 23 Oct 09:00"
    assert Store.load(clinic_file).visits[9].reason == "check-up"
    _, out, _ = run(clinic_file, capsys, "cancel", "9")
    assert out.strip() == "Visit 9 cancelled"
    assert 9 not in Store.load(clinic_file).visits


def test_errors_are_printed_not_raised(clinic_file, capsys):
    code, out, err = run(clinic_file, capsys, "book", "2", "2026-10-22 10:30", "check-up")
    assert code == 2
    assert err.startswith("error: start:")


def test_pay_and_takings(clinic_file, capsys):
    _, out, _ = run(clinic_file, capsys, "pay", "5", "--method", "credit")
    assert out.strip() == "Paid $99.71 by credit."
    _, out, _ = run(clinic_file, capsys, "takings", "--date", "2026-10-13")
    assert out.splitlines()[1].split()[:3] == ["Credit", "card", "1"]


def test_statement(clinic_file, capsys):
    _, out, _ = run(clinic_file, capsys, "statement", "4", "--month", "2026-10", "--on", "2026-10-16")
    assert out.splitlines()[-1].split()[-1] == "$47.75"


def test_merge_owners(clinic_file, capsys):
    run(clinic_file, capsys, "add-owner", "mei lin", "022 555 0142")
    run(clinic_file, capsys, "add-pet", "6", "Mochi", "cat", "2021-07-08")
    _, out, _ = run(clinic_file, capsys, "merge-owners", "3", "6")
    assert out.splitlines() == ["Mochi: merged into pet 4", "Owner 6 merged into owner 3"]
    store = Store.load(clinic_file)
    assert 6 not in store.owners and 7 not in store.pets


def test_search_and_audit(clinic_file, capsys):
    _, out, _ = run(clinic_file, capsys, "search", "0142")
    assert "Mei Lin" in out
    run(clinic_file, capsys, "add-owner", "Hemi Walker", "021 555 0876")
    _, out, _ = run(clinic_file, capsys, "audit", "--who", "front desk")
    assert out.strip().endswith("owner 6 added: 'Hemi Walker' (021 555 0876)")
