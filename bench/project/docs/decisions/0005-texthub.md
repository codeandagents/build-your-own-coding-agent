# 0005: Texts through TextHub

**Date:** 2023-05-29. **Status:** accepted.

**Context.** ClinicMaster sent letters. Clients asked for texts.

**Decision.** TextHub (NZ gateway, prepaid segments). Its Python client is vendored in `vendor/texthub` (decision 0007).
Texts are queued in an outbox and sent by a job at 09:00 and 13:00; nothing is sent in quiet hours (20:00-09:00).

**Consequences.** A text is billed per segment: 160 GSM characters, or 70 if the text has one character outside the
GSM alphabet (a curly quote, a macron, an emoji). The wording in `messages.py` stays in plain GSM characters.
