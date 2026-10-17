# Data formats

All files are UTF-8 JSON or CSV. Dates are ISO (`YYYY-MM-DD`), times are clinic local time without a time zone
(`YYYY-MM-DDTHH:MM`), money is integer cents.

## clinic.json

One object with five lists. `Store.save()` writes one record per line, so a diff shows exactly what changed. Optional
fields are left out when they're empty.

| List | Fields |
|---|---|
| `owners` | `id`, `name`, `telephone`, optional `email`, optional `insurer` (`"PetCover"`) |
| `pets` | `id`, `name`, `species` (lower case), `birth_date`, `owner_id`, optional `breed`, optional `microchip` (15 digits) |
| `visits` | `id`, `pet_id`, `start`, `reason`, optional `vet_id` (no vet: any vet) |
| `vaccinations` | `pet_id`, `vaccine`, `given` |
| `payments` | `id`, `visit_id`, `cents` (card surcharge included), `method` (`eftpos`, `credit`, `cash`), `paid` |

Ids are never reused while the record exists; a new record gets the highest id plus one.

## data/staff.json

```json
{"vets": [{"id": 1, "name": "Dr Priya Patel"}],
 "leave": [{"vet_id": 1, "first_day": "2026-11-02", "last_day": "2026-11-06", "note": "conference"}]}
```

`first_day` and `last_day` are the first and the last day the vet is away: both days are leave. The practice
manager exports the file from her spreadsheet, which has every vet's leave since 2019. Former vets and locums
stay in `vets` with `"active": false`.

## data/stock.json

`items`: `code`, `name`, `reorder_level`, `location` (`pharmacy`, `surgery` or `front desk`), `batches` (each a
`quantity` and an optional `expiry`; a batch without one never expires), optional `discontinued` (true: used up and
not reordered), optional `on_order` (units ordered and not delivered yet).

## data/fees.json

`fees`: `code`, `description`, `cents` (GST exclusive), `kind` (`consult`, `medicine` or `procedure`).

## data/archive.json

A list of archived visits, with the same fields as `visits` in `clinic.json` (`vet_id` may be `null`).

## data/exports/clinicmaster-YYYY-MM-DD.csv

The weekly export from ClinicMaster 4 at Devonport (`legacy/clinicmaster/export_clients.py`). Columns:
`owner_name, owner_phone, pet_name, species, birth_date, notes`. ClinicMaster copies names, numbers and dates as
they were typed at Devonport: expect any case and extra spaces in names. See `docs/runbooks/weekly-import.md`.

## Accountant's invoices CSV (`export`)

`date, visit, owner, pet, subtotal_cents, gst_cents, total_cents`: one row per visit in the month.

## logs/

- `import-YYYY-MM-DD.log`: what an import did, row by row (`INFO`) and why rows were skipped (`WARNING`).
- `audit.log`: one line per change: time, who (`import`, `admin`, `archive`, `front desk`), what.
