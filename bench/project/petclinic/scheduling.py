"""Opening hours and free appointment slots. All times are the clinic's local time."""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

CLINIC_TZ = ZoneInfo("Pacific/Auckland")
OPEN = time(9, 0)
CLOSE = time(17, 0)  # the last appointment starts at 16:30
SLOT = timedelta(minutes=30)


def clinic_today(now: datetime | None = None) -> date:
    """Today's date at the clinic. `now` is a time-zone-aware datetime; by default, the current time."""
    now = now or datetime.now(CLINIC_TZ)
    return now.astimezone(CLINIC_TZ).date()


def clinic_now() -> datetime:
    """The clinic's local time now, without a time zone (the way visits store it)."""
    return datetime.now(CLINIC_TZ).replace(tzinfo=None)


def is_open(day: date) -> bool:
    """Weekdays only."""
    return day.weekday() < 5


def slot_times() -> list[time]:
    """Every appointment start time in a day, open or not."""
    times, start = [], datetime.combine(date.min, OPEN)
    while start + SLOT <= datetime.combine(date.min, CLOSE):
        times.append(start.time())
        start += SLOT
    return times


def slots_for_day(day: date, taken=()) -> list[time]:
    """Free appointment start times on `day`. The clinic is closed at weekends."""
    if day.weekday() >= 5:
        return []
    taken_times = {t.time() if isinstance(t, datetime) else t for t in taken}
    slots = []
    start = datetime.combine(day, OPEN)
    end = datetime.combine(day, CLOSE)
    while start + SLOT <= end:
        if start.time() not in taken_times:
            slots.append(start.time())
        start += SLOT
    return slots


def next_free_slot(booked: list[datetime], now: datetime | None = None, days_ahead: int = 14) -> datetime | None:
    """The first free slot from now on (clinic time), or None if the next `days_ahead` days are full."""
    now = (now or datetime.now(CLINIC_TZ)).astimezone(CLINIC_TZ)
    today = clinic_today(now)
    for offset in range(days_ahead):
        day = today + timedelta(days=offset)
        taken = [b for b in booked if b.date() == day]
        for slot in slots_for_day(day, taken):
            if day == today and slot <= now.time().replace(tzinfo=None):
                continue
            return datetime.combine(day, slot)
    return None


def parse_start(text: str) -> datetime:
    """"2026-10-21 14:30" or "2026-10-21T14:30" -> a naive clinic-time datetime."""
    from .errors import ValidationError
    try:
        return datetime.fromisoformat(text.strip().replace(" ", "T", 1))
    except ValueError:
        raise ValidationError(f"start: {text!r} is not YYYY-MM-DD HH:MM") from None
