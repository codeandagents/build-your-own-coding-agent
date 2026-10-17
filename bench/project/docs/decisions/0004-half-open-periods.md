# 0004: Periods are half-open

**Date:** 2024-03-11. **Status:** accepted.

**Context.** Reports, statements and the export all select "the visits in a period", and each did it differently: the
October statement and the November one both counted visits on 1 November.

**Decision.** A run of days is a `periods.Period(start, end)`: from `start` up to, but not including, `end`, like
`range()`. A month is `Period.month(2026, 10)` = 1 October to 1 November. `report --until` is not included either.

People write ranges with the last day included ("closed from 24 to 28 December"). Data like that is converted once,
where it is read, with `Period.inclusive(first, last)`. Code never adds or subtracts a day to make a period "work".

**Consequences.** Periods that meet don't overlap, and a month's statement never double counts. `Period.label()`
prints the last day included, the way people read it.
