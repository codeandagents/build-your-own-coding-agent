"""The price list (data/fees.json): what the clinic charges for each service, medicine and procedure.

Prices are GST exclusive, in cents. The practice manager updates the file; code never changes a price."""
import json
from dataclasses import dataclass
from pathlib import Path

from ..errors import NotFound, ValidationError


@dataclass(frozen=True)
class Fee:
    code: str
    description: str
    cents: int
    kind: str  # consult, medicine or procedure


def load_fees(path: str | Path) -> dict[str, Fee]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    fees = {}
    for row in data["fees"]:
        if row["kind"] not in ("consult", "medicine", "procedure"):
            raise ValidationError(f"kind: {row['code']} has kind {row['kind']!r}")
        fees[row["code"]] = Fee(row["code"], row["description"], row["cents"], row["kind"])
    return fees


def parse_extra(text: str, fees: dict[str, Fee]) -> tuple[str, int, int, str]:
    """"MED-MELOX" or "MED-AMOX*10" -> an invoice extra (description, cents, quantity, kind)."""
    code, _, quantity = text.partition("*")
    fee = fees.get(code.strip().upper())
    if fee is None:
        raise NotFound(f"code: no fee {code!r} in the price list")
    if quantity and not quantity.isdigit():
        raise ValidationError(f"quantity: {quantity!r} is not a whole number")
    return fee.description, fee.cents, int(quantity or 1), fee.kind
