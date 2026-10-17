# Runbook: end of day

1. Take payment for every visit of the day that hasn't paid (`report --since <today>` lists them; `invoice` shows
   what's due). Clients who will pay later get a statement at month end.
2. `takings` and compare it with the EFTPOS terminal's settlement slip and the cash drawer. Credit card payments
   include the 2% surcharge: the terminal shows the same amounts.
3. If they don't match: `audit --since <today>` shows every payment taken, with its amount.
4. Lock the cash in the safe, and the drawer float stays at $200.

The terminal settles at 21:00 every day; its slip covers 21:00 to 21:00, so a payment after 21:00 shows on the next
day's slip but on today's `takings`.
