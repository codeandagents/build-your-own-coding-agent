from datetime import date
from pathlib import Path

from petclinic.billing import Invoice
from petclinic.billing.takings import format_takings, takings
from petclinic.money import percent_of
from petclinic.store import Store

FIXTURE = Path(__file__).parent / "fixtures" / "clinic.json"


def gst(cents: int) -> int:
    invoice = Invoice(pet_id=1)
    invoice.add("Consultation", cents)
    return invoice.gst()


def test_the_clients_invoice():
    assert gst(3310) == 497  # 496.5 cents


def test_half_a_cent_rounds_up():
    assert gst(30) == 5      # 4.5 cents
    assert gst(70) == 11     # 10.5 cents
    assert gst(50) == 8      # 7.5 cents
    assert gst(3330) == 500  # 499.5 cents


def test_exact_and_small_amounts():
    assert gst(1000) == 150
    assert gst(4) == 1       # 0.6 cents
    assert gst(1) == 0       # 0.15 cents
    assert gst(0) == 0


def test_gst_is_whole_cents():
    assert type(gst(3310)) is int


def test_total_includes_the_rounded_gst():
    invoice = Invoice(pet_id=1)
    invoice.add("Consultation", 3310)
    assert invoice.total() == 3807


def test_takings_count_each_card_surcharge_once():
    clinic = Store.load(FIXTURE)
    tuesday = takings(clinic, date(2026, 10, 13))  # one credit card payment: $97.75 + $1.96 surcharge
    assert tuesday == {"credit": {"count": 1, "paid": 9971, "surcharge": 196}}
    lines = format_takings(date(2026, 10, 13), tuesday).splitlines()
    assert [line.split() for line in lines[1:3]] == [["Credit", "card", "1", "$99.71"], ["Total", "1", "$99.71"]]
    assert takings(clinic, date(2026, 10, 12)) == {"eftpos": {"count": 1, "paid": 9775, "surcharge": 0}}


def test_the_shared_helper_is_fixed():
    assert percent_of(3310, 15) == 497
    assert percent_of(1225, 2) == 25
    assert percent_of(12745, 10) == 1275  # 1274.5 cents
    assert type(percent_of(3310, 15)) is int
