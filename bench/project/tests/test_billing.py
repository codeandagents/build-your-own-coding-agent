from datetime import date, datetime

import pytest

from petclinic.billing import Invoice, consultation_invoice, format_invoice, money
from petclinic.billing.insurance import Claim, member_discount
from petclinic.errors import ValidationError
from petclinic.store import Store


def test_money():
    assert money(8500) == "$85.00"
    assert money(123456) == "$1,234.56"
    assert money(5) == "$0.05"
    assert money(-850) == "-$8.50"


def test_subtotal_gst_and_total():
    invoice = Invoice(pet_id=1)
    invoice.add("Consultation", 8500)
    invoice.add("Meloxicam oral 10 ml", 2380, kind="medicine")
    assert invoice.subtotal() == 10880
    assert invoice.gst() == 1632  # 15% of $108.80
    assert invoice.total() == 12512


def test_quantity_multiplies():
    invoice = Invoice(pet_id=1)
    line = invoice.add("Amoxicillin 250 mg tablets", 120, quantity=10, kind="medicine")
    assert line.amount == 1200
    assert invoice.gst() == 180


def test_money_must_be_whole_cents():
    with pytest.raises(ValidationError, match="^cents:"):
        Invoice(pet_id=1).add("Consultation", 85.0)


def test_quantity_and_kind_are_checked():
    with pytest.raises(ValidationError, match="^quantity:"):
        Invoice(pet_id=1).add("Syringes", 40, quantity=0, kind="medicine")
    with pytest.raises(ValidationError, match="^kind:"):
        Invoice(pet_id=1).add("Grooming", 4000, kind="grooming")


def test_only_discounts_are_negative():
    with pytest.raises(ValidationError, match="^cents:"):
        Invoice(pet_id=1).add("Refund", -500)
    with pytest.raises(ValidationError, match="^cents:"):
        Invoice(pet_id=1).add("Loyalty discount", 500, kind="discount")


def test_consultation_invoice_from_the_fixture(clinic):
    invoice = consultation_invoice(clinic, 1)
    assert [(line.description, line.amount, line.kind) for line in invoice.lines] == [
        ("Consultation: annual check-up", 8500, "consult")]
    assert invoice.total() == 9775
    assert invoice.visit_id == 1


def test_consultation_invoice_with_extras():
    store = Store()
    owner = store.add_owner("Ben Carter", "027 555 0199")
    pet = store.add_pet(owner.id, "Rocket", "rabbit", date(2024, 2, 29))
    visit = store.book_visit(pet.id, datetime(2026, 10, 22, 11, 0), "teeth")
    invoice = consultation_invoice(store, visit.id, extras=[("Dental procedure", 12000, 1, "procedure"),
                                                            ("Syringes 3 ml", 40, 2, "medicine")])
    assert [line.kind for line in invoice.lines] == ["consult", "procedure", "medicine"]
    assert invoice.subtotal() == 8500 + 12000 + 80
    assert invoice.gst() == 3087  # 15% of $205.80


def test_petcover_members_get_their_discount(clinic):
    invoice = consultation_invoice(clinic, 6)  # Biscuit; Kauri Aumua is a PetCover member
    assert [(line.description, line.amount) for line in invoice.lines] == [
        ("Consultation: skin rash", 8500), ("PetCover member discount", -637)]
    assert invoice.subtotal() == 7863
    assert invoice.total() == 9042


def test_petcover_discount_is_rounded_down():
    assert member_discount(12345) == 925  # 7.5% of $123.45 is $9.25875
    assert member_discount(8500) == 637   # $6.375


def test_petcover_claim_row():
    assert Claim("PC-118220", 9042, "Biscuit", "2026-10-14").as_row() == ["PC-118220", "Biscuit", "2026-10-14", "90.42"]


def test_format_invoice_ends_with_the_totals():
    invoice = Invoice(pet_id=1)
    invoice.add("Consultation", 8500)
    lines = format_invoice(invoice).splitlines()
    assert [line.split()[-1] for line in lines[-3:]] == ["$85.00", "$12.75", "$97.75"]
    assert lines[-2].startswith("GST 15%")
