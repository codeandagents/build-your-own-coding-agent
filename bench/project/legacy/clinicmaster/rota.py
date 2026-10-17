"""Devonport's vet rota (ClinicMaster 4 staff module).

ClinicMaster's HR screen recorded leave as the first day away and the day the vet is back at work."""
import datetime

VETS = {"PP": "Dr Priya Patel", "SW": "Dr Sam Walker", "HT": "Dr Hine Tane", "AR": "Dr Alan Reid"}


def on_leave(day, leave_start, back_on):
    return leave_start <= day < back_on


def working(day, leave):
    """leave: {initials: [(start, back_on), ...]}"""
    if day.weekday() >= 5:
        return []
    return [name for code, name in sorted(VETS.items())
            if not any(on_leave(day, start, back) for start, back in leave.get(code, []))]


def parse_leave_line(line):
    """'PP 2019-11-04 2019-11-11' -> ('PP', start, back_on)"""
    code, start, back = line.split()
    return code, datetime.date.fromisoformat(start), datetime.date.fromisoformat(back)


def load_leave(path):
    leave = {}
    with open(path) as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                code, start, back = parse_leave_line(line)
                leave.setdefault(code, []).append((start, back))
    return leave
