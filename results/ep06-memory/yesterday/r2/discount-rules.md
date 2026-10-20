---
name: Clinic discount rules
description: How every clinic discount must appear on invoices (accountant checks them monthly)
type: feedback
---
Every clinic discount on an invoice:
- is its own line: kind "discount", quantity 1, negative amount (never a changed price);
- description is the name plus percentage in brackets, e.g. "Multi-pet discount (5%)";
- is a percentage of the consultation lines (kind "consult") only, via money.percent_of (half up);
- sits directly after the last consultation line, before medicine/procedure lines;
- GST is charged on the discounted subtotal (Invoice.gst does this).

PetCover's discount is the contract's exception (whole invoice, rounded down, at the end): do not copy it.

Why: the accountant checks a sample of invoices monthly against these rules (raised in code review of the multi-pet discount).
