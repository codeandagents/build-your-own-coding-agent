"""Clinic settings. The front desk may change these values; a code change must not (docs/CONVENTIONS.md)."""

CLINIC_NAME = "Harbourside Vets"
CLINIC_PHONE = "09 555 0100"
CLINIC_EMAIL = "frontdesk@harbourside-vets.example"
SMS_SENDER = "HarbsideVet"       # the name texts come from (TextHub allows 11 characters)

GST_PERCENT = 15
CONSULT_CENTS = 8500             # standard consultation, GST exclusive
CARD_SURCHARGE_PERCENT = 2       # credit cards only; EFTPOS and cash pay no surcharge

QUIET_HOURS = (20, 9)            # no text messages from 20:00 until 09:00, clinic time
REMINDER_WINDOW_DAYS = 14        # remind owners about vaccinations due this many days ahead
OVERDUE_AFTER_DAYS = 30          # the overdue list: doses more than this many days late
ONLINE_BOOKING_DAYS = 28         # how far ahead the online booking page offers appointments

ALLOW_UNVERIFIED_PHONES = False  # importer: keep rows whose phone number fails validation
ARCHIVE_AFTER_YEARS = 7          # visits older than this go to the archive file (NZ record keeping)

DATA_FILE = "clinic.json"
STAFF_FILE = "data/staff.json"
STOCK_FILE = "data/stock.json"
FEES_FILE = "data/fees.json"
ARCHIVE_FILE = "data/archive.json"
