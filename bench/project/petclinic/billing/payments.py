"""Taking payment for a visit at the front desk."""
import logging
from datetime import datetime

from ..errors import ValidationError
from ..money import money
from ..settings import CARD_SURCHARGE_PERCENT
from .invoices import consultation_invoice

log = logging.getLogger("petclinic.billing.payments")


def surcharge(cents: int, method: str) -> int:
    """The card surcharge on a payment of `cents`: credit cards only, rounded half up to the cent."""
    if method != "credit":
        return 0
    return (cents * CARD_SURCHARGE_PERCENT + 50) // 100


def amount_due(store, visit_id: int) -> int:
    """The visit's invoice total less what has been paid towards it (surcharges don't count as paid)."""
    total = consultation_invoice(store, visit_id).total()
    paid = sum(p.cents - surcharge_in(p.cents, p.method) for p in store.payments_for_visit(visit_id))
    return total - paid


def surcharge_in(paid: int, method: str) -> int:
    """The surcharge inside a card payment of `paid` cents (paid = amount + surcharge(amount))."""
    if method != "credit":
        return 0
    for amount in range(paid * 100 // (100 + CARD_SURCHARGE_PERCENT) - 1, paid + 1):
        if amount + surcharge(amount, method) == paid:
            return paid - amount
    raise ValidationError(f"cents: {money(paid)} isn't an amount plus its surcharge")


def take_payment(store, visit_id: int, method: str, when: datetime, cents: int | None = None):
    """Record a payment: by default the whole amount due, plus the surcharge for credit cards."""
    due = amount_due(store, visit_id)
    if due <= 0:
        raise ValidationError(f"visit_id: visit {visit_id} is paid")
    amount = due if cents is None else cents
    if amount > due:
        raise ValidationError(f"cents: {money(amount)} is more than the {money(due)} due")
    payment = store.add_payment(visit_id, amount + surcharge(amount, method), method, when)
    log.info("visit %d: %s by %s", visit_id, money(payment.cents), method)
    return payment
