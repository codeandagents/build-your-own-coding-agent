"""Monthly statements: what an owner was invoiced and paid in a month, and what they still owe."""
from dataclasses import dataclass, field
from datetime import date

from ..money import money
from ..periods import Period
from .invoices import consultation_invoice
from .payments import surcharge_in


@dataclass
class StatementLine:
    day: date
    description: str
    cents: int  # invoices positive, payments negative


@dataclass
class Statement:
    owner_id: int
    period: Period
    opening: int                       # owed before the month started
    lines: list[StatementLine] = field(default_factory=list)

    @property
    def closing(self) -> int:
        return self.opening + sum(line.cents for line in self.lines)


def _invoiced_and_paid(store, owner_id: int):
    """Every invoice and payment of the owner's visits, as (day, description, cents)."""
    for visit in store.visits_for_owner(owner_id):
        pet = store.pets[visit.pet_id]
        yield visit.start.date(), f"{pet.name}: {visit.reason}", consultation_invoice(store, visit.id).total()
        for payment in store.payments_for_visit(visit.id):
            paid = payment.cents - surcharge_in(payment.cents, payment.method)
            yield payment.paid.date(), f"Payment, {payment.method}", -paid


def statement(store, owner_id: int, period: Period, today: date) -> Statement:
    """The statement for `period`. Visits after `today` aren't invoiced yet."""
    opening, lines = 0, []
    for day, description, cents in sorted(_invoiced_and_paid(store, owner_id)):
        if day > today:
            continue
        if day < period.start:
            opening += cents
        elif day in period:
            lines.append(StatementLine(day, description, cents))
    return Statement(owner_id, period, opening, lines)


def format_statement(store, s: Statement) -> str:
    owner = store.owners[s.owner_id]
    out = [f"Statement for {owner.name}, {s.period.start:%B %Y}",
           f"{'Owed at the start of the month':48}  {money(s.opening):>11}"]
    for line in s.lines:
        out.append(f"{line.day:%d %b}  {line.description[:40]:40}  {money(line.cents):>11}")
    out.append(f"{'Balance to pay':48}  {money(s.closing):>11}")
    return "\n".join(out)
