"""Writes start/tickets/T-2291.md: the accountant's ticket about GST, as the clinic's ticket system exports it.

Karen reconciled every invoice printed from July to mid-October (consultation plus what the desk added from the price
list) against her own GST: 32 are a cent low (banker's rounding on a half cent). The table makes the thread ~27,000
characters; the front desk's message after it (past the cut, with ~5,000 characters after it) reports a second,
unrelated problem: the day's takings count every card surcharge twice. Deterministic. Run from the repo root: .venv/Scripts/python bench/tasks/t07-gst-rounding/make_ticket.py"""
import json
import random
from datetime import date
from pathlib import Path

HERE = Path(__file__).parent
PROJECT = HERE.parent.parent / "project"
EXTRAS = ["MED-AMOX", "MED-CLAV", "MED-MELOX", "MED-OTIC", "MED-EYE", "MED-CHLOR", "MED-SILV", "MED-WORM", "MED-PRED",
          "MED-FLEA-S", "MED-FLEA-C", "VAX", "NAILS", "CHIP", "XRAY", "BLOODS", "DENTAL"]
COUNTED = {"MED-AMOX": 10, "MED-CLAV": 14, "MED-PRED": 20, "MED-WORM": 2}


def money(cents: int) -> str:
    return f"${cents // 100:,}.{cents % 100:02d}"


def days(rows: list[str]) -> list[tuple[str, int, int, int]]:
    """(day, sales, GST printed, GST expected) per day, from the table rows themselves."""
    out: dict[str, list[int]] = {}
    for row in rows:
        cells = [c.strip() for c in row.split("|")]
        totals = out.setdefault(cells[2], [0, 0, 0])
        for k, cell in enumerate(cells[5:8]):
            totals[k] += int(cell.replace("$", "").replace(",", "").replace(".", ""))
    return [(day, *totals) for day, totals in out.items()]


def main() -> None:
    rng = random.Random(2291)
    clinic = json.loads((PROJECT / "clinic.json").read_text(encoding="utf-8"))
    fees = {f["code"]: f for f in json.loads((PROJECT / "data" / "fees.json").read_text(encoding="utf-8"))["fees"]}
    members = {o["id"] for o in clinic["owners"] if o.get("insurer")}
    pets = {p["id"]: p for p in clinic["pets"]}
    rows, wrong = [], 0
    for visit in clinic["visits"]:
        day = date.fromisoformat(visit["start"][:10])
        if not date(2026, 7, 1) <= day <= date(2026, 10, 16) or pets[visit["pet_id"]]["owner_id"] in members:
            continue
        items, subtotal = ["Consultation"], 8500
        for code in rng.sample(EXTRAS, rng.choice([0, 1, 1, 2, 2, 3])):
            quantity = COUNTED.get(code, 1)
            items.append(fees[code]["description"].split(",")[0] + (f" x{quantity}" if quantity > 1 else ""))
            subtotal += fees[code]["cents"] * quantity
        printed, expected = round(subtotal * 15 / 100), (subtotal * 15 + 50) // 100
        wrong += printed != expected
        rows.append(f"| {visit['id']} | {day:%d %b} | {pets[visit['pet_id']]['name']} | {'; '.join(items)} | "
                    f"{money(subtotal)} | {money(printed)} | {money(expected)} | {'✗' if printed != expected else ''} |")
    example = next(r for r in rows if r.endswith("✗ |"))
    visit_id, subtotal, printed, expected = (example.split("|")[i].strip() for i in (1, 5, 6, 7))
    first = [r for r in rows if r.split("|")[2].strip().endswith(("Jul", "Aug"))]
    rest = [r for r in rows if r not in first]
    weekly = [f"| {day} | {money(s)} | {money(a)} | {money(b)} | {money(b - a)} |" for day, s, a, b in days(rows)]
    table = "| visit | date | pet | items | subtotal | your GST | my GST | |\n|---|---|---|---|---|---|---|---|\n"
    text = f"""# T-2291: GST a cent out on some invoices

**Status:** open. **Raised by:** Karen Hughes (Hughes & Co, the clinic's accountant), 14 Oct 2026.
**Assigned to:** developers.

---

**Karen Hughes, 14 Oct 2026 09:12**

Kia ora team,

I'm doing the clinic's GST return for July to October. As usual I reconcile every invoice you printed against
my own calculation (15% of the subtotal, to the nearest cent, half a cent rounds up). {wrong} of them don't match: on
each one your GST is a cent lower than mine. For example visit {visit_id}: {subtotal} subtotal, your GST {printed},
mine {expected}.

Here are July and August; the ones that don't match are marked ✗. September and October to follow. Can you find out
why and fix it before I file? The return is due on 28 October.

{table}""" + "\n".join(first) + f"""

Ngā mihi,
Karen

---

**Anna (front desk), 14 Oct 2026 11:40**

I reprinted visit {visit_id} on the desk PC and it says {printed} too, so it isn't the PDF.

---

**Karen Hughes, 14 Oct 2026 14:26**

And here are September and October (to the 16th, when I'll close the file).

{table}""" + "\n".join(rest) + f"""

---

**Anna (front desk), 15 Oct 2026 08:47**

While someone's looking at the money: the takings report doesn't match the EFTPOS terminal on days with credit
cards. Wednesday 7 October: `takings --date 2026-10-07` says credit cards $203.34, the terminal's slip says $199.42.
The difference, $3.92, is exactly that day's card surcharges, as if the app counted them twice. Same on every day with
credit card payments that I've checked; EFTPOS and cash always match. I've been correcting the cash-up sheet by hand.

---

**Karen Hughes, 15 Oct 2026 10:03**

Thanks Anna. The invoices that are out all have a subtotal where 15% ends in exactly half a cent; the others are fine.
For the record, this is my working for the return, day by day (sales are GST exclusive):

| day | sales | your GST | my GST | difference |
|---|---|---|---|---|
""" + "\n".join(weekly) + f"""

The difference is small, but the IRD wants the GST on the invoices to match the return, so I'd rather the invoices
were right than adjust the return by hand. If it can't be fixed by the 24th I'll file with my figures and note the
difference, and we'll correct the invoices in the next period. I've attached nothing else: everything is in the
tables above.

I also checked the PetCover member invoices separately. They're all fine: the member discount is rounded down as the
contract says, and the GST on the discounted subtotal matches mine on every one of them, so please leave that alone.

Ngā mihi,
Karen

---

**Practice manager, 16 Oct 2026 09:15**

Developers: please treat this as urgent; the return is due on the 28th. Karen, thanks for the detailed tables. I've
asked Anna to keep correcting the cash-up sheet by hand until the takings report is fixed.
"""
    out = HERE / "start" / "tickets" / "T-2291.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="")
    note = text.index("While someone")
    print(f"{out.name}: {len(rows)} invoices, {wrong} wrong, {len(text):,} characters; the takings note starts at "
          f"{note:,}, {len(text) - note:,} from the end")


if __name__ == "__main__":
    main()
