---
name: Clinic discount rules for invoices
description: How every clinic-added discount must appear on invoices (accountant checks samples monthly)
type: feedback
---

Every discount the clinic adds (not PetCover's contract discount) must:
- be its own invoice line: kind "discount", quantity 1, negative amount. Never change a price.
- have a description of the name plus the percentage in brackets, e.g. "Multi-pet discount (5%)".
- be a percentage of the consultation lines (kind "consult") only, via `money.percent_of` (half up).
  Medicines and procedures keep full price.
- sit directly after the last consultation line, before any medicine or procedure lines.
- let GST be charged on the discounted subtotal (Invoice.gst does this).

PetCover's member discount is the exception: whole invoice, rounded down, at the end. Don't copy it.

**Why:** the accountant checks a monthly sample of invoices against these rules; code review sent back a version
that put the discount at the end of the invoice.
**How to apply:** use `add_discount_after_consults` in petclinic/billing/invoices.py for any new clinic discount.
