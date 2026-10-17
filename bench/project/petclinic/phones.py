"""New Zealand phone numbers, as the front desk types them: "021 555 0101", "022-555-0142", "09 555 0100"."""
import re


def digits(number: str) -> str:
    return re.sub(r"\D", "", number)


def looks_valid(number: str) -> bool:
    """Digits, spaces and dashes only, and at least one digit."""
    return bool(digits(number)) and number.replace(" ", "").replace("-", "").isdigit()


def is_mobile(number: str) -> bool:
    """New Zealand mobile numbers start with 02 and have 9 to 11 digits."""
    d = digits(number)
    return d.startswith("02") and 9 <= len(d) <= 11


def is_landline(number: str) -> bool:
    """Landlines: an area code 03, 04, 06, 07 or 09, then 7 digits."""
    d = digits(number)
    return len(d) == 9 and d[:2] in ("03", "04", "06", "07", "09")


def same_number(a: str, b: str) -> bool:
    """True when two numbers have the same digits: "022-555-0142" and "022 555 0142"."""
    return digits(a) == digits(b) != ""


def international(number: str) -> str:
    """+64 form for the SMS gateway: "021 555 0101" -> "+64215550101"."""
    d = digits(number)
    return "+64" + d[1:] if d.startswith("0") else "+" + d
