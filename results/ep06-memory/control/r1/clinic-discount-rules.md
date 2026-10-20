---
name: Clinic discount line rules
description: How the clinic's own (non-PetCover) invoice discounts must appear; accountant checks them monthly
type: project
---
- A discount is its own line: kind "discount", quantity 1, negative amount. Never change a price.
- Description is the name plus percentage in brackets, e.g. "Multi-pet discount (5%)".
- Percentage is of consultation lines (kind "consult") only, via money.percent_of (half up).
- Discount line goes directly after the last consultation line, before medicine/procedure lines.
- GST is charged on the discounted subtotal.
- PetCover is the exception (whole invoice, rounded down, at the end); don't copy it.
