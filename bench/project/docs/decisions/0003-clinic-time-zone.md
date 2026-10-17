# 0003: The clinic's time zone

**Date:** 2023-04-17. **Status:** accepted.

**Context.** The online booking script runs on a web host in Sydney, and the host is moving to UTC. "Today" there
isn't today in Auckland for up to 13 hours.

**Decision.** Clinic time (Pacific/Auckland, `scheduling.CLINIC_TZ`) is the only time the app knows. Code that needs
"now" takes a time-zone-aware datetime and converts it (`now.astimezone(CLINIC_TZ)`); "today" is
`scheduling.clinic_today()`. Visit times are stored as clinic local time without a time zone.

**Consequences.** Tests pass a `now` in the time zone they need. A visit at 02:30 on the night the clocks change is
ambiguous: the clinic is closed then.
