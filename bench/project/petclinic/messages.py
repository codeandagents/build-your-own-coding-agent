"""Every text and email the clinic sends, in one place so the practice manager can review the wording.

The templates are string.Template: $name or ${name} is a placeholder, filled in by notifications.py; $$ is a
literal dollar sign. Texts go out through TextHub (sms.py): keep them under 3 segments (459 characters)."""
from string import Template

# Vaccinations

VACCINE_DUE_SMS = Template("Kia ora $owner! $pets $verb due for $vaccines on $date. "
                           "Book online or call $clinic on $phone.")

VACCINE_OVERDUE_SMS = Template("Kia ora $owner! $pets $verb overdue for $vaccines (due on $date). "
                               "Book online or call $clinic on $phone.")

VACCINE_DUE_EMAIL_SUBJECT = Template("$pets: vaccinations due on $date")

VACCINE_DUE_EMAIL = Template("""\
Kia ora $owner,

$pets $verb due for $vaccines on $date.

You can book online at any time, or call us on $phone between 8:30 and 17:30, Monday to Friday.

Ngā mihi,
The team at $clinic
""")

# Appointments

APPOINTMENT_SMS = Template("Kia ora $owner! $pet's appointment at $clinic is on $date at $time${vet}. "
                           "To change it, call $phone.")

APPOINTMENT_CANCELLED_SMS = Template("Kia ora $owner. $pet's appointment on $date at $time is cancelled. "
                                     "Book online or call $clinic on $phone.")

APPOINTMENT_MOVED_SMS = Template("Kia ora $owner. $pet's appointment has moved to $date at $time. "
                                 "If that doesn't suit, call $clinic on $phone.")

# Clients

WELCOME_SMS = Template("Welcome to $clinic, $owner! Save our number: $phone. Reply STOP to opt out.")

STATEMENT_EMAIL_SUBJECT = Template("Your $clinic statement for $month")

STATEMENT_EMAIL = Template("""\
Kia ora $owner,

Your statement for $month is below. The balance to pay is $balance.

$lines

You can pay at the front desk, or by bank transfer to 12-3456-7890123-00 with your client number ($client) as the
reference. Card payments by credit card have a ${surcharge}% surcharge.

Ngā mihi,
The team at $clinic
""")

PAYMENT_RECEIPT_SMS = Template("Thanks $owner, we've received $amount for $pet's visit on $date. $clinic")

# Stock (internal emails to the practice manager)

REORDER_EMAIL_SUBJECT = Template("Stock to reorder: $count item(s)")
