"""The clinic's records. The store (store.py) keeps them in clinic.json."""
from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class Owner:
    id: int
    name: str
    telephone: str
    email: str = ""
    insurer: str = ""     # "PetCover" for members of the clinic's insurance partner (billing/insurance.py)


@dataclass
class Pet:
    id: int
    name: str
    species: str          # lower case: dog, cat, rabbit, guinea pig, bird
    birth_date: date
    owner_id: int
    breed: str = ""
    microchip: str = ""   # 15 digits, or "" if the pet isn't chipped


@dataclass
class Visit:
    id: int
    pet_id: int
    start: datetime       # clinic local time, without a time zone
    reason: str
    vet_id: int | None = None  # None: whichever vet is free


@dataclass
class Vaccination:
    pet_id: int
    vaccine: str
    given: date


@dataclass
class Payment:
    id: int
    visit_id: int
    cents: int            # what the client paid, card surcharge included
    method: str           # eftpos, credit or cash
    paid: datetime        # clinic local time, without a time zone
