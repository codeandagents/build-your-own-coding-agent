from datetime import date, datetime

from petclinic.billing import consultation_invoice
from petclinic.store import Store

VISIT = datetime(2026, 10, 21, 10, 0)
FOLLOW_UP = ("Follow-up consultation", 4245, 1, "consult")
MEDICINE = ("Meloxicam oral 10 ml", 2380, 1, "medicine")
PROCEDURE = ("Dental procedure", 12000, 1, "procedure")


def invoice_for(born: date, extras=()):
    store = Store()
    owner = store.add_owner("Ben Carter", "027 555 0199")
    pet = store.add_pet(owner.id, "Rocket", "rabbit", born)
    visit = store.book_visit(pet.id, VISIT, "check-up")
    return consultation_invoice(store, visit.id, extras)


def discounts(invoice):
    return [line for line in invoice.lines if line.kind == "discount"]


def test_ten_on_the_day_of_the_visit():
    invoice = invoice_for(date(2016, 10, 21), [FOLLOW_UP, MEDICINE])
    [line] = discounts(invoice)
    assert line.description == "Senior pet discount (10%)"
    assert line.amount == -1275  # 10% of $127.45 is $12.745: half up
    assert line.quantity == 1


def test_other_lines_keep_their_prices():
    invoice = invoice_for(date(2016, 10, 21), [FOLLOW_UP, MEDICINE])
    assert [(line.description, line.amount) for line in invoice.lines if line.kind != "discount"] == [
        ("Consultation: check-up", 8500), ("Follow-up consultation", 4245), ("Meloxicam oral 10 ml", 2380)]


def test_the_discount_line_follows_the_consultations():
    invoice = invoice_for(date(2016, 10, 21), [FOLLOW_UP, MEDICINE, PROCEDURE])
    assert [line.kind for line in invoice.lines] == ["consult", "consult", "discount", "medicine", "procedure"]


def test_gst_on_the_discounted_subtotal():
    invoice = invoice_for(date(2016, 10, 21), [FOLLOW_UP, MEDICINE])
    assert invoice.subtotal() == 8500 + 4245 + 2380 - 1275
    assert invoice.gst() == 2078
    assert invoice.total() == 15928


def test_medicines_and_procedures_are_not_discounted():
    invoice = invoice_for(date(2012, 3, 5), [MEDICINE, PROCEDURE])
    assert [line.amount for line in discounts(invoice)] == [-850]
    assert invoice.total() == 8500 + 2380 + 12000 - 850 + 3305


def test_nine_year_olds_pay_full_price():
    invoice = invoice_for(date(2016, 10, 22), [FOLLOW_UP])  # 10 the day after the visit
    assert discounts(invoice) == []
    assert invoice.subtotal() == 12745
