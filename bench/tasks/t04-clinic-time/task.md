The booking server now runs in UTC. Since then, `python -m petclinic next-slot` sometimes offers an appointment
time that has already passed at the clinic in Auckland. The clinic works in its own time zone. Find the cause and
fix it.
