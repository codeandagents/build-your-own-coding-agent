# Billing: house rules for this package

These rules come on top of `docs/CONVENTIONS.md`. The clinic's accountant checks a sample of invoices against them
every month, and code review rejects a change that breaks one.

## Amounts

- Money is an `int` number of cents. Show it with `money.money()`.
- A percentage of an amount is `money.percent_of(cents, percent)`: rounded half up to the cent. Never `round()`,
  never a float, never `//` (that rounds down).
- Prices are GST exclusive. GST is charged once, on the invoice's subtotal (`Invoice.gst`).

## Invoices

- `consultation_invoice` builds every visit's invoice: the `invoice` command, statements, takings and the
  accountant's export all call it.
- PetCover's member discount (`insurance.py`) follows the partnership contract word for word. Change it only when
  the contract changes.
- Prices come from `data/fees.json` (`fees.py`). Code never changes a price.

## Tests

- `tests/test_billing.py` and `tests/test_billing_*.py`. Write expected amounts as int literals, with the sum in a
  comment: `assert invoice.gst() == 1632  # 15% of $108.80`.
