"""Periods of days (decision 0004). A Period is half-open, like range(): it runs from `start` up to, but not
including, `end`. So a month is Period(1 Oct, 1 Nov), and two periods that meet don't overlap.

Period.inclusive(first, last) builds one from a first and a last day, both included."""
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterator

from .errors import ValidationError

ONE_DAY = timedelta(days=1)


@dataclass(frozen=True)
class Period:
    start: date
    end: date  # the first day after the period

    def __post_init__(self):
        if self.end < self.start:
            raise ValidationError(f"end: {self.end} is before {self.start}")

    @classmethod
    def inclusive(cls, first: date, last: date) -> "Period":
        """The days from `first` to `last`, both included."""
        return cls(first, last + ONE_DAY)

    @classmethod
    def month(cls, year: int, month: int) -> "Period":
        start = date(year, month, 1)
        end = date(year + month // 12, month % 12 + 1, 1)
        return cls(start, end)

    @classmethod
    def parse_month(cls, text: str) -> "Period":
        """"2026-10" -> October 2026."""
        try:
            year, month = (int(part) for part in text.split("-"))
            return cls.month(year, month)
        except ValueError:
            raise ValidationError(f"month: {text!r} is not YYYY-MM") from None

    def __contains__(self, day: date) -> bool:
        return self.start <= day < self.end

    def __len__(self) -> int:
        return (self.end - self.start).days

    @property
    def last_day(self) -> date:
        return self.end - ONE_DAY

    def days(self) -> Iterator[date]:
        day = self.start
        while day < self.end:
            yield day
            day += ONE_DAY

    def weekdays(self) -> Iterator[date]:
        return (day for day in self.days() if day.weekday() < 5)

    def overlaps(self, other: "Period") -> bool:
        return self.start < other.end and other.start < self.end

    def label(self) -> str:
        """"Mon 2 Nov to Fri 6 Nov 2026" (the last day included, as people read it)."""
        last = self.last_day
        year = "" if self.start.year == last.year else f" {self.start.year}"
        return f"{self.start:%a} {self.start.day} {self.start:%b}{year} to {last:%a} {last.day} {last:%b %Y}"
