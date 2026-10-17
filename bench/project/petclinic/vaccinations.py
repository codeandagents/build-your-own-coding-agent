"""Vaccination schedules and what's due."""
import calendar
from datetime import date, timedelta

# months between doses, per species
SCHEDULES = {
    "dog": {"DHPP": 36, "Kennel cough": 12},
    "cat": {"F3": 36, "FeLV": 12},
    "rabbit": {"RHDV": 12},
}
FIRST_DOSE_AGE = timedelta(weeks=8)


def add_months(day: date, months: int) -> date:
    """The same day `months` later, or the month's last day when it's shorter (31 Jan + 1 month = 28/29 Feb)."""
    month = day.month - 1 + months
    year, month = day.year + month // 12, month % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def next_due(store, pet) -> dict[str, date]:
    """Each vaccine on the pet's schedule and the date its next dose is due."""
    due = {}
    for vaccine, months in SCHEDULES.get(pet.species, {}).items():
        given = [r.given for r in store.vaccinations if r.pet_id == pet.id and r.vaccine == vaccine]
        due[vaccine] = add_months(max(given), months) if given else pet.birth_date + FIRST_DOSE_AGE
    return due


def due_within(store, on: date, days: int) -> list[tuple]:
    """(pet, vaccine, due date) for doses due from `on` up to `days` later, or already overdue, by due date."""
    until = on + timedelta(days=days)
    found = [(pet, vaccine, due) for pet in store.pets.values()
             for vaccine, due in next_due(store, pet).items() if due <= until]
    return sorted(found, key=lambda item: (item[2], item[0].name, item[1]))


def overdue(store, on: date, days: int) -> list[tuple]:
    """(pet, vaccine, due date) for doses more than `days` late on `on`, most overdue first."""
    found = [(pet, vaccine, due) for pet in store.pets.values()
             for vaccine, due in next_due(store, pet).items() if (on - due).days > days]
    return sorted(found, key=lambda item: (item[2], item[0].name, item[1]))


def history(store, pet) -> list[str]:
    """"2025-10-30  Kennel cough" lines, oldest first."""
    return [f"{r.given.isoformat()}  {r.vaccine}" for r in store.vaccinations_for(pet.id)]
