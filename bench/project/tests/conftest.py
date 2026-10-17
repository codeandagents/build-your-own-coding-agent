"""Shared fixtures. Tests never touch the live data files: they use a copy of tests/fixtures/clinic.json."""
import shutil
from pathlib import Path

import pytest

from petclinic.store import Store

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def clinic_file(tmp_path) -> Path:
    """A copy of the fixture clinic that the test may change and save."""
    path = tmp_path / "clinic.json"
    shutil.copy(FIXTURES / "clinic.json", path)
    return path


@pytest.fixture
def clinic(clinic_file) -> Store:
    """The fixture clinic: 5 owners, 6 pets, 8 visits, 11 vaccinations, 4 payments."""
    return Store.load(clinic_file)
