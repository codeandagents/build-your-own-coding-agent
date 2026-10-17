from datetime import date, datetime, timezone

from petclinic.notifications import (appointment_text, can_send, cancelled_text, first_name, is_mobile, join_names,
                                     overdue_text, receipt_text, reminder_email, reminder_text, short_date, short_time)
from petclinic.scheduling import CLINIC_TZ


def test_join_names():
    assert join_names([]) == ""
    assert join_names(["Kiwi"]) == "Kiwi"
    assert join_names(["Kiwi", "Pip"]) == "Kiwi and Pip"
    assert join_names(["Kiwi", "Pip", "Rocket"]) == "Kiwi, Pip and Rocket"


def test_short_date_has_no_leading_zero():
    assert short_date(date(2026, 11, 4)) == "Wed 4 Nov"
    assert short_date(date(2026, 10, 28)) == "Wed 28 Oct"


def test_short_time():
    assert short_time(datetime(2026, 10, 22, 9, 30)) == "9:30am"
    assert short_time(datetime(2026, 10, 22, 14, 0)) == "2:00pm"
    assert short_time(datetime(2026, 10, 22, 12, 0)) == "12:00pm"


def test_first_name():
    assert first_name("Aroha Ngata") == "Aroha"


def test_mobile_numbers():
    assert is_mobile("021 555 0101")
    assert is_mobile("022-555-0142")
    assert not is_mobile("09 555 0100")  # a landline
    assert not is_mobile("02")


def test_quiet_hours_are_clinic_time():
    assert can_send(datetime(2026, 10, 21, 10, 0, tzinfo=CLINIC_TZ))
    assert not can_send(datetime(2026, 10, 21, 20, 30, tzinfo=CLINIC_TZ))
    assert not can_send(datetime(2026, 10, 21, 7, 0, tzinfo=CLINIC_TZ))
    # 21:00 UTC on 20 October is 10:00 on 21 October in Auckland
    assert can_send(datetime(2026, 10, 20, 21, 0, tzinfo=timezone.utc))


def test_reminder_names_the_pets_vaccines_and_date():
    text = reminder_text("Aroha Ngata", ["Kiwi", "Pip"], ["F3", "DHPP", "F3"], date(2026, 10, 28))
    assert "Aroha" in text and "Ngata" not in text
    assert "Kiwi and Pip are" in text
    assert "DHPP and F3" in text
    assert "Wed 28 Oct" in text


def test_reminder_email():
    subject, body = reminder_email("Mei Lin", ["Mochi"], ["FeLV"], date(2026, 10, 25))
    assert subject == "Mochi: vaccinations due on Sun 25 Oct"
    assert body.startswith("Kia ora Mei,\n")


def test_overdue_text():
    text = overdue_text("Ben Carter", ["Rocket"], ["RHDV"], date(2026, 9, 1))
    assert text.startswith("Kia ora Ben! Rocket is overdue for RHDV")
    assert "Tue 1 Sep" in text


def test_appointment_texts():
    text = appointment_text("Ben Carter", "Rocket", datetime(2026, 10, 22, 10, 30), "Dr Hine Tane")
    assert "Rocket's appointment" in text and "Thu 22 Oct at 10:30am with Dr Hine Tane" in text
    assert " with " not in appointment_text("Ben Carter", "Rocket", datetime(2026, 10, 22, 10, 30))
    assert "is cancelled" in cancelled_text("Ben Carter", "Rocket", datetime(2026, 10, 22, 10, 30))


def test_receipt_text():
    assert "$97.75" in receipt_text("Aroha Ngata", "Kiwi", 9775, date(2026, 10, 12))
