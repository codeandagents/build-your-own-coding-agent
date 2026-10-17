# Runbook: vaccination reminders

**When:** Wednesday mornings. The desk runs `reminders`, checks the list, and the send job sends the texts at 09:00
(never during quiet hours, 20:00-09:00).

**Who gets one:** every owner whose pets have a dose due in the next 14 days, or overdue. One text per owner, naming all
their pets and vaccines, with the earliest due date. Schedules (months between doses):

| Species | Vaccines |
|---|---|
| dog | DHPP every 36 months, Kennel cough every 12 |
| cat | F3 every 36 months, FeLV every 12 |
| rabbit | RHDV every 12 months |

A pet's first dose is due at 8 weeks old.

**Owners without a mobile number** are listed as "(no mobile number for ...)": phone them.

**Wording:** the texts' wording is in `petclinic/messages.py`. Changes go through the practice manager. A text
longer than 160 characters is sent as two or three (TextHub bills each one), and one emoji or macron makes every
part shorter: check with `vendor.texthub.segments()`.

**Overdue doses** (more than 30 days late) get a different text from `overdue`, sent on the first Wednesday of the
month.
