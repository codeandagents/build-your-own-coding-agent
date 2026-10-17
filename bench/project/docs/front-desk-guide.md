# Front-desk guide

Every command is `python -m petclinic <command>`, run in the clinic folder. Add `--data other.json` to work on
another data file (the training copy, for example). A command that changes something saves `clinic.json` and writes
a line to `logs/audit.log`.

## Clients

**`owners`**: every owner, by name, with their number.

**`owner ID`**: one owner's details, pets, and each pet's last visit.

**`add-owner NAME NUMBER [--email ADDRESS]`**: a new owner. The number takes digits, spaces and dashes.

**`add-pet OWNER_ID NAME SPECIES BIRTH_DATE [--breed BREED]`**: a new pet. Species: dog, cat, rabbit, guinea pig,
bird.

**`search TEXT`**: owners whose name contains the text, whose number contains its digits (type at least four),
or who have a pet with that name or microchip.

## Appointments

The clinic is open 9:00 to 17:00 on weekdays. Appointments are 30 minutes; the last one starts at 16:30.

**`next-slot`**: the first free appointment from now on.

**`book PET_ID "YYYY-MM-DD HH:MM" REASON [--vet ID]`**: book a visit. Without `--vet`, any vet sees the pet.

**`cancel VISIT_ID`**, **`reschedule VISIT_ID "YYYY-MM-DD HH:MM"`**.

**`online-slots --date YYYY-MM-DD [--vet ID]`**: what the online booking page offers that day. With `--vet`, only
the days that vet is at work. Use it when a client says the page won't show a time.

**`report [--since DATE] [--until DATE]`**: visits from `--since` (default: a week ago) up to, not including,
`--until`.

## Money

**`invoice VISIT_ID [--add CODE[*QTY] ...]`**: the invoice for a visit: the consultation, anything added from the
price list (`--add MED-AMOX*10`), PetCover's member discount for members, GST and the total.

**`pay VISIT_ID --method eftpos|credit|cash [--cents N]`**: take payment. Credit cards pay a 2% surcharge on top.
Without `--cents` the client pays everything due.

**`statement OWNER_ID --month YYYY-MM`**: what the owner owed at the start of the month, the month's invoices and
payments, and the balance.

**`takings [--date DATE]`**: the day's payments by method, for the cash-up (`docs/runbooks/end-of-day.md`).

**`export --month YYYY-MM`**: the accountant's CSV of the month's invoices.

## Texts

**`reminders [--on DATE]`**: one vaccination reminder text per owner whose pets have doses due in the next 14 days
(or overdue). Owners without a mobile number are listed so the desk can phone them. See
`docs/runbooks/reminders.md`.

**`overdue [--on DATE]`**: texts for doses more than 30 days late.

## The vets

**`rota [--date DATE]`**: who is on duty, and for anyone away, the day they are back.

## Housekeeping (practice manager)

**`import FILE`**: the weekly ClinicMaster export (`docs/runbooks/weekly-import.md`).

**`merge-owners KEEP DUPLICATE`**, **`merge-pets KEEP DUPLICATE`**: merge a duplicate into the original record
(`docs/runbooks/duplicates.md`).

**`archive --before DATE`**, **`restore [--pet ID]`**: the visit archive.

**`purge --before DATE`**: delete visits for good. Only for test data: real visits are archived, never purged.

**`audit [--since DATE] [--who WHO]`**: the audit trail.
