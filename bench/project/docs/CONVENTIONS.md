# House rules for PetClinic Lite

Every change follows these rules. Code review rejects a change that breaks one.

## Errors

- Bad input raises `errors.ValidationError` (or `errors.NotFound` for a missing record). The message starts with
  the field's name and a colon: `ValidationError("birth_date: must not be in the future")`.
- Don't catch an error just to hide it. Log it and skip the row (the importer), or let it reach the user: the CLI
  prints a `ValidationError` as `error: ...` and exits with code 2.

## Dates and times

- "Today" is today **at the clinic**: `scheduling.clinic_today()`. Never `date.today()` or `datetime.now()` without
  the clinic's time zone (`scheduling.CLINIC_TZ`, Pacific/Auckland). Decision 0003.
- Appointment times are clinic local time, stored without a time zone.
- Dates in the clinic's own files and on the command line are ISO: `YYYY-MM-DD`.
- Ranges of days are `periods.Period`: half-open, like `range()`. Decision 0004.

## Money

- Money is always an `int` number of cents: `8500` is $85.00. Never a `float`, never `Decimal`. Decision 0002.
- Show amounts with `money.money()`: `$1,234.56`, or `-$8.50` for a negative amount.

## Code

- Python 3.12, standard library only: **no new dependencies** (decision 0007). Third-party code we need is copied
  into `vendor/` whole and never edited.
- Logging: `log = logging.getLogger("petclinic.<module>")` at the top of the module. No `print` outside `cli.py`.
- Settings the front desk may change live in `petclinic/settings.py`. Don't change their values in a code change.
- Keep functions small and give each a docstring when what it does isn't obvious from its name.
- Every change to what a command prints goes in `docs/front-desk-guide.md` too.

## Tests

- Every change comes with tests: `tests/test_<module>.py` for `petclinic/<module>.py`.
- Run them all before you say you're done: `python -m pytest -q`. All of them must pass.
- Tests never depend on today's date: pass the date in (`on=`, `--on`, `now=`).
- Tests never read or write the live data files. Use `tests/fixtures/` (copy a fixture to `tmp_path` before a
  command that saves).
