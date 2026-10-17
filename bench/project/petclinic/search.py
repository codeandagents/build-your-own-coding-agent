"""The front desk's search box: one text, matched against owners' names and numbers and pets' names and chips."""
from dataclasses import dataclass

from .phones import digits


@dataclass
class Hit:
    owner_id: int
    pet_id: int | None
    why: str  # "name", "number", "pet" or "microchip"


def search(store, text: str) -> list[Hit]:
    """Owners whose name contains `text`, whose number contains its digits (at least 4), or who have a pet with
    that name or microchip. Owners in name order; one hit per owner and pet."""
    text = text.strip()
    if not text:
        return []
    wanted, number = text.casefold(), digits(text)
    hits: dict[tuple, Hit] = {}
    for owner in store.owners.values():
        if wanted in owner.name.casefold():
            hits.setdefault((owner.id, None), Hit(owner.id, None, "name"))
        elif len(number) >= 4 and number in digits(owner.telephone):
            hits.setdefault((owner.id, None), Hit(owner.id, None, "number"))
    for pet in store.pets.values():
        if wanted == pet.name.casefold():
            hits.setdefault((pet.owner_id, pet.id), Hit(pet.owner_id, pet.id, "pet"))
        elif len(number) == 15 and number == pet.microchip:
            hits.setdefault((pet.owner_id, pet.id), Hit(pet.owner_id, pet.id, "microchip"))
    return sorted(hits.values(), key=lambda h: (store.owners[h.owner_id].name.casefold(), h.pet_id or 0))


def describe(store, hit: Hit) -> str:
    owner = store.owners[hit.owner_id]
    line = f"{owner.id:4}  {owner.name:24}  {owner.telephone:14}"
    if hit.pet_id:
        pet = store.pets[hit.pet_id]
        line += f"  {pet.name} ({pet.species})"
    return line
