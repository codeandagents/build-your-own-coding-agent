"""Medicines and supplies in stock (data/stock.json)."""
import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .errors import ValidationError

LOCATIONS = ("pharmacy", "surgery", "front desk")


@dataclass
class Batch:
    quantity: int
    expiry: date | None = None  # None: doesn't expire
    recalled: bool = False      # the supplier recalled it: it stays on the shelf until collected, unused


@dataclass
class StockItem:
    code: str
    name: str
    reorder_level: int
    batches: list[Batch] = field(default_factory=list)
    location: str = "pharmacy"
    discontinued: bool = False  # no longer ordered; used up and then removed from the file
    on_order: int = 0           # units ordered from the supplier and not delivered yet
    pack_size: int = 1          # the supplier sells it in packs of this many units

    def total(self) -> int:
        return sum(b.quantity for b in self.batches)

    def dispense(self, quantity: int) -> None:
        """Take units from the batches that expire first (never from a recalled batch)."""
        available = sum(b.quantity for b in self.batches if not b.recalled)
        if quantity > available:
            raise ValidationError(f"quantity: only {available} {self.code} in stock")
        for batch in sorted((b for b in self.batches if not b.recalled), key=lambda b: b.expiry or date.max):
            taken = min(batch.quantity, quantity)
            batch.quantity -= taken
            quantity -= taken
        self.batches = [b for b in self.batches if b.quantity]

    def receive(self, quantity: int, expiry: date | None = None) -> None:
        """A delivery: a new batch, and that many fewer units on order."""
        if quantity < 1:
            raise ValidationError("quantity: must be at least 1")
        self.batches.append(Batch(quantity, expiry))
        self.on_order = max(0, self.on_order - quantity)


def load_stock(path: str | Path) -> dict[str, StockItem]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    items = {}
    for item in data["items"]:
        batches = [Batch(b["quantity"], date.fromisoformat(b["expiry"]) if b.get("expiry") else None,
                         b.get("recalled", False)) for b in item["batches"]]
        location = item.get("location", "pharmacy")
        if location not in LOCATIONS:
            raise ValidationError(f"location: {item['code']} is in {location!r}")
        items[item["code"]] = StockItem(item["code"], item["name"], item["reorder_level"], batches, location,
                                        item.get("discontinued", False), item.get("on_order", 0),
                                        item.get("pack_size", 1))
    return items


def save_stock(items: dict[str, StockItem], path: str | Path) -> None:
    rows = []
    for item in items.values():
        row = {"code": item.code, "name": item.name, "reorder_level": item.reorder_level,
               "batches": [{"quantity": b.quantity, **({"expiry": b.expiry.isoformat()} if b.expiry else {}),
                            **({"recalled": True} if b.recalled else {})} for b in item.batches]}
        if item.location != "pharmacy":
            row["location"] = item.location
        if item.discontinued:
            row["discontinued"] = True
        if item.on_order:
            row["on_order"] = item.on_order
        if item.pack_size != 1:
            row["pack_size"] = item.pack_size
        rows.append(row)
    Path(path).write_text(json.dumps({"items": rows}, indent=2) + "\n", encoding="utf-8")
