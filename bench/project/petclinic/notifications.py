"""Texts and emails to owners: the wording comes from messages.py, the sending from sms.py."""
from datetime import date, datetime

from . import messages
from .money import money
from .names import first_name, join_names
from .phones import is_mobile
from .scheduling import CLINIC_TZ
from .settings import CLINIC_NAME, CLINIC_PHONE, QUIET_HOURS

__all__ = ["appointment_text", "can_send", "first_name", "is_mobile", "join_names", "overdue_text",
           "reminder_text", "short_date"]


def short_date(day: date) -> str:
    """Wed 21 Oct (no leading zero on the day)."""
    return f"{day:%a} {day.day} {day:%b}"


def short_time(moment: datetime) -> str:
    """9:30am, 2:00pm."""
    hour = moment.hour % 12 or 12
    return f"{hour}:{moment.minute:02d}{'am' if moment.hour < 12 else 'pm'}"


def _vaccine_fields(owner_name: str, pet_names: list[str], vaccines: list[str], due: date) -> dict:
    return dict(owner=first_name(owner_name), pets=join_names(pet_names),
                verb="is" if len(pet_names) == 1 else "are", vaccines=join_names(sorted(set(vaccines))),
                date=short_date(due), clinic=CLINIC_NAME, phone=CLINIC_PHONE)


def reminder_text(owner_name: str, pet_names: list[str], vaccines: list[str], due: date) -> str:
    """The vaccination reminder text: due soon."""
    return messages.VACCINE_DUE_SMS.substitute(_vaccine_fields(owner_name, pet_names, vaccines, due))


def overdue_text(owner_name: str, pet_names: list[str], vaccines: list[str], due: date) -> str:
    """The text for doses that are already late."""
    return messages.VACCINE_OVERDUE_SMS.substitute(_vaccine_fields(owner_name, pet_names, vaccines, due))


def reminder_email(owner_name: str, pet_names: list[str], vaccines: list[str], due: date) -> tuple[str, str]:
    """(subject, body) of the vaccination reminder email."""
    fields = _vaccine_fields(owner_name, pet_names, vaccines, due)
    return messages.VACCINE_DUE_EMAIL_SUBJECT.substitute(fields), messages.VACCINE_DUE_EMAIL.substitute(fields)


def appointment_text(owner_name: str, pet_name: str, start: datetime, vet_name: str = "") -> str:
    """The day-before reminder of an appointment."""
    return messages.APPOINTMENT_SMS.substitute(
        owner=first_name(owner_name), pet=pet_name, clinic=CLINIC_NAME, date=short_date(start.date()),
        time=short_time(start), vet=f" with {vet_name}" if vet_name else "", phone=CLINIC_PHONE)


def cancelled_text(owner_name: str, pet_name: str, start: datetime) -> str:
    return messages.APPOINTMENT_CANCELLED_SMS.substitute(
        owner=first_name(owner_name), pet=pet_name, date=short_date(start.date()), time=short_time(start),
        clinic=CLINIC_NAME, phone=CLINIC_PHONE)


def receipt_text(owner_name: str, pet_name: str, cents: int, day: date) -> str:
    return messages.PAYMENT_RECEIPT_SMS.substitute(owner=first_name(owner_name), amount=money(cents), pet=pet_name,
                                                   date=short_date(day), clinic=CLINIC_NAME)


def can_send(now: datetime) -> bool:
    """False during quiet hours (clinic time). `now` is time-zone aware."""
    hour = now.astimezone(CLINIC_TZ).hour
    start, end = QUIET_HOURS
    return not (hour >= start or hour < end)
