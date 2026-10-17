"""PetCover, the clinic's insurance partner (decision 0008).

The partnership contract (PC-2024-17) sets the member discount, and its wording is the contract's, not ours:
- clause 4.1: members get 7.5% off the whole invoice, medicines and procedures included, before GST;
- clause 4.2: the discount is rounded down to the cent, and shown as one line, "PetCover member discount",
  at the end of the invoice;
- clause 6: claims are sent to PetCover with the invoice total and the member's policy number.
"""
from dataclasses import dataclass

PETCOVER = "PetCover"
MEMBER_DISCOUNT_LINE = "PetCover member discount"
MEMBER_DISCOUNT_PER_MILLE = 75  # 7.5%


def member_discount(subtotal: int) -> int:
    """Clause 4.2: 7.5% of the subtotal, rounded down to the cent."""
    return subtotal * MEMBER_DISCOUNT_PER_MILLE // 1000


def add_member_discount(invoice) -> None:
    discount = member_discount(invoice.subtotal())
    if discount:
        invoice.add(MEMBER_DISCOUNT_LINE, -discount, kind="discount")


@dataclass
class Claim:
    policy: str
    invoice_total: int
    pet_name: str
    visit_date: str

    def as_row(self) -> list[str]:
        """A row of the monthly claims file PetCover asks for (clause 6)."""
        dollars, cents = divmod(self.invoice_total, 100)
        return [self.policy, self.pet_name, self.visit_date, f"{dollars}.{cents:02d}"]
