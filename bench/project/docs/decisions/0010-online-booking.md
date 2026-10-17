# 0010: The online booking page

**Date:** 2025-08-04. **Status:** accepted.

**Context.** Half of all bookings were phone calls during the morning rush.

**Decision.** A booking page on the clinic's website. The web host's script calls `booking.available` to show free
times (for one vet, if the client picks one) and `booking.book` to book. Only existing clients can book: the page
asks for their name, number and pet's name, and `booking.find_client` matches them. A vet on leave, or a closed day,
must never be offered.

**Consequences.** The page and the desk share the same slots; the page can't double-book. New clients still phone.
