# Changelog

## 3.4.0 (2026-09-28)

- `search`: one box for names, numbers, pets and microchips (replaces `find-owner` and `find-pet`).
- `overdue`: texts for doses more than 30 days late, with their own wording.
- `owner ID` shows each pet's last visit.
- The audit trail records payments.

## 3.3.0 (2026-06-15)

- `statement`: the opening balance counts invoices and payments before the month, not just unpaid invoices.
- `takings` lists card surcharges separately.
- `export`: the accountant's CSV has `gst_cents` (she asked for it after the 2025-26 GST return).
- Fixed: `reschedule` to a time on another day checked the old day's slots.

## 3.2.0 (2026-03-02)

- The visit archive: `archive` and `restore` (decision 0009). 40 visits from 2017-2018 archived.
- Payments: `pay`, with the 2% credit card surcharge (decision 0002 for the rounding).
- Fixed: the weekly import added a client twice when the export had a trailing space in the name.

## 3.1.0 (2025-08-04)

- The online booking page: `booking.py`, `online-slots` (decision 0010).
- Visits can be booked with a vet (`book --vet`).
- `periods.Period` everywhere a range of days is selected (decision 0004).
- Fixed: the October statement and the November one both counted visits on 1 November.

## 3.0.0 (2025-02-24)

- `billing/` package: invoices, fees, insurance, payments, statements, takings. `petclinic.billing` still exports
  `Invoice`, `consultation_invoice`, `format_invoice` and `money`.
- The price list moved to `data/fees.json`.
- `merge-owners` and `merge-pets` (docs/runbooks/duplicates.md).

## 2.4.0 (2024-07-01)

- PetCover member discount (decision 0008).
- Texts through TextHub: `sms.py`, the outbox, quiet hours (decision 0005).

## 2.3.0 (2024-03-11)

- `rota` shows when an absent vet is back.
- `messages.py`: every text and email template in one place.
- Fixed: reminders went out at 07:00 when the PC's clock was on UTC (decision 0003).

## 2.2.0 (2023-11-06)

- Vaccination reminders: `reminders`, one text per owner.
- `report --until`.

## 2.0.0 (2023-06-12)

- The weekly import from ClinicMaster at Devonport (decision 0006).
- The audit trail (`logs/audit.log`, `audit`).

## 1.0.0 (2023-02-06)

- Harbourside moves from ClinicMaster 4 to PetClinic Lite: owners, pets, visits, invoices in integer cents, the
  appointment diary (9:00-17:00, 30-minute slots), `clinic.json` (decisions 0001, 0002, 0007).
