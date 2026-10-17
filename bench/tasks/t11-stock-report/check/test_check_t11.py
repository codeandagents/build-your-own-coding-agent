import json
import re
from pathlib import Path

from petclinic.cli import main

PROJECT = Path(__file__).parent.parent
DATA = str(Path(__file__).parent / "fixtures" / "clinic.json")
ON = "2026-10-21"


def item(code, name, level, *batches, **more):
    return {"code": code, "name": name, "reorder_level": level,
            "batches": [{"quantity": b[0], **({"expiry": b[1]} if b[1] else {}), **({"recalled": True} if b[2:] else {})}
                        for b in batches], **more}


def stock(tmp_path, capsys, items, *extra):
    path = tmp_path / "stock.json"
    path.write_text(json.dumps({"items": items}), encoding="utf-8")
    capsys.readouterr()
    assert main(["--data", DATA, "stock", "--stock", str(path), "--on", ON, *extra]) in (0, None)
    return capsys.readouterr().out


def codes(out):
    return [row["code"] for row in json.loads(out)]


def test_at_or_below_the_reorder_level(tmp_path, capsys):
    out = stock(tmp_path, capsys, [item("BAND", "Bandage", 20, (20, None)),
                                   item("GAUZE", "Gauze swabs", 10, (5, None)),
                                   item("SYR", "Syringes", 200, (201, None))], "--json")
    assert sorted(codes(out)) == ["BAND", "GAUZE"]


def test_expired_units_dont_count(tmp_path, capsys):
    out = stock(tmp_path, capsys, [
        item("AMOX", "Amoxicillin", 100, (25, "2026-12-31"), (300, "2026-10-20")),  # 300 expired yesterday
        item("MELOX", "Meloxicam", 6, (3, "2027-01-31"), (9, "2026-10-21")),        # 9 still usable today
        item("FOREVER", "Saline", 2, (3, None)),
    ], "--json")
    assert codes(out) == ["AMOX"]


def test_recalled_batches_dont_count(tmp_path, capsys):
    out = stock(tmp_path, capsys, [item("FLEA", "Flea treatment, cat", 10, (5, "2027-07-31"), (50, "2027-05-31", True)),
                                   item("WORM", "Allwormer", 10, (40, None))], "--json")
    assert [(row["code"], row["usable"]) for row in json.loads(out)] == [("FLEA", 5)]


def test_how_many_to_order_in_whole_packs(tmp_path, capsys):
    out = stock(tmp_path, capsys, [item("SYR", "Syringes 10 ml", 100, (80, None), pack_size=50),       # 120: 3 packs
                                   item("OTIC", "Ear drops", 10, (4, None), on_order=3, pack_size=4),  # 13: 4 packs
                                   item("BAND", "Bandage", 20, (20, None))], "--json")                # 20
    assert {row["code"]: row["order"] for row in json.loads(out)} == {"SYR": 150, "OTIC": 16, "BAND": 20}


def test_units_on_order(tmp_path, capsys):
    out = stock(tmp_path, capsys, [item("RHDV", "RHDV vaccine", 10, (5, None), on_order=6),   # 11: enough coming
                                   item("GABA", "Gabapentin", 10, (5, None), on_order=5),     # 10: not above
                                   item("KC", "Kennel cough", 10, (4, None))], "--json")
    assert codes(out) == ["KC", "GABA"]


def test_discontinued_items_are_never_listed(tmp_path, capsys):
    out = stock(tmp_path, capsys, [item("ACEP", "Acepromazine", 30, (2, None), discontinued=True),
                                   item("OTIC", "Ear drops", 10, (4, None))], "--json")
    assert codes(out) == ["OTIC"]


def test_one_location(tmp_path, capsys):
    items = [item("BAND", "Bandage", 20, (3, None), location="surgery"),
             item("CONE", "Recovery cone", 5, (2, None), location="front desk"),
             item("AMOX", "Amoxicillin", 100, (25, None))]
    assert codes(stock(tmp_path, capsys, items, "--location", "surgery", "--json")) == ["BAND"]
    assert codes(stock(tmp_path, capsys, items, "--location", "pharmacy", "--json")) == ["AMOX"]
    assert codes(stock(tmp_path, capsys, items, "--location", "front desk", "--json")) == ["CONE"]
    assert codes(stock(tmp_path, capsys, items, "--location", "Surgery", "--json")) == ["BAND"]


def test_an_unknown_location_is_an_error(tmp_path, capsys):
    path = tmp_path / "stock.json"
    path.write_text(json.dumps({"items": [item("BAND", "Bandage", 20, (3, None))]}), encoding="utf-8")
    try:
        code = main(["--data", DATA, "stock", "--stock", str(path), "--on", ON, "--location", "car park"])
    except SystemExit as e:
        code = e.code
    assert code == 2
    assert "location" in capsys.readouterr().err


def test_most_urgent_first(tmp_path, capsys):
    out = stock(tmp_path, capsys, [item("BAND", "Bandage", 20, (20, None)),
                                   item("DHPP", "DHPP vaccine", 10, (8, None)),
                                   item("RHDV", "RHDV vaccine", 4, (2, None)),
                                   item("FELV", "FeLV vaccine", 6, (3, None)),
                                   item("AMOX", "Amoxicillin", 100, (25, None))], "--json")
    assert codes(out) == ["AMOX", "FELV", "RHDV", "DHPP", "BAND"]


def test_json_rows(tmp_path, capsys):
    out = stock(tmp_path, capsys, [item("DHPP", "DHPP vaccine", 10, (8, "2027-03-31"), (4, "2026-09-30"), on_order=1),
                                   item("F3", "F3 vaccine", 10, (15, "2027-06-30"))], "--json")
    assert json.loads(out) == [{"code": "DHPP", "name": "DHPP vaccine", "location": "pharmacy", "usable": 8,
                                "reorder_level": 10, "on_order": 1, "order": 11}]


def test_one_line_per_item(tmp_path, capsys):
    out = stock(tmp_path, capsys, [item("DHPP", "DHPP vaccine", 10, (8, None), on_order=2),
                                   item("AMOX", "Amoxicillin", 100, (25, None)),
                                   item("SYR", "Syringes", 200, (450, None))])
    lines = [line for line in out.splitlines() if line.strip()]
    assert [line.split()[0] for line in lines] == ["AMOX", "DHPP"]
    amox, dhpp = lines
    assert numbers_after(amox, "Amoxicillin") == [25, 100, 175]
    assert "on order" not in amox
    assert numbers_after(dhpp, "DHPP vaccine")[:3] == [8, 10, 10]
    assert dhpp.rstrip().endswith("(2 on order)")


def numbers_after(line, name):
    """The whole numbers on a line after the item's name: usable units, reorder level, how many to order, ..."""
    return [int(n) for n in re.findall(r"\d+", line[line.index(name) + len(name):])]


def test_all_stock_levels_ok(tmp_path, capsys):
    items = [item("SYR", "Syringes", 200, (450, None))]
    assert stock(tmp_path, capsys, items).strip() == "All stock levels OK."
    assert json.loads(stock(tmp_path, capsys, items, "--json")) == []


def test_the_clinics_own_stock_file_by_default(capsys, monkeypatch):
    monkeypatch.chdir(PROJECT)
    capsys.readouterr()
    main(["--data", DATA, "stock", "--on", ON, "--json"])
    assert codes(capsys.readouterr().out) == [
        "MED-OTIC", "SUP-CONE-L", "MED-MELOX", "SUP-GLOVE-M", "MED-FLEA-S", "SUP-GAUZE", "SUP-SYR10", "VAX-DHPP",
        "FOOD-RENAL", "MED-FLEA-C", "SUP-BAND"]
