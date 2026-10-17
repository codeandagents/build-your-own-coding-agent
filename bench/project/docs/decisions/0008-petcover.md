# 0008: PetCover member discount

**Date:** 2024-07-01. **Status:** accepted.

**Context.** The clinic became PetCover's preferred provider in Auckland (contract PC-2024-17). PetCover sets the
member discount and how it appears on invoices, so its claims system can match them.

**Decision.** `billing/insurance.py` implements the contract's terms exactly: 7.5% off the whole invoice before GST,
rounded down to the cent, one line "PetCover member discount" at the end. Owners who are members have
`insurer: "PetCover"`. The contract's terms aren't the clinic's own rules for discounts and aren't a model for them.

**Consequences.** When the contract changes, only `insurance.py` changes.
