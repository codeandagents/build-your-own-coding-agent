"""Writes start/docs/specs/stock-report.md: the practice manager's spec for the stock command, as agreed at the review.

Background, the first draft's requirements, the October stock-take and a year of usage (tables from data/stock.json),
the developers' questions and the review meeting's minutes come first; the "Decisions" that the review added (recalled
batches, how many to order in whole packs, --location in any case) come last, after ~20,000 characters. Deterministic.
Run from the repo root: .venv/Scripts/python bench/tasks/t11-stock-report/make_spec.py"""
import json
import random
from pathlib import Path

HERE = Path(__file__).parent
PROJECT = HERE.parent.parent / "project"
MONTHS = ["Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct"]

HEAD = """# Spec: the stock report ("what do I need to order?")

**Author:** practice manager. **Status:** agreed at the review meeting on 8 October 2026. The decisions taken there
are at the end of this document and replace anything above that disagrees with them.

## Why we need it

Every Friday afternoon I walk round the pharmacy, the surgery and the front desk with a clipboard and count what we have,
then compare it with the reorder levels in my spreadsheet and phone or email the suppliers. It takes about an hour and a
half, and twice this year we still ran out of something: in March the cat flea treatment (the recall: the shelf looked
full, but most of it couldn't be sold) and in August the 10 ml syringes (we had ordered, but the order hadn't arrived and
nobody knew how many were coming). The app already knows every batch we hold, its expiry date and what's on order
(`data/stock.json`, kept up to date by the pharmacy screen), so it should be able to tell me what to order.

What I want is one command I can run on Friday that lists only the things I need to order, the most urgent first, and
that I can also send to the suppliers' portal as JSON (Rangi from IT will write that part; he needs the JSON).

## Who uses it

- Me (practice manager), every Friday, and before long weekends.
- The head nurse, for the surgery cupboard, on Monday mornings before the operating list.
- Anna at the front desk, for the retail shelf (flea treatments, wormers, diets, cones).
- Rangi's script for the suppliers' portal, once a week, with `--json`.

## What it shows (first draft, 24 September)

The command is

    python -m petclinic stock [--stock data/stock.json] [--on YYYY-MM-DD] [--json]

1. An item's usable units are the units in its batches that haven't expired. A batch is still usable on its expiry
   date and expired from the next day. A batch without an expiry date (syringes, bandages) never expires.
2. An item must be reordered when its usable units are at or below its reorder level, unless the units already on
   order (`on_order` in the stock file) would take it above its reorder level.
3. Discontinued items are never listed: we're using them up and not buying more.
4. `--on` is the day to check (default: today at the clinic); `--stock` is the stock file (default:
   `data/stock.json`).
5. Most urgent first: the smallest share of the reorder level left (usable units divided by the reorder level).
   Items with the same share are listed in order of their code.
6. One line per item: its code, its name, its usable units and its reorder level, in that order. An item with units
   on order ends its line with "(N on order)".
7. With `--json`, print a JSON array instead, one object per item in the same order, with exactly these keys:
   "code", "name", "location", "usable", "reorder_level", "on_order" (numbers as JSON numbers).
8. When nothing needs reordering, print exactly `All stock levels OK.` (with `--json`: an empty array).

## The October stock-take

This is what the clinic held on Friday 9 October, from `data/stock.json`, so you can check the report against it.

| code | item | where | reorder level | batches (units, expiry) | on order |
|---|---|---|---|---|---|
"""

QUESTIONS = """
## Questions from the developers (1 October) and my answers

**Q: Should units on order count as usable?** No. They aren't on the shelf. But if enough is already coming to take us
over the reorder level, I don't need to order it again, so don't list it (rule 2).

**Q: An item at exactly its reorder level: order or not?** Order. "At or below".

**Q: What about an expiry date of today?** Still usable today: we can use it until the end of the day.

**Q: How should the share be compared? 3 of 6 and 5 of 10 are the same share.** Then by code, as rule 5 says. Please
don't use floating point for it: two items with the same share must come out in code order every time.

**Q: Should the report say which supplier?** Not yet. The suppliers' portal knows who sells what.

**Q: Do you want a total line?** No. One line per item, nothing else, so Rangi's script can read it if it has to.

**Q: Text output format?** Whatever is readable, as long as each line has the code, the name, the usable units and the
reorder level in that order (rule 6) and the "(N on order)" ending. Nobody parses the text.

**Q: Should the report change the stock file?** Never. It only reads it.

## Review meeting, 8 October 2026: minutes

Present: practice manager, head nurse, Anna (front desk), Rangi (IT), the developers.

1. The practice manager walked through the first draft and the stock-take above. The head nurse pointed out that the
   recalled flea treatment from March is still on the front-desk shelf (12 units, waiting for the supplier to collect
   them), and in the draft's rules it counts as usable, which is exactly how we ran out last time.
2. Rangi asked whether the JSON could also say how many to order, so his script can fill in the portal's order form
   without anyone typing numbers. The practice manager said she always orders enough to get back to twice the reorder
   level. The head nurse added that most suppliers sell in packs (syringes in fifties, amoxicillin in hundreds), so
   the number has to be whole packs: the portal rejects anything else.
3. The head nurse asked for the surgery cupboard on its own, and Anna for the front-desk shelf on its own; the practice
   manager wants everything. Agreed: an option to pick one location. Anna types "Front desk" with a capital, so the
   option shouldn't care about case. A location that doesn't exist should be an error, not an empty list (an empty
   list looks like "all OK").
4. Discussed and dropped: a supplier column, a total line, emailing the report automatically.
5. The developers will build it from this spec with the decisions below, with tests, and add it to the front-desk
   guide.

## Usage over the last twelve months

Units used per month (from the pharmacy screen's dispensing log), for context. Not used by the report.

"""

DECISIONS = """
## Decisions (8 October 2026)

These replace anything above that disagrees with them.

1. **Recalled batches.** A batch marked `"recalled": true` in the stock file is never usable, whatever its expiry
   date. (Rule 1 now reads: usable units are the units in batches that haven't expired and haven't been recalled.)
2. **How many to order.** Each listed item also gets how many to order: enough units to bring its usable units plus
   the units on order up to twice its reorder level, rounded up to whole packs (the item's `pack_size` in the stock
   file; 1 if it has none).
   - In the text, it comes after the reorder level: code, name, usable units, reorder level, how many to order, in
     that order; the "(N on order)" ending stays at the end.
   - In the JSON, each object gets one more key, "order": the keys are exactly "code", "name", "location", "usable",
     "reorder_level", "on_order", "order".
3. **One location.** `--location NAME` lists only the items kept there: pharmacy, surgery or front desk, in any case
   (`Surgery` works too). Any other location is an error: the command says so and exits with code 2.

Everything else in the first draft stands.
"""


def main() -> None:
    rng = random.Random(1008)
    items = json.loads((PROJECT / "data" / "stock.json").read_text(encoding="utf-8"))["items"]
    rows = []
    for item in items:
        batches = "; ".join(f"{b['quantity']} ({b.get('expiry', 'no expiry')}{', recalled' if b.get('recalled') else ''})"
                            for b in item["batches"])
        flags = " (discontinued)" if item.get("discontinued") else ""
        rows.append(f"| {item['code']} | {item['name']}{flags} | {item['location']} | {item['reorder_level']} | "
                    f"{batches} | {item.get('on_order', 0)} |")
    usage = ["| code | " + " | ".join(MONTHS) + " | total |", "|---|" + "---|" * (len(MONTHS) + 1)]
    for item in items:
        monthly = [max(0, int(rng.gauss(item["reorder_level"] * 0.6, item["reorder_level"] * 0.25))) for _ in MONTHS]
        usage.append(f"| {item['code']} | " + " | ".join(str(n) for n in monthly) + f" | {sum(monthly)} |")
    notes = []
    for item in items:
        packs = f", sold in packs of {item['pack_size']}" if item.get("pack_size") else ""
        notes.append(f"- **{item['code']}** ({item['name']}): reorder level {item['reorder_level']}, set in "
                     f"{rng.choice(['2023', '2024', '2025'])} from the busiest month's use; supplier "
                     f"{rng.choice(['VetSupply NZ', 'Provet', 'Animates Wholesale', 'Southern Vet'])}, delivered in "
                     f"{rng.choice([2, 3, 5, 7, 10])} working days{packs}.")
    earlier = []
    for title, shift in (("Friday 11 September", 30), ("Friday 14 August", 58), ("Friday 10 July", 80)):
        earlier.append(f"\n**{title}** (my clipboard count, typed up)\n\n| code | item | where | counted | note |\n|---|---|---|---|---|")
        for item in items:
            counted = max(0, sum(b["quantity"] for b in item["batches"]) + rng.randrange(-shift // 3, shift))
            note = rng.choice(["", "", "", "ordered", "short-dated batch", "checked twice", "box opened"])
            earlier.append(f"| {item['code']} | {item['name']} | {item['location']} | {counted} | {note} |")
    text = (HEAD + "\n".join(rows) + "\n\nThe three stock-takes before it, for comparison:\n" + "\n".join(earlier) + "\n"
            + QUESTIONS + "\n".join(usage) + "\n\n## Reorder levels: where they come from\n\n" + "\n".join(notes) + "\n"
            + DECISIONS)
    out = HERE / "start" / "docs" / "specs" / "stock-report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="")
    print(f"{out.name}: {len(text):,} characters; the decisions start at {text.index('## Decisions'):,}")


if __name__ == "__main__":
    main()
