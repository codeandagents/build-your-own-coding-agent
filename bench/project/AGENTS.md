# Notes for coding agents

- House rules for the whole project are in `docs/CONVENTIONS.md`: errors, dates, code and tests.
- Run the tests with `python -m pytest -q` from this folder. They must all pass when you finish.
- The clinic's data is `clinic.json`; staff, stock, fees and the archive are in `data/`. Don't edit data files by
  hand: use the app's commands (`python -m petclinic --help`).
- Don't change `petclinic/settings.py` unless the task asks for it.
- `legacy/` is the old system's code and `vendor/` is third-party code: neither is part of the app.
