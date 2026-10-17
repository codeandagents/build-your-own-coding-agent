# Runbook: duplicate owners and pets

**How to spot them:** the same client twice in `owners` (often one with odd capitals or spaces), two texts to the
same number from `reminders`, or a pet whose history is split between two records.

**Which one to keep:** the original, older record: the lower id. It has the client's history, payments and the name
as the desk typed it.

**Merging:**

```bash
python -m petclinic owners                      # find both ids
python -m petclinic merge-owners KEEP DUPLICATE # e.g. merge-owners 3 51
```

`merge-owners` moves the duplicate's pets to the owner you keep. A pet the kept owner already has (same name and birth
date) is merged into theirs, with its visits and vaccinations; the same dose recorded twice is kept once. Then the
duplicate owner is deleted.

For a pet on its own: `merge-pets KEEP DUPLICATE` (both must be the same species).

**Afterwards:** `owner KEEP` to check the pets, and find out how the duplicate got in (`audit --who import`, or
the desk). Merging fixes the records, not the cause.
