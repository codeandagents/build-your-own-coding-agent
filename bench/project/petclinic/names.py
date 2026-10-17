"""People's and pets' names: comparing them, and writing them in texts."""


def normalise_name(text: str) -> str:
    """Single spaces, no spaces at the ends: "  Ben   Carter " -> "Ben Carter". Case is kept."""
    return " ".join(text.split())


def same_name(a: str, b: str) -> bool:
    """True for names that differ only in case and spacing: "mei lin" and " Mei  Lin" are the same name."""
    return normalise_name(a).casefold() == normalise_name(b).casefold()


def first_name(full_name: str) -> str:
    return full_name.split()[0]


def join_names(names: list[str]) -> str:
    """Kiwi / Kiwi and Pip / Kiwi, Pip and Rocket."""
    names = list(names)
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def initials(full_name: str) -> str:
    """Dr Priya Patel -> PP (titles are skipped)."""
    words = [w for w in full_name.split() if w.rstrip(".") not in ("Dr", "Mr", "Mrs", "Ms", "Miss")]
    return "".join(w[0].upper() for w in words)
