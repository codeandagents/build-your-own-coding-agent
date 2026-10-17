"""Days the clinic is closed on a weekday, from the clinic's admin system: public holidays and training days."""
from datetime import date

CLOSURE_DAYS = {
    date(2026, 10, 26): "Labour Day",
    date(2026, 11, 18): "Staff training day",
    date(2026, 12, 25): "Christmas Day",
    date(2026, 12, 28): "Boxing Day (observed)",
    date(2027, 1, 1): "New Year's Day",
    date(2027, 1, 4): "Day after New Year's Day (observed)",
    date(2027, 2, 1): "Auckland Anniversary Day",
    date(2027, 2, 8): "Waitangi Day (observed)",
    date(2027, 3, 19): "Staff training day",
    date(2027, 3, 26): "Good Friday",
    date(2027, 3, 29): "Easter Monday",
    date(2027, 4, 26): "ANZAC Day (observed)",
    date(2027, 6, 7): "King's Birthday",
    date(2027, 6, 16): "Staff training day",
    date(2027, 6, 25): "Matariki",
    date(2027, 9, 17): "Staff training day",
    date(2027, 10, 25): "Labour Day",
    date(2027, 12, 27): "Christmas Day (observed)",
    date(2027, 12, 28): "Boxing Day (observed)",
}
