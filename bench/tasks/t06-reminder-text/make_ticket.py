"""Writes start/tickets/T-2302.md: the practice manager's ticket asking for new wording for the vaccination reminder.

Her first proposal is at the top. Two tables of segment counts (every reminder the clinic would have sent, with the
old and the proposed wording) follow, then the wording the vets agreed on 9 October, which differs from the first
proposal in two places ("call" for "ring", "Txt STOP" for "Reply STOP"). It starts after ~20,000 characters, and more
than 3,000 follow it. Deterministic. Run from the repo root: .venv/Scripts/python bench/tasks/t06-reminder-text/make_ticket.py"""
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).parent
PROJECT = HERE.parent.parent / "project"
sys.path.insert(0, str(PROJECT))

from vendor.texthub import segments  # noqa: E402

OLD = "Kia ora {o}! {p} {v} due for {x} on {d}. Book online or call Harbourside Vets on 09 555 0100."
FIRST = ('Kia ora {o}! {p} {v} due for {x} on {d}. It\'s quick to book: reply "BOOK" & we\'ll call you, or ring '
         'Harbourside Vets on 09 555 0100. Reply STOP to opt out.')
FINAL = ('Kia ora {o}! {p} {v} due for {x} on {d}. It\'s quick to book: reply "BOOK" & we\'ll call you, or call '
         'Harbourside Vets on 09 555 0100. Txt STOP to opt out.')
FIRST_TEMPLATE = ('Kia ora $owner! $pets $verb due for $vaccines on $date. It\'s quick to book: reply "BOOK" & we\'ll '
                  'call you, or ring $clinic on $phone. Reply STOP to opt out.')
FINAL_TEMPLATE = ('Kia ora $owner! $pets $verb due for $vaccines on $date. It\'s quick to book: reply "BOOK" & we\'ll '
                  'call you, or call $clinic on $phone. Txt STOP to opt out.')


def samples(rng: random.Random) -> list[tuple[str, str, str, str, str]]:
    """(owner's first name, pets, verb, vaccines, date) for every reminder the clinic would have sent this year."""
    clinic = json.loads((PROJECT / "clinic.json").read_text(encoding="utf-8"))
    pets_of: dict[int, list[str]] = {}
    for pet in clinic["pets"]:
        pets_of.setdefault(pet["owner_id"], []).append(pet["name"])
    out = []
    for owner in clinic["owners"]:
        for _ in range(rng.choice([1, 2, 3])):
            pets = rng.sample(pets_of.get(owner["id"], ["Kiwi"]), min(len(pets_of.get(owner["id"], ["Kiwi"])),
                                                                      rng.choice([1, 1, 2])))
            vaccines = rng.sample(["DHPP", "Kennel cough", "F3", "FeLV", "RHDV"], rng.choice([1, 1, 2]))
            day = date(2026, 1, 1) + timedelta(days=rng.randrange(0, 300))
            names = pets[0] if len(pets) == 1 else " and ".join(pets)
            out.append((owner["name"].split()[0], names, "is" if len(pets) == 1 else "are",
                        " and ".join(sorted(vaccines)), f"{day:%a} {day.day} {day:%b}"))
    return out


def table(rows, wording: str, title: str, full: bool = False) -> str:
    """One row per text; with `full`, the text itself too, so the vets can read what clients would get."""
    lines = [f"| # | owner | pets | due | {title} characters | segments |" + (" text |" if full else ""),
             "|---|---|---|---|---|---|" + ("---|" if full else "")]
    for i, (o, p, v, x, d) in enumerate(rows, start=1):
        text = wording.format(o=o, p=p, v=v, x=x, d=d)
        lines.append(f"| {i} | {o} | {p} | {d} | {len(text)} | {segments(text)} |" + (f" {text} |" if full else ""))
    return "\n".join(lines)


def main() -> None:
    rows = samples(random.Random(2302))
    total = lambda wording: sum(segments(wording.format(o=o, p=p, v=v, x=x, d=d)) for o, p, v, x, d in rows)  # noqa
    text = f"""# T-2302: New wording for the vaccination reminder text

**Status:** open. **Raised by:** practice manager, 5 Oct 2026. **Assigned to:** developers.

---

**Practice manager, 5 Oct 2026 08:55**

The vets want the vaccination reminder (the text the `reminders` command sends, not the overdue one) to make booking
easier: clients can now reply BOOK and Anna calls them back. Proposed wording, placeholders as now:

    {FIRST_TEMPLATE}

So Aroha's reminder for Kiwi and Pip would read:

    {FIRST.format(o="Aroha", p="Kiwi and Pip", v="are", x="DHPP and F3", d="Wed 28 Oct")}

Before we decide, I'd like to know what it does to the TextHub bill: we pay per segment.

---

**Anna (front desk), 5 Oct 2026 10:20**

Love the BOOK idea. Could the text say "call" rather than "ring"? Younger clients don't "ring" anybody.

---

**Practice manager, 6 Oct 2026 16:02**

Here's every reminder we'd have sent this year ({len(rows)} texts), with today's wording and with the proposal. Today's
wording: {total(OLD)} segments in all. Proposal: {total(FIRST)} segments.

Today's wording:

{table(rows, OLD, "today's")}

The proposal:

{table(rows, FIRST, "proposed", full=True)}

---

**Practice manager, 9 Oct 2026 12:31**

Agreed with the vets this morning: Anna's "call" instead of "ring", and "Txt STOP" instead of "Reply STOP" (TextHub
says that's what most clinics use). Final wording, please use this one and not the one at the top:

    {FINAL_TEMPLATE}

Aroha's would read:

    {FINAL.format(o="Aroha", p="Kiwi and Pip", v="are", x="DHPP and F3", d="Wed 28 Oct")}

The overdue text and the emails stay as they are.

---

**Anna (front desk), 9 Oct 2026 13:05**

Perfect, thanks. Here are the counts for the final wording, for the record ({total(FINAL)} segments in all):

{table(rows, FINAL, "final")}

---

**Practice manager, 12 Oct 2026 09:40**

Developers, this can go live whenever it's ready. The budget for the extra segments is approved.
"""
    out = HERE / "start" / "tickets" / "T-2302.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="")
    final = text.index("Agreed with the vets")
    print(f"{out.name}: {len(text):,} characters; the final wording starts at {final:,}, {len(text) - final:,} from the end")


if __name__ == "__main__":
    main()
