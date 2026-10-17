from datetime import date, datetime

import pytest
from conftest import FIXTURES

from petclinic.billing.fees import load_fees, parse_extra
from petclinic.billing.payments import amount_due, surcharge, surcharge_in, take_payment
from petclinic.billing.statements import format_statement, statement
from petclinic.billing.takings import format_takings, takings
from petclinic.errors import NotFound, ValidationError
from petclinic.periods import Period

FEES = FIXTURES / "fees.json"
OCTOBER = Period.month(2026, 10)
STATEMENT_DAY = date(2026, 10, 16)


# the price list

def test_fees():
    fees = load_fees(FEES)
    assert fees["CONSULT"].cents == 8500
    assert parse_extra("MED-AMOX*10", fees) == ("Amoxicillin 250 mg tablets", 120, 10, "medicine")
    assert parse_extra("dental", fees) == ("Dental procedure", 12000, 1, "procedure")


def test_unknown_fee():
    with pytest.raises(NotFound, match="^code:"):
        parse_extra("GROOM", load_fees(FEES))
    with pytest.raises(ValidationError, match="^quantity:"):
        parse_extra("MED-AMOX*ten", load_fees(FEES))


# payments

def test_card_surcharge():
    assert surcharge(8500, "credit") == 170  # 2% of $85.00
    assert surcharge(10000, "credit") == 200
    assert surcharge(8500, "eftpos") == 0
    assert surcharge(8500, "cash") == 0


def test_surcharge_inside_a_payment():
    assert surcharge_in(9971, "credit") == 196
    assert surcharge_in(8670, "credit") == 170
    assert surcharge_in(9775, "eftpos") == 0


def test_amount_due(clinic):
    assert amount_due(clinic, 1) == 0      # paid by EFTPOS
    assert amount_due(clinic, 2) == 0      # paid by credit card, surcharge on top
    assert amount_due(clinic, 7) == 4775   # $50 paid of $97.75
    assert amount_due(clinic, 5) == 9775


def test_take_payment_by_credit_card(clinic):
    payment = take_payment(clinic, 5, "credit", datetime(2026, 10, 16, 15, 10))
    assert payment.cents == 9971
    assert amount_due(clinic, 5) == 0


def test_part_payment(clinic):
    take_payment(clinic, 7, "cash", datetime(2026, 10, 16, 9, 5), cents=775)
    assert amount_due(clinic, 7) == 4000


def test_cannot_pay_twice_or_too_much(clinic):
    with pytest.raises(ValidationError, match="^visit_id:"):
        take_payment(clinic, 1, "cash", datetime(2026, 10, 16, 9, 5))
    with pytest.raises(ValidationError, match="^cents:"):
        take_payment(clinic, 7, "cash", datetime(2026, 10, 16, 9, 5), cents=5000)


# statements

def test_statement_for_a_month(clinic):
    s = statement(clinic, 1, OCTOBER, STATEMENT_DAY)
    assert [(line.day.day, line.description, line.cents) for line in s.lines] == [
        (12, "Kiwi: annual check-up", 9775), (12, "Payment, eftpos", -9775), (15, "Pip: limping", 9775),
        (16, "Kiwi: follow-up", 9775)]
    assert (s.opening, s.closing) == (0, 19550)


def test_opening_balance(clinic):
    s = statement(clinic, 4, OCTOBER, STATEMENT_DAY)  # Moana's September visit, $50 paid in October
    assert (s.opening, [line.cents for line in s.lines], s.closing) == (9775, [-5000], 4775)


def test_visits_after_the_statement_day_are_not_invoiced(clinic):
    assert statement(clinic, 2, OCTOBER, STATEMENT_DAY).closing == 0  # Rocket's 22 October nail trim


def test_format_statement(clinic):
    text = format_statement(clinic, statement(clinic, 4, OCTOBER, STATEMENT_DAY))
    assert text.splitlines()[0] == "Statement for Tama Parata, October 2026"
    assert text.splitlines()[-1].split()[-1] == "$47.75"


# takings

def test_takings_by_method(clinic):
    assert takings(clinic, date(2026, 10, 12)) == {"eftpos": {"count": 1, "paid": 9775, "surcharge": 0}}
    assert takings(clinic, date(2026, 10, 13))["credit"]["surcharge"] == 196


def test_format_takings(clinic):
    lines = format_takings(date(2026, 10, 14), takings(clinic, date(2026, 10, 14))).splitlines()
    assert lines[0] == "Takings for Wed 14 Oct 2026"
    assert lines[1].split() == ["Cash", "1", "$90.42"]
    assert format_takings(date(2026, 10, 17), {}) == "No payments on Sat 17 Oct 2026."
