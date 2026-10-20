---
name: Clinic discount rules
description: How every clinic discount must appear on an invoice (accountant checks samples monthly)
type: feedback
---

Every clinic discount (not PetCover's, which is the contract's exception):
- its own invoice line: kind "discount", quantity 1, negative amount; never a changed price.
- description is the name plus percentage in brackets, e.g. "Multi-pet discount (5%)".
- a percentage (money.percent_of, half up) of consultation lines (kind "consult") only.
- placed directly after the last consultation line, before medicine/procedure lines.
- GST then charges on the discounted subtotal.

Why: the accountant checks a sample of invoices against these rules every month.
How to apply: use `add_discount_after_consults` in petclinic/billing/invoices.py for any new discount.
