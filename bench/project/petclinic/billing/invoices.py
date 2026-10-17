"""Invoices. Money is always integer cents."""
from dataclasses import dataclass, field

from ..errors import ValidationError
from ..money import money, percent_of
from ..settings import CONSULT_CENTS, GST_PERCENT
from . import insurance

KINDS = ("consult", "medicine", "procedure", "discount")


@dataclass
class Line:
    description: str
    cents: int          # per unit, GST exclusive; negative for discounts
    quantity: int = 1
    kind: str = "consult"

    @property
    def amount(self) -> int:
        return self.cents * self.quantity


@dataclass
class Invoice:
    pet_id: int
    lines: list[Line] = field(default_factory=list)
    visit_id: int | None = None

    def add(self, description: str, cents: int, quantity: int = 1, kind: str = "consult") -> Line:
        if not isinstance(cents, int):
            raise ValidationError("cents: must be a whole number of cents")
        if quantity < 1:
            raise ValidationError("quantity: must be at least 1")
        if kind not in KINDS:
            raise ValidationError(f"kind: one of {', '.join(KINDS)}")
        if (cents < 0) != (kind == "discount") and cents != 0:
            raise ValidationError("cents: negative for discounts, and only for discounts")
        line = Line(description, cents, quantity, kind)
        self.lines.append(line)
        return line

    def lines_of(self, kind: str) -> list[Line]:
        return [line for line in self.lines if line.kind == kind]

    def subtotal(self) -> int:
        return sum(line.amount for line in self.lines)

    def gst(self) -> int:
        """GST on the subtotal."""
        return percent_of(self.subtotal(), GST_PERCENT)

    def total(self) -> int:
        return self.subtotal() + self.gst()


def consultation_invoice(store, visit_id: int, extras: tuple = ()) -> Invoice:
    """The invoice for a visit: the consultation plus extras, given as (description, cents, quantity, kind).
    Members of the clinic's insurance partner get their member discount."""
    visit = store.visits[visit_id]
    owner = store.owners[store.pets[visit.pet_id].owner_id]
    invoice = Invoice(visit.pet_id, visit_id=visit.id)
    invoice.add(f"Consultation: {visit.reason}", CONSULT_CENTS)
    for description, cents, quantity, kind in extras:
        invoice.add(description, cents, quantity, kind)
    if owner.insurer == insurance.PETCOVER:
        insurance.add_member_discount(invoice)
    return invoice


def format_invoice(invoice: Invoice) -> str:
    lines = [f"{line.description[:40]:40}  {line.quantity:>3}  {money(line.amount):>11}" for line in invoice.lines]
    lines += [f"{'Subtotal':40}  {'':>3}  {money(invoice.subtotal()):>11}",
              f"{'GST ' + str(GST_PERCENT) + '%':40}  {'':>3}  {money(invoice.gst()):>11}",
              f"{'Total':40}  {'':>3}  {money(invoice.total()):>11}"]
    return "\n".join(lines)
