"""ClinicMaster's appointment diary rules (Devonport).

Devonport opens 8:30 to 17:30 with 20-minute appointments, and closes for lunch 12:30-13:30."""
import datetime

OPEN = datetime.time(8, 30)
CLOSE = datetime.time(17, 30)
LUNCH = (datetime.time(12, 30), datetime.time(13, 30))
SLOT_MINUTES = 20


def day_slots(day):
    """Appointment start times on `day`. Closed at weekends."""
    if day.weekday() >= 5:
        return []
    slots = []
    t = datetime.datetime.combine(day, OPEN)
    close = datetime.datetime.combine(day, CLOSE)
    step = datetime.timedelta(minutes=SLOT_MINUTES)
    while t < close:
        if not (LUNCH[0] <= t.time() < LUNCH[1]):
            slots.append(t.time())
        t += step
    return slots


def free_slots(day, booked_times):
    return [s for s in day_slots(day) if s not in booked_times]


def first_free(booked, now):
    """`booked`: datetimes. `now`: the PC's local time (Devonport's PCs are on NZ time)."""
    day = now.date()
    for _ in range(14):
        taken = set(b.time() for b in booked if b.date() == day)
        for s in free_slots(day, taken):
            if day == now.date() and s <= now.time():
                continue
            return datetime.datetime.combine(day, s)
        day += datetime.timedelta(days=1)
    return None
