"""End of day: the takings by payment method, for the cash-up (docs/runbooks/end-of-day.md)."""
from collections import defaultdict
from datetime import date

from ..money import money
from .payments import surcharge_in

METHOD_NAMES = {"eftpos": "EFTPOS", "credit": "Credit card", "cash": "Cash"}


def takings(store, day: date) -> dict[str, dict[str, int]]:
    """Per method: count, paid (surcharges included) and surcharge, for payments made on `day`."""
    totals: dict[str, dict[str, int]] = defaultdict(lambda: {"count": 0, "paid": 0, "surcharge": 0})
    for payment in store.payments.values():
        if payment.paid.date() != day:
            continue
        row = totals[payment.method]
        row["count"] += 1
        row["paid"] += payment.cents
        row["surcharge"] += surcharge_in(payment.cents, payment.method)
    return dict(totals)


def format_takings(day: date, totals: dict[str, dict[str, int]]) -> str:
    if not totals:
        return f"No payments on {day:%a %d %b %Y}."
    lines = [f"Takings for {day:%a %d %b %Y}"]
    for method in ("eftpos", "credit", "cash"):
        if method in totals:
            row = totals[method]
            lines.append(f"{METHOD_NAMES[method]:12}  {row['count']:>3}  {money(row['paid']):>11}")
    surcharges = sum(row["surcharge"] for row in totals.values())
    lines.append(f"{'Total':12}  {sum(r['count'] for r in totals.values()):>3}  "
                 f"{money(sum(r['paid'] for r in totals.values())):>11}")
    if surcharges:
        lines.append(f"  of which card surcharges {money(surcharges)}")
    return "\n".join(lines)
