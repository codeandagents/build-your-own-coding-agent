"""How many SMS segments a text needs. TextHub bills per segment.

A text that uses only the GSM 03.38 alphabet is sent as GSM-7: 160 characters in one segment, 153 per segment when
it needs several. One character outside it (an emoji, a macron, a curly quote) sends the whole text as UCS-2:
70 characters in one segment, 67 per segment otherwise. Characters from the GSM extension table count twice."""

GSM_BASIC = set(
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
)
GSM_EXTENDED = set("^{}\\[~]|€\f")


def encoding_of(text: str) -> str:
    """"GSM-7" or "UCS-2"."""
    return "GSM-7" if all(c in GSM_BASIC or c in GSM_EXTENDED for c in text) else "UCS-2"


def length_in_units(text: str) -> int:
    if encoding_of(text) == "UCS-2":
        # UTF-16 code units: characters outside the BMP (most emoji) take two
        return sum(2 if ord(c) > 0xFFFF else 1 for c in text)
    return sum(2 if c in GSM_EXTENDED else 1 for c in text)


def segments(text: str) -> int:
    """The number of segments TextHub will bill for `text` (0 for an empty text)."""
    units = length_in_units(text)
    if units == 0:
        return 0
    single, multi = (160, 153) if encoding_of(text) == "GSM-7" else (70, 67)
    if units <= single:
        return 1
    return -(-units // multi)


def split(text: str) -> list[str]:
    """The parts a phone shows as one message. Only used for previews: the gateway splits for real."""
    if segments(text) <= 1:
        return [text]
    size = 153 if encoding_of(text) == "GSM-7" else 67
    parts, current, used = [], "", 0
    for c in text:
        cost = 2 if c in GSM_EXTENDED and size == 153 else 1
        if used + cost > size:
            parts.append(current)
            current, used = "", 0
        current += c
        used += cost
    return parts + [current] if current else parts
