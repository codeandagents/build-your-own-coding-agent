# How PetClinic Lite fits together

PetClinic Lite is a command-line app. Each command (`petclinic/cli.py`) loads `clinic.json` into a `Store`, does
one thing, and saves the file if it changed anything. There is no server: the front desk's PC runs the commands,
and the online booking page calls the same code through a small script on the web host (not in this repository).

```
cli.py ──► store.py (Store: owners, pets, visits, vaccinations, payments) ◄──► clinic.json
   │           ▲
   │           ├── admin.py      merge duplicate owners and pets
   │           ├── archive.py    old visits to data/archive.json and back
   │           ├── importer.py   the weekly ClinicMaster export ──► audit.py (logs/audit.log)
   │           └── booking.py    the online booking page ──► staff.py (data/staff.json) ──► periods.py
   │
   ├── scheduling.py   opening hours, slots, clinic_today(), CLINIC_TZ
   ├── billing/        invoices.py, fees.py (data/fees.json), insurance.py, payments.py, statements.py, takings.py
   ├── money.py        money(), percent_of()
   ├── notifications.py + messages.py   the wording of every text and email
   ├── sms.py ──► vendor/texthub        sending texts, the outbox, quiet hours
   ├── vaccinations.py schedules, what's due, what's overdue
   ├── inventory.py    stock (data/stock.json)
   ├── reports.py, exporter.py, search.py
   └── names.py, phones.py, settings.py, errors.py, models.py
```

## The modules

| Module | What it does | Used by |
|---|---|---|
| `models.py` | the records: `Owner`, `Pet`, `Visit`, `Vaccination`, `Payment` | everything |
| `store.py` | `Store`: add, find, book, cancel, reschedule, purge; load and save `clinic.json` | everything |
| `scheduling.py` | opening hours (9:00-17:00, 30-minute slots, weekdays), `clinic_today()`, `next_free_slot()` | store, booking, cli |
| `periods.py` | `Period`, a half-open run of days (decision 0004) | staff, reports, statements, exporter |
| `staff.py` | vets, leave, who is on duty, when a vet is back | booking, cli (`rota`) |
| `booking.py` | what the online booking page offers, and booking from it | the web host's script, cli (`online-slots`) |
| `billing/invoices.py` | `Invoice`, `Line`, `consultation_invoice()`, `format_invoice()` | cli, statements, payments, exporter |
| `billing/fees.py` | the price list | cli (`invoice --add`) |
| `billing/insurance.py` | PetCover's member discount and claims (decision 0008) | invoices |
| `billing/payments.py` | taking payment, the card surcharge | cli (`pay`), statements, takings |
| `billing/statements.py` | monthly statements | cli (`statement`) |
| `billing/takings.py` | the day's takings for the cash-up | cli (`takings`) |
| `money.py` | `money()` for display, `percent_of()` for percentages | billing |
| `messages.py` | every text and email template | notifications |
| `notifications.py` | fills in the templates; quiet hours | cli, sms |
| `sms.py` | the outbox and TextHub | the send job (cron on the front-desk PC) |
| `vaccinations.py` | schedules per species, next dose, due and overdue lists | cli (`reminders`, `overdue`) |
| `inventory.py` | stock items, batches, dispensing | the pharmacy screen (not in this repository) |
| `importer.py` | the weekly ClinicMaster import (decision 0006) | cli (`import`) |
| `admin.py` | merging duplicates | cli (`merge-owners`, `merge-pets`) |
| `archive.py` | the visit archive (decision 0009) | cli (`archive`, `restore`) |
| `audit.py` | the audit trail | importer, admin, archive, cli |
| `reports.py` | the visit report, busiest days, species mix, vet workload | cli (`report`) |
| `exporter.py` | the accountant's monthly CSV | cli (`export`) |
| `search.py` | the search box | cli (`search`) |
| `names.py`, `phones.py` | comparing names and numbers | importer, booking, search, notifications |

## Data flow for a visit

1. Booked at the desk (`book`) or online (`booking.book`), into a free slot (`Store._check_free`).
2. On the day: the vet sees the pet; the desk prints the invoice (`invoice VISIT`, with `--add` for anything from the
   price list) and takes payment (`pay VISIT --method ...`).
3. End of day: `takings` for the cash-up.
4. Month end: `statement` for owners who owe money, `export` for the accountant.
5. After seven years: `archive` moves the visit to `data/archive.json`.

## What isn't here

The web host's booking script, the pharmacy screen and the send job's cron entry live on other machines. They only
call the functions named above.
