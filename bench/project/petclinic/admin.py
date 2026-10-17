"""Housekeeping the practice manager does: merging duplicate owners and pets.

Duplicates happen: a client registers online and is also typed in at the desk, or an import runs twice. Merging
keeps the original record (the one to keep) and moves everything of the duplicate onto it."""
import logging

from . import audit
from .errors import ValidationError
from .names import same_name

log = logging.getLogger("petclinic.admin")


def merge_pets(store, keep_id: int, duplicate_id: int) -> int:
    """Move the duplicate pet's visits and vaccinations to the pet to keep, then delete the duplicate.
    Returns how many visits moved."""
    keep, duplicate = store.pet(keep_id), store.pet(duplicate_id)
    if keep_id == duplicate_id:
        raise ValidationError("duplicate_id: a pet can't be merged into itself")
    if keep.species != duplicate.species:
        raise ValidationError(f"duplicate_id: {duplicate.name} is a {duplicate.species}, {keep.name} a {keep.species}")
    moved = 0
    for visit in store.visits.values():
        if visit.pet_id == duplicate_id:
            visit.pet_id = keep_id
            moved += 1
    given = {(r.vaccine, r.given) for r in store.vaccinations if r.pet_id == keep_id}
    for record in list(store.vaccinations):
        if record.pet_id == duplicate_id:
            if (record.vaccine, record.given) in given:
                store.vaccinations.remove(record)  # the same dose, recorded twice
            else:
                record.pet_id = keep_id
    if not keep.microchip and duplicate.microchip:
        keep.microchip = duplicate.microchip
    del store.pets[duplicate_id]
    audit.record(store, "admin", f"pet {duplicate_id} merged into pet {keep_id} ({moved} visits moved)")
    log.info("pet %d merged into pet %d", duplicate_id, keep_id)
    return moved


def merge_owners(store, keep_id: int, duplicate_id: int) -> list[str]:
    """Move the duplicate owner's pets to the owner to keep. A pet the kept owner already has (same name and birth
    date) is merged into theirs. Then the duplicate owner is deleted. Returns what happened, one line per pet."""
    keep, duplicate = store.owner(keep_id), store.owner(duplicate_id)
    if keep_id == duplicate_id:
        raise ValidationError("duplicate_id: an owner can't be merged into themselves")
    done = []
    for pet in store.pets_of(duplicate_id):
        twin = next((p for p in store.pets_of(keep_id)
                     if same_name(p.name, pet.name) and p.birth_date == pet.birth_date), None)
        if twin:
            merge_pets(store, twin.id, pet.id)
            done.append(f"{pet.name}: merged into pet {twin.id}")
        else:
            pet.owner_id = keep_id
            done.append(f"{pet.name}: moved")
    if not keep.email and duplicate.email:
        keep.email = duplicate.email
    del store.owners[duplicate_id]
    audit.record(store, "admin", f"owner {duplicate_id} {duplicate.name!r} merged into owner {keep_id}")
    return done


def possible_duplicates(store) -> list[tuple[int, int]]:
    """Pairs of owners (lower id first) whose names differ only in case and spacing."""
    owners = sorted(store.owners.values(), key=lambda o: o.id)
    return [(a.id, b.id) for i, a in enumerate(owners) for b in owners[i + 1:] if same_name(a.name, b.name)]
