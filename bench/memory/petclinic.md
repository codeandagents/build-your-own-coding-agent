# Notes I've kept about PetClinic Lite (Harbourside Vets)

What earlier sessions learned, from the practice manager and from code review. Not in the repository.

## Billing

- 2026-09-30, after code review sent back the "Multi-pet discount": the clinic's own discounts must follow these
  rules, and the accountant checks a sample of invoices against them every month.
  - A discount is its own invoice line, never a changed price: kind "discount", quantity 1, a negative amount.
  - Its description is the discount's name and its percentage in brackets: "Multi-pet discount (5%)".
  - It is a percentage of the consultation lines (kind "consult") only, worked out with `money.percent_of`
    (half up). Medicines and procedures keep their full price.
  - The discount line goes directly after the last consultation line, before any medicine or procedure lines,
    so the printed invoice shows it next to what it reduces.
  - GST is then charged on the discounted subtotal (`Invoice.gst` does that by itself).
  - PetCover's member discount (billing/insurance.py) is the contract's exception: the whole invoice, rounded
    down, at the end. Don't copy it.
- Discounts the clinic gives on visits go in `billing.consultation_invoice`: statements, takings and the export
  all build invoices with it.

## Working on the project

- Tests: `python -m pytest -q` from the project folder, about a second. They use `tests/fixtures/`, never the live
  `clinic.json`.
- New or changed command output goes in `docs/front-desk-guide.md`; the desk prints it.
- The weekly import runs on Mondays at 06:00, and the practice manager reads its log the same morning.
