from datetime import datetime

from vendor.texthub import Client, Message, encoding_of, segments

from petclinic.scheduling import CLINIC_TZ
from petclinic.sms import Outbox, Queued, queue_for_owner, send_all

MORNING = datetime(2026, 10, 21, 10, 0, tzinfo=CLINIC_TZ)
EVENING = datetime(2026, 10, 21, 21, 0, tzinfo=CLINIC_TZ)


def test_queue_for_an_owner(tmp_path, clinic):
    outbox = Outbox(tmp_path / "outbox.json")
    queue_for_owner(outbox, clinic.owners[1], "Kia ora Aroha!")
    assert outbox.load() == [Queued("021 555 0101", "Kia ora Aroha!", 1)]


def test_quiet_hours_keep_texts_waiting(tmp_path):
    outbox = Outbox(tmp_path / "outbox.json")
    outbox.add([Queued("021 555 0101", "hello", 1)])
    assert send_all(outbox, EVENING, Client(None, dry_run=True)) == (0, 1)
    assert len(outbox.load()) == 1


def test_sending_in_the_morning(tmp_path):
    outbox = Outbox(tmp_path / "outbox.json")
    outbox.add([Queued("021 555 0101", "hello", 1), Queued("09 555 0144", "landline", 4)])
    hub = Client(None, dry_run=True)
    assert send_all(outbox, MORNING, hub) == (2, 0)
    assert [m.to for m in hub.sent] == ["+64215550101"]  # the landline is dropped
    assert outbox.load() == []


def test_segments():
    assert segments("a" * 160) == 1
    assert segments("a" * 161) == 2
    assert encoding_of("Kia ora Aroha!") == "GSM-7"
    assert encoding_of("Tēnā koe") == "UCS-2"
    assert segments("ā" * 70) == 1
    assert segments("ā" * 71) == 2


def test_long_texts_are_refused():
    result = Client(None, dry_run=True).send(Message("+64215550101", "a" * 500))
    assert not result.ok and result.segments == 4
