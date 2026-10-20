"""Yesterday's session, after code review: the Multi-pet discount follows the clinic's rules for discounts."""
from datetime import date, datetime

from petclinic.billing import consultation_invoice
from petclinic.store import Store

VISIT = datetime(2026, 10, 21, 10, 0)
FOLLOW_UP = ("Follow-up consultation", 4230, 1, "consult")
MEDICINE = ("Meloxicam oral 10 ml", 2380, 1, "medicine")
PROCEDURE = ("Dental procedure", 12000, 1, "procedure")
NAMES = ("Pita", "Kiri", "Moana", "Tui")


def invoice_for(pets: int, extras=()):
    store = Store()
    other = store.add_owner("Sam Lee", "027 555 0177")
    store.add_pet(other.id, "Rex", "dog", date(2019, 4, 2))  # another owner's pet doesn't count
    owner = store.add_owner("Mere Tane", "027 555 0142")
    mine = [store.add_pet(owner.id, name, "cat", date(2020, 1, 1)) for name in NAMES[:pets]]
    visit = store.book_visit(mine[0].id, VISIT, "check-up")
    return consultation_invoice(store, visit.id, extras)


def discounts(invoice):
    return [line for line in invoice.lines if line.kind == "discount"]


def test_three_pets_get_the_discount():
    invoice = invoice_for(3, [FOLLOW_UP, MEDICINE])
    [line] = discounts(invoice)
    assert line.description == "Multi-pet discount (5%)"
    assert line.amount == -637  # 5% of $127.30 is $6.365: half up
    assert line.quantity == 1


def test_other_lines_keep_their_prices():
    invoice = invoice_for(3, [FOLLOW_UP, MEDICINE])
    assert [(line.description, line.amount) for line in invoice.lines if line.kind != "discount"] == [
        ("Consultation: check-up", 8500), ("Follow-up consultation", 4230), ("Meloxicam oral 10 ml", 2380)]


def test_the_discount_line_follows_the_consultations():
    invoice = invoice_for(3, [FOLLOW_UP, MEDICINE, PROCEDURE])
    assert [line.kind for line in invoice.lines] == ["consult", "consult", "discount", "medicine", "procedure"]


def test_gst_on_the_discounted_subtotal():
    invoice = invoice_for(3, [FOLLOW_UP, MEDICINE])
    assert invoice.subtotal() == 8500 + 4230 + 2380 - 637
    assert invoice.gst() == 2171  # 15% of $144.73
    assert invoice.total() == 16644


def test_medicines_and_procedures_are_not_discounted():
    invoice = invoice_for(4, [MEDICINE, PROCEDURE])
    assert [line.amount for line in discounts(invoice)] == [-425]  # 5% of $85.00
    assert invoice.total() == 8500 + 2380 + 12000 - 425 + 3368


def test_two_pets_pay_full_price():
    invoice = invoice_for(2, [FOLLOW_UP])
    assert discounts(invoice) == []
    assert invoice.subtotal() == 12730
