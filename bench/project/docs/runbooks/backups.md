# Runbook: backups

- The front-desk PC copies `clinic.json`, `data/` and `logs/` to the NAS every night at 23:30, keeping 60 days.
- Before any housekeeping (merging, archiving, an import run by hand), copy `clinic.json` to
  `clinic-YYYY-MM-DD-before-<what>.json` in the same folder; delete the copy a week later.
- To restore: stop the scheduled tasks, copy the backup over `clinic.json`, run `owners` to check it loads, and
  start the tasks again. Anything done since the backup has to be typed in again: `audit` lists it.
