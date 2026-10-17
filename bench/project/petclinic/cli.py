"""Command line for the front desk: python -m petclinic [--data clinic.json] <command>.

Every command loads the data file, does one thing, and saves the file if it changed something. Errors in what
the user typed (ValidationError) are printed as "error: ..." with exit code 2, never as a traceback."""
import argparse
import logging
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from . import admin, archive, audit, settings
from .billing import consultation_invoice, format_invoice
from .billing.fees import load_fees, parse_extra
from .billing.payments import amount_due, take_payment
from .billing.statements import format_statement, statement
from .billing.takings import format_takings, takings
from .booking import available
from .errors import ValidationError
from .exporter import export_month
from .importer import import_csv
from .money import money
from .notifications import is_mobile, overdue_text, reminder_text
from .periods import Period
from .reports import format_table, visit_rows
from .scheduling import clinic_now, clinic_today, next_free_slot, parse_start
from .search import describe, search
from .staff import back_at_work, load_staff, on_duty
from .store import Store
from .vaccinations import due_within, overdue


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="petclinic")
    p.add_argument("--data", default=settings.DATA_FILE, help="the clinic's data file")
    commands = p.add_subparsers(dest="command", required=True)

    # clients
    commands.add_parser("owners", help="list owners")
    owner = commands.add_parser("owner", help="one owner: details, pets and recent visits")
    owner.add_argument("owner_id", type=int)
    add_owner = commands.add_parser("add-owner", help="register a new owner")
    add_owner.add_argument("name")
    add_owner.add_argument("number", help="phone number")
    add_owner.add_argument("--email", default="")
    add_pet = commands.add_parser("add-pet", help="register a pet")
    add_pet.add_argument("owner_id", type=int)
    add_pet.add_argument("name")
    add_pet.add_argument("species")
    add_pet.add_argument("birth_date", type=date.fromisoformat, help="YYYY-MM-DD")
    add_pet.add_argument("--breed", default="")
    find = commands.add_parser("search", help="find owners and pets by name, number or microchip")
    find.add_argument("text")

    # visits
    report = commands.add_parser("report", help="visits since a date")
    report.add_argument("--since", type=date.fromisoformat, help="YYYY-MM-DD (default: 7 days ago)")
    report.add_argument("--until", type=date.fromisoformat, help="YYYY-MM-DD, not included (default: no end)")
    commands.add_parser("next-slot", help="the first free appointment")
    book = commands.add_parser("book", help="book a visit")
    book.add_argument("pet_id", type=int)
    book.add_argument("start", help="YYYY-MM-DD HH:MM")
    book.add_argument("reason")
    book.add_argument("--vet", type=int, help="vet id (default: any vet)")
    cancel = commands.add_parser("cancel", help="cancel a visit")
    cancel.add_argument("visit_id", type=int)
    move = commands.add_parser("reschedule", help="move a visit to another time")
    move.add_argument("visit_id", type=int)
    move.add_argument("start", help="YYYY-MM-DD HH:MM")
    online = commands.add_parser("online-slots", help="what the online booking page offers on a day")
    online.add_argument("--date", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    online.add_argument("--vet", type=int, help="only this vet's appointments")
    online.add_argument("--staff", default=settings.STAFF_FILE)

    # money
    invoice = commands.add_parser("invoice", help="the invoice for a visit")
    invoice.add_argument("visit_id", type=int)
    invoice.add_argument("--add", action="append", default=[], metavar="CODE[*QTY]",
                         help="a fee from the price list (repeatable)")
    invoice.add_argument("--fees", default=settings.FEES_FILE)
    pay = commands.add_parser("pay", help="take payment for a visit")
    pay.add_argument("visit_id", type=int)
    pay.add_argument("--method", choices=("eftpos", "credit", "cash"), required=True)
    pay.add_argument("--cents", type=int, help="part payment (default: everything due)")
    owed = commands.add_parser("statement", help="an owner's monthly statement")
    owed.add_argument("owner_id", type=int)
    owed.add_argument("--month", required=True, help="YYYY-MM")
    owed.add_argument("--on", type=date.fromisoformat, help="the statement date (default: today)")
    till = commands.add_parser("takings", help="the day's takings by payment method")
    till.add_argument("--date", type=date.fromisoformat, help="YYYY-MM-DD (default: today)")
    export = commands.add_parser("export", help="the accountant's monthly invoices CSV")
    export.add_argument("--month", required=True, help="YYYY-MM")
    export.add_argument("--out", help="file to write (default: exports/invoices-YYYY-MM.csv)")

    # texts
    reminders = commands.add_parser("reminders", help="vaccination reminder texts to send")
    reminders.add_argument("--on", type=date.fromisoformat, help="YYYY-MM-DD (default: today)")
    late = commands.add_parser("overdue", help="texts for vaccinations more than a month overdue")
    late.add_argument("--on", type=date.fromisoformat, help="YYYY-MM-DD (default: today)")

    # staff
    rota = commands.add_parser("rota", help="vets on duty")
    rota.add_argument("--date", type=date.fromisoformat, help="YYYY-MM-DD (default: today)")
    rota.add_argument("--staff", default=settings.STAFF_FILE)

    # housekeeping
    load = commands.add_parser("import", help="import a legacy CSV export")
    load.add_argument("csv")
    purge = commands.add_parser("purge", help="delete old visits")
    which = purge.add_mutually_exclusive_group(required=True)
    which.add_argument("--before", type=date.fromisoformat, help="delete visits before YYYY-MM-DD")
    which.add_argument("--all", action="store_true", help="delete every visit")
    store_away = commands.add_parser("archive", help="move old visits to the archive file")
    store_away.add_argument("--before", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    store_away.add_argument("--archive", default=settings.ARCHIVE_FILE)
    restore = commands.add_parser("restore", help="bring archived visits back")
    restore.add_argument("--pet", type=int, help="only this pet's visits")
    restore.add_argument("--archive", default=settings.ARCHIVE_FILE)
    merge_owners = commands.add_parser("merge-owners", help="merge a duplicate owner into the original")
    merge_owners.add_argument("keep_id", type=int)
    merge_owners.add_argument("duplicate_id", type=int)
    merge_pets = commands.add_parser("merge-pets", help="merge a duplicate pet into the original")
    merge_pets.add_argument("keep_id", type=int)
    merge_pets.add_argument("duplicate_id", type=int)
    trail = commands.add_parser("audit", help="who changed what")
    trail.add_argument("--since", type=date.fromisoformat, help="YYYY-MM-DD")
    trail.add_argument("--who", help="import, admin, archive, front desk, ...")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    store = Store.load(args.data)
    try:
        changed = run(args, store)
    except ValidationError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if changed:
        store.save()
    return 0


def run(args, store: Store) -> bool:
    """Run one command. Returns True if the data file must be saved."""
    command = args.command
    if command == "owners":
        for o in sorted(store.owners.values(), key=lambda o: o.name):
            print(f"{o.id:3}  {o.name:20}  {o.telephone}")
    elif command == "owner":
        print_owner(store, args.owner_id)
    elif command == "add-owner":
        o = store.add_owner(args.name, args.number, args.email)
        audit.record(store, "front desk", f"owner {o.id} added: {o.name!r} ({o.telephone})")
        print(f"Owner {o.id} added: {o.name}")
        return True
    elif command == "add-pet":
        pet = store.add_pet(args.owner_id, args.name, args.species, args.birth_date, args.breed)
        audit.record(store, "front desk", f"pet {pet.id} added: {pet.name} ({pet.species}) for owner {pet.owner_id}")
        print(f"Pet {pet.id} added: {pet.name}")
        return True
    elif command == "search":
        hits = search(store, args.text)
        print("\n".join(describe(store, hit) for hit in hits) if hits else "Nothing found.")
    elif command == "report":
        since = args.since or clinic_today() - timedelta(days=7)
        print(format_table(visit_rows(store, since, args.until)))
    elif command == "next-slot":
        slot = next_free_slot([v.start for v in store.visits.values()], datetime.now(timezone.utc))
        print(slot.strftime("%Y-%m-%d %H:%M") if slot else "No free slot in the next 14 days.")
    elif command == "book":
        visit = store.book_visit(args.pet_id, parse_start(args.start), args.reason, args.vet)
        audit.record(store, "front desk", f"visit {visit.id} booked for pet {visit.pet_id} at {visit.start}")
        print(f"Visit {visit.id} booked: {visit.start:%a %d %b %H:%M}")
        return True
    elif command == "cancel":
        visit = store.cancel_visit(args.visit_id)
        audit.record(store, "front desk", f"visit {visit.id} cancelled")
        print(f"Visit {visit.id} cancelled")
        return True
    elif command == "reschedule":
        visit = store.reschedule_visit(args.visit_id, parse_start(args.start))
        audit.record(store, "front desk", f"visit {visit.id} moved to {visit.start}")
        print(f"Visit {visit.id} moved to {visit.start:%a %d %b %H:%M}")
        return True
    elif command == "online-slots":
        vets, leave = load_staff(args.staff)
        offer = available(store, args.date, vets, leave, args.vet)
        if not offer.times:
            print(f"Nothing free on {args.date:%a %d %b}.")
        else:
            print(f"{args.date:%a %d %b} with {', '.join(v.name for v in offer.vets)}:")
            print("  " + " ".join(t.strftime("%H:%M") for t in offer.times))
    elif command == "invoice":
        fees = load_fees(args.fees) if args.add else {}
        extras = [parse_extra(text, fees) for text in args.add]
        print(format_invoice(consultation_invoice(store, store.visit(args.visit_id).id, extras)))
    elif command == "pay":
        payment = take_payment(store, args.visit_id, args.method, clinic_now(), args.cents)
        audit.record(store, "front desk", f"payment {payment.id}: {money(payment.cents)} for visit {args.visit_id}")
        left = amount_due(store, args.visit_id)
        print(f"Paid {money(payment.cents)} by {args.method}." + (f" Still due: {money(left)}" if left > 0 else ""))
        return True
    elif command == "statement":
        s = statement(store, store.owner(args.owner_id).id, Period.parse_month(args.month), args.on or clinic_today())
        print(format_statement(store, s))
    elif command == "takings":
        day = args.date or clinic_today()
        print(format_takings(day, takings(store, day)))
    elif command == "export":
        period = Period.parse_month(args.month)
        out = Path(args.out or f"exports/invoices-{args.month}.csv")
        out.parent.mkdir(parents=True, exist_ok=True)
        print(f"{export_month(store, period, out)} invoices written to {out.as_posix()}")
    elif command == "reminders":
        print_reminders(store, args.on or clinic_today())
    elif command == "overdue":
        print_overdue(store, args.on or clinic_today())
    elif command == "rota":
        vets, leave = load_staff(args.staff)
        day = args.date or clinic_today()
        working = on_duty(day, vets, leave)
        print(f"On duty {day:%a %d %b}: " + (", ".join(v.name for v in working) or "nobody"))
        for vet in vets:
            if vet.active and vet not in working and day.weekday() < 5:
                print(f"  {vet.name} is away, back {back_at_work(vet, day, leave):%a %d %b}")
    elif command == "import":
        Path("logs").mkdir(exist_ok=True)
        log_file = Path("logs") / f"import-{clinic_today()}.log"
        logging.basicConfig(filename=log_file, level=logging.INFO, force=True,
                            format="%(asctime)s %(levelname)s %(name)s: %(message)s")
        result = import_csv(store, args.csv)
        print(f"{result.pets_added} pets and {result.owners_added} owners added, "
              f"{result.skipped} rows skipped (log: {log_file.as_posix()})")
        return True
    elif command == "purge":
        gone = store.purge_visits(None if args.all else args.before)
        audit.record(store, "front desk", f"{gone} visits purged")
        print(f"{gone} visits deleted")
        return True
    elif command == "archive":
        print(f"{archive.archive_visits(store, args.before, args.archive)} visits archived")
        return True
    elif command == "restore":
        print(f"{archive.restore_visits(store, args.archive, args.pet)} visits restored")
        return True
    elif command == "merge-owners":
        for line in admin.merge_owners(store, args.keep_id, args.duplicate_id):
            print(line)
        print(f"Owner {args.duplicate_id} merged into owner {args.keep_id}")
        return True
    elif command == "merge-pets":
        moved = admin.merge_pets(store, args.keep_id, args.duplicate_id)
        print(f"Pet {args.duplicate_id} merged into pet {args.keep_id} ({moved} visits moved)")
        return True
    elif command == "audit":
        since = datetime.combine(args.since, datetime.min.time()) if args.since else None
        print("\n".join(audit.entries(store, since, args.who)) or "No changes recorded.")
    return False


def print_owner(store: Store, owner_id: int) -> None:
    o = store.owner(owner_id)
    print(f"{o.name} ({o.telephone}{', ' + o.email if o.email else ''})" + (f", {o.insurer} member" if o.insurer else ""))
    for pet in sorted(store.pets_of(o.id), key=lambda p: p.name):
        visits = store.visits_for_pet(pet.id)
        last = f", last visit {visits[-1].start:%d %b %Y}" if visits else ""
        print(f"  {pet.id:4}  {pet.name} ({pet.species}{', ' + pet.breed if pet.breed else ''}), "
              f"born {pet.birth_date:%d %b %Y}{last}")


def print_reminders(store: Store, on: date) -> None:
    """One text per owner, covering all their pets' doses due in the reminder window."""
    by_owner: dict[int, list] = {}
    for pet, vaccine, due in due_within(store, on, settings.REMINDER_WINDOW_DAYS):
        by_owner.setdefault(pet.owner_id, []).append((pet, vaccine, due))
    for owner_id, items in sorted(by_owner.items()):
        owner = store.owners[owner_id]
        number = owner.telephone
        if not is_mobile(number):
            print(f"(no mobile number for {owner.name})")
            continue
        pets = sorted({pet.name for pet, _, _ in items})
        print(f"{number}: " + reminder_text(owner.name, pets, [v for _, v, _ in items], min(d for *_, d in items)))


def print_overdue(store: Store, on: date) -> None:
    """One text per owner whose pets have doses more than OVERDUE_AFTER_DAYS late."""
    by_owner: dict[int, list] = {}
    for pet, vaccine, due in overdue(store, on, settings.OVERDUE_AFTER_DAYS):
        by_owner.setdefault(pet.owner_id, []).append((pet, vaccine, due))
    for owner_id, items in sorted(by_owner.items()):
        owner = store.owners[owner_id]
        if not is_mobile(owner.telephone):
            print(f"(no mobile number for {owner.name})")
            continue
        pets = sorted({pet.name for pet, _, _ in items})
        print(f"{owner.telephone}: " + overdue_text(owner.name, pets, [v for _, v, _ in items],
                                                    min(d for *_, d in items)))
