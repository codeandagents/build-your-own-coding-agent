# Runbook: the weekly import from Devonport

**When:** Mondays at 06:00, by the scheduled task on the front-desk PC (it runs `import` on the newest file in
`data/exports/`). The Devonport branch's ClinicMaster writes the file on Sunday night.

**What it does:** every row is a pet seen at Devonport that week, with its owner. New owners and pets are added; owners
and pets already on file are recognised (names compared without case or extra spaces) and left alone. Rows the app
can't use are skipped and logged: a number that isn't a phone number, a birth date that isn't a date, a species the
clinic doesn't treat.

**Afterwards (practice manager, Monday morning):**

1. Read the summary line in the scheduled task's email: "N pets and M owners added, K rows skipped".
2. If K isn't 0, open `logs/import-YYYY-MM-DD.log` and look at the `WARNING` lines. Phone the clients whose rows
   were skipped for a bad number, and add them by hand (`add-owner`, `add-pet`).
3. Check `audit --since <today> --who import` for anything odd: an owner added who was already a client means the
   import didn't recognise them. Merge them (`docs/runbooks/duplicates.md`) and tell the developers.

**Running it again** is safe: nothing already on file is added twice.

**Never** set `ALLOW_UNVERIFIED_PHONES` to get rows in: it adds owners with the number "0", who then get no texts.
