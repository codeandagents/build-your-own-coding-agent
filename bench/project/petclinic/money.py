"""Money helpers. Money is always an int number of cents (docs/CONVENTIONS.md)."""


def money(cents: int) -> str:
    """$1,234.56, or -$8.50 for a negative amount."""
    sign = "-" if cents < 0 else ""
    dollars, rest = divmod(abs(cents), 100)
    return f"{sign}${dollars:,}.{rest:02d}"


def percent_of(cents: int, percent: int) -> int:
    """`percent` per cent of an amount in cents, rounded half up to the cent."""
    return (cents * percent + 50) // 100


def parse_money(text: str) -> int:
    """"$1,234.56" or "1234.56" or "85" -> cents. No floats on the way."""
    text = text.strip().replace("$", "").replace(",", "")
    negative = text.startswith("-")
    dollars, _, cents = text.lstrip("-").partition(".")
    if not dollars.isdigit() or (cents and (not cents.isdigit() or len(cents) > 2)):
        raise ValueError(f"not an amount of money: {text!r}")
    value = int(dollars) * 100 + int(cents.ljust(2, "0") or 0)
    return -value if negative else value


def split_evenly(cents: int, parts: int) -> list[int]:
    """Split an amount into `parts` amounts that add up to it exactly; the first ones get the odd cents."""
    base, extra = divmod(cents, parts)
    return [base + (1 if i < extra else 0) for i in range(parts)]
