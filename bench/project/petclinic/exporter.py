"""The accountant's monthly export: one CSV row per invoiced visit (docs/data-formats.md, "invoices CSV")."""
import csv
from pathlib import Path

from .billing import consultation_invoice
from .periods import Period

HEADER = ["date", "visit", "owner", "pet", "subtotal_cents", "gst_cents", "total_cents"]


def invoice_rows(store, period: Period) -> list[list]:
    rows = []
    for visit in sorted(store.visits.values(), key=lambda v: v.start):
        if visit.start.date() not in period:
            continue
        invoice = consultation_invoice(store, visit.id)
        pet = store.pets[visit.pet_id]
        rows.append([visit.start.date().isoformat(), visit.id, store.owners[pet.owner_id].name, pet.name,
                     invoice.subtotal(), invoice.gst(), invoice.total()])
    return rows


def export_month(store, period: Period, path: str | Path) -> int:
    """Write the month's invoices to `path`. Returns the number of rows."""
    rows = invoice_rows(store, period)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        writer.writerows(rows)
    return len(rows)
