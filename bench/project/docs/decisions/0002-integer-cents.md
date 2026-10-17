# 0002: Money in integer cents

**Date:** 2023-02-06. **Status:** accepted.

**Context.** ClinicMaster stored dollars as floats. Its invoices were sometimes a cent off the sum of their lines, and
the accountant reconciled them by hand every month.

**Decision.** Every amount is an `int` number of cents, from the price list to the export. Percentages (GST, the
card surcharge, discounts) go through one helper, `money.percent_of`, which rounds half up to the cent, as the IRD's
guidance for GST does. Display goes through `money.money`.

**Consequences.** No float anywhere near money. A percentage that isn't a whole number (PetCover's 7.5%) is written
as a per-mille or a fraction, never `0.075`.
