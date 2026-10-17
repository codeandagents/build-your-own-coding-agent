import json
from datetime import date

import pytest
from conftest import FIXTURES

from petclinic.errors import ValidationError
from petclinic.inventory import Batch, StockItem, load_stock, save_stock

STOCK = FIXTURES / "stock.json"


def test_load_stock():
    items = load_stock(STOCK)
    assert items["VAX-DHPP"].name == "DHPP vaccine"
    assert items["VAX-DHPP"].reorder_level == 10
    assert items["VAX-DHPP"].total() == 12
    assert items["SUP-SYR3"].batches == [Batch(450, None)]
    assert items["SUP-SYR3"].location == "surgery"
    assert items["MED-ACEP"].discontinued
    assert items["VAX-RHDV"].on_order == 10
    assert items["MED-AMOX"].pack_size == 100 and items["VAX-DHPP"].pack_size == 1
    assert [b.recalled for b in items["MED-FLEA-C"].batches] == [False, True]


def test_recalled_batches_are_never_dispensed():
    item = StockItem("MED-FLEA-C", "Flea treatment, cat", 20, [Batch(3, date(2027, 7, 31)),
                                                               Batch(12, date(2027, 5, 31), recalled=True)])
    with pytest.raises(ValidationError, match="^quantity:"):
        item.dispense(4)
    item.dispense(3)
    assert item.batches == [Batch(12, date(2027, 5, 31), recalled=True)]


def test_dispense_uses_the_batch_that_expires_first():
    item = StockItem("MED-MELOX", "Meloxicam oral 10 ml", 6,
                     [Batch(5, date(2027, 1, 31)), Batch(2, date(2026, 12, 31)), Batch(10, None)])
    item.dispense(4)
    assert item.batches == [Batch(3, date(2027, 1, 31)), Batch(10, None)]


def test_cannot_dispense_more_than_in_stock():
    item = StockItem("SUP-BAND", "Bandage 7.5 cm", 20, [Batch(3)])
    with pytest.raises(ValidationError, match="^quantity:"):
        item.dispense(4)
    assert item.total() == 3


def test_a_delivery_reduces_what_is_on_order():
    item = StockItem("VAX-RHDV", "RHDV vaccine", 4, [Batch(2, date(2026, 12, 31))], on_order=10)
    item.receive(6, date(2027, 9, 30))
    assert (item.total(), item.on_order) == (8, 4)


def test_unknown_location(tmp_path):
    path = tmp_path / "stock.json"
    path.write_text(json.dumps({"items": [{"code": "X", "name": "X", "reorder_level": 1, "batches": [],
                                           "location": "car park"}]}), encoding="utf-8")
    with pytest.raises(ValidationError, match="^location:"):
        load_stock(path)


def test_save_and_load(tmp_path):
    items = load_stock(STOCK)
    save_stock(items, tmp_path / "stock.json")
    assert load_stock(tmp_path / "stock.json") == items
