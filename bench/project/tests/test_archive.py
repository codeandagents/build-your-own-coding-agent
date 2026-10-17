from datetime import date

from petclinic.archive import archive_visits, archived_count, restore_visits


def test_archive_and_restore(clinic, tmp_path):
    path = tmp_path / "archive.json"
    assert archive_visits(clinic, date(2026, 10, 13), path) == 2  # visits 1 and 7
    assert sorted(clinic.visits) == [2, 3, 4, 5, 6, 8]
    assert archived_count(path) == 2
    assert restore_visits(clinic, path, pet_id=5) == 1
    assert sorted(clinic.visits) == [2, 3, 4, 5, 6, 7, 8]
    assert archived_count(path) == 1
    assert restore_visits(clinic, path) == 1
    assert sorted(clinic.visits) == [1, 2, 3, 4, 5, 6, 7, 8]
    assert archived_count(path) == 0


def test_restored_visits_keep_their_details(clinic, tmp_path):
    before = clinic.visits[1]
    archive_visits(clinic, date(2026, 10, 13), tmp_path / "archive.json")
    restore_visits(clinic, tmp_path / "archive.json")
    after = clinic.visits[1]
    assert (after.pet_id, after.start, after.reason, after.vet_id) == (before.pet_id, before.start, before.reason,
                                                                       before.vet_id)


def test_the_archive_is_recorded(clinic, tmp_path):
    from petclinic import audit
    archive_visits(clinic, date(2026, 10, 13), tmp_path / "archive.json")
    assert audit.entries(clinic, who="archive")[-1].endswith("2 visits before 2026-10-13 archived")
