import pytest

from petclinic.money import money, parse_money, percent_of, split_evenly


def test_money():
    assert money(0) == "$0.00"
    assert money(100000000) == "$1,000,000.00"
    assert money(-5) == "-$0.05"


def test_percent_of():
    assert percent_of(8500, 15) == 1275
    assert percent_of(10880, 15) == 1632
    assert percent_of(10000, 2) == 200
    assert percent_of(0, 15) == 0
    assert type(percent_of(8500, 15)) is int


def test_parse_money():
    assert parse_money("$1,234.56") == 123456
    assert parse_money("85") == 8500
    assert parse_money("0.5") == 50
    assert parse_money("-8.50") == -850
    with pytest.raises(ValueError):
        parse_money("12.345")
    with pytest.raises(ValueError):
        parse_money("ten dollars")


def test_split_evenly():
    assert split_evenly(1000, 3) == [334, 333, 333]
    assert sum(split_evenly(9775, 4)) == 9775
