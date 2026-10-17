# PetClinic Lite

The front-desk app of Harbourside Vets, a vet clinic in Auckland: owners, pets, visits, appointment slots and the
online booking page, invoices and payments, vaccination reminders, the vets' rota, stock, and the weekly import from
the Devonport branch's old system (ClinicMaster 4).

```bash
python -m petclinic owners                           # owners and their numbers
python -m petclinic search 0142                      # find an owner or pet by name, number or microchip
python -m petclinic report --since 2026-10-01        # visits since a date
python -m petclinic next-slot                        # the first free appointment
python -m petclinic book 4 "2026-10-22 10:30" "vaccination" --vet 3
python -m petclinic online-slots --date 2026-11-04   # what the online booking page offers
python -m petclinic invoice 928 --add MED-MELOX      # the invoice for a visit
python -m petclinic pay 928 --method credit          # take payment
python -m petclinic statement 1 --month 2026-10      # an owner's monthly statement
python -m petclinic takings --date 2026-10-14        # the day's takings for the cash-up
python -m petclinic reminders --on 2026-10-21        # vaccination reminder texts to send
python -m petclinic rota --date 2026-11-04           # vets on duty
python -m petclinic import data/exports/clinicmaster-2026-10-12.csv   # the weekly import
python -m petclinic merge-owners 3 51                # merge a duplicate owner into the original
python -m petclinic --help                           # everything else
python -m pytest -q                                  # the tests
```

How each command is used at the desk: `docs/front-desk-guide.md`. How the code fits together:
`docs/architecture.md`. Data files: `docs/data-formats.md`. Runbooks (weekly import, end of day, reminders,
duplicates, backups): `docs/runbooks/`. Why things are the way they are: `docs/decisions/`.

| Folder | What's in it |
|---|---|
| `petclinic/` | the app |
| `petclinic/billing/` | invoices, the price list, PetCover, payments, statements, takings |
| `tests/` | the tests; `tests/fixtures/` is a small clinic for them |
| `data/` | staff, stock, fees, the visit archive, and the weekly exports from Devonport |
| `logs/` | import logs and the audit trail (`logs/audit.log`) |
| `docs/` | guides, runbooks and decisions |
| `legacy/` | ClinicMaster 4's scripts, kept for reference (not used by the app) |
| `vendor/` | the TextHub SMS client (third-party, vendored) |

Times are the clinic's local time (Pacific/Auckland). House rules: `docs/CONVENTIONS.md`.
