"""Online booking: what the booking page on the clinic's website offers, and the bookings it sends back.

The page asks for a day and, optionally, a vet. It shows the free appointment times for that day; a client who
picks a vet only sees that vet's days at work. A booking from the page arrives as a BookingRequest."""
import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from . import settings
from .errors import ValidationError
from .names import same_name
from .phones import same_number
from .scheduling import clinic_today, slots_for_day
from .staff import Leave, Vet, on_duty, vet_by_id

log = logging.getLogger("petclinic.booking")


@dataclass
class BookingRequest:
    owner_name: str
    telephone: str
    pet_name: str
    start: datetime
    reason: str
    vet_id: int | None = None


@dataclass
class Offer:
    day: date
    times: list[time]
    vets: list[Vet]  # the vets on duty that day (or just the one the client asked for)


def available(store, day: date, vets: list[Vet], leave: list[Leave], vet_id: int | None = None) -> Offer:
    """Free times on `day`. With `vet_id`, only if that vet is at work that day."""
    working = on_duty(day, vets, leave)
    if vet_id is not None:
        vet = vet_by_id(vets, vet_id)
        working = [v for v in working if v.id == vet.id]
    if not working:
        return Offer(day, [], [])
    taken = [v.start for v in store.visits_on(day)]
    return Offer(day, slots_for_day(day, taken), working)


def week_ahead(store, vets: list[Vet], leave: list[Leave], vet_id: int | None = None,
               today: date | None = None) -> list[Offer]:
    """The booking page's first screen: the next seven days that have something free."""
    today = today or clinic_today()
    offers = []
    for offset in range(1, settings.ONLINE_BOOKING_DAYS + 1):
        offer = available(store, today + timedelta(days=offset), vets, leave, vet_id)
        if offer.times:
            offers.append(offer)
        if len(offers) == 7:
            break
    return offers


def find_client(store, request: BookingRequest):
    """The owner and pet a request is for: same phone number and owner name, then the pet's name."""
    owner = next((o for o in store.owners.values()
                  if same_number(o.telephone, request.telephone) and same_name(o.name, request.owner_name)), None)
    if owner is None:
        raise ValidationError("telephone: no client with that name and number; new clients call the clinic")
    pet = next((p for p in store.pets_of(owner.id) if same_name(p.name, request.pet_name)), None)
    if pet is None:
        raise ValidationError(f"pet_name: {owner.name} has no pet called {request.pet_name}")
    return owner, pet


def book(store, request: BookingRequest, vets: list[Vet], leave: list[Leave]):
    """Book a request from the page. Raises ValidationError if the time or the vet isn't available any more."""
    owner, pet = find_client(store, request)
    offer = available(store, request.start.date(), vets, leave, request.vet_id)
    if request.start.time() not in offer.times:
        who = f" with {vet_by_id(vets, request.vet_id).name}" if request.vet_id else ""
        raise ValidationError(f"start: {request.start:%a %d %b %H:%M}{who} is not available")
    visit = store.book_visit(pet.id, request.start, request.reason, request.vet_id)
    log.info("online booking: visit %d for %s (%s) at %s", visit.id, pet.name, owner.name, request.start)
    return visit
