# Spec: the stock report ("what do I need to order?")

**Author:** practice manager. **Status:** agreed at the review meeting on 8 October 2026. The decisions taken there
are at the end of this document and replace anything above that disagrees with them.

## Why we need it

Every Friday afternoon I walk round the pharmacy, the surgery and the front desk with a clipboard and count what we have,
then compare it with the reorder levels in my spreadsheet and phone or email the suppliers. It takes about an hour and a
half, and twice this year we still ran out of something: in March the cat flea treatment (the recall: the shelf looked
full, but most of it couldn't be sold) and in August the 10 ml syringes (we had ordered, but the order hadn't arrived and
nobody knew how many were coming). The app already knows every batch we hold, its expiry date and what's on order
(`data/stock.json`, kept up to date by the pharmacy screen), so it should be able to tell me what to order.

What I want is one command I can run on Friday that lists only the things I need to order, the most urgent first, and
that I can also send to the suppliers' portal as JSON (Rangi from IT will write that part; he needs the JSON).

## Who uses it

- Me (practice manager), every Friday, and before long weekends.
- The head nurse, for the surgery cupboard, on Monday mornings before the operating list.
- Anna at the front desk, for the retail shelf (flea treatments, wormers, diets, cones).
- Rangi's script for the suppliers' portal, once a week, with `--json`.

## What it shows (first draft, 24 September)

The command is

    python -m petclinic stock [--stock data/stock.json] [--on YYYY-MM-DD] [--json]

1. An item's usable units are the units in its batches that haven't expired. A batch is still usable on its expiry
   date and expired from the next day. A batch without an expiry date (syringes, bandages) never expires.
2. An item must be reordered when its usable units are at or below its reorder level, unless the units already on
   order (`on_order` in the stock file) would take it above its reorder level.
3. Discontinued items are never listed: we're using them up and not buying more.
4. `--on` is the day to check (default: today at the clinic); `--stock` is the stock file (default:
   `data/stock.json`).
5. Most urgent first: the smallest share of the reorder level left (usable units divided by the reorder level).
   Items with the same share are listed in order of their code.
6. One line per item: its code, its name, its usable units and its reorder level, in that order. An item with units
   on order ends its line with "(N on order)".
7. With `--json`, print a JSON array instead, one object per item in the same order, with exactly these keys:
   "code", "name", "location", "usable", "reorder_level", "on_order" (numbers as JSON numbers).
8. When nothing needs reordering, print exactly `All stock levels OK.` (with `--json`: an empty array).

## The October stock-take

This is what the clinic held on Friday 9 October, from `data/stock.json`, so you can check the report against it.

| code | item | where | reorder level | batches (units, expiry) | on order |
|---|---|---|---|---|---|
| VAX-DHPP | DHPP vaccine | pharmacy | 10 | 8 (2027-03-31); 4 (2026-09-30) | 0 |
| VAX-F3 | F3 vaccine | pharmacy | 10 | 15 (2027-06-30) | 0 |
| VAX-FELV | FeLV vaccine | pharmacy | 6 | 9 (2027-02-28) | 0 |
| VAX-RHDV | RHDV vaccine | pharmacy | 4 | 2 (2026-12-31); 6 (2026-10-01) | 10 |
| VAX-KC | Kennel cough vaccine | pharmacy | 8 | 12 (2027-01-31) | 0 |
| MED-MELOX | Meloxicam oral 10 ml | pharmacy | 6 | 3 (2027-01-31); 2 (2026-10-10) | 0 |
| MED-AMOX | Amoxicillin 250 mg tablets | pharmacy | 100 | 120 (2026-12-31) | 0 |
| MED-CLAV | Amoxyclav 500 mg tablets | pharmacy | 60 | 40 (2027-05-31); 30 (2026-11-30) | 0 |
| MED-GABA | Gabapentin 100 mg capsules | pharmacy | 50 | 25 (2027-08-31) | 100 |
| MED-PRED | Prednisolone 5 mg tablets | pharmacy | 100 | 210 (2027-04-30) | 0 |
| MED-OTIC | Ear drops 15 ml | pharmacy | 10 | 4 (2026-12-15); 6 (2026-10-15) | 0 |
| MED-EYE | Eye ointment 5 g | pharmacy | 8 | 9 (2027-02-28) | 0 |
| MED-FLEA-S | Flea treatment, small dog | front desk | 20 | 14 (2027-09-30) | 0 |
| MED-FLEA-L | Flea treatment, large dog | front desk | 20 | 31 (2027-09-30) | 0 |
| MED-FLEA-C | Flea treatment, cat | front desk | 20 | 18 (2027-07-31); 12 (2027-05-31, recalled) | 0 |
| MED-WORM | Allwormer tablets | front desk | 40 | 55 (2028-01-31) | 0 |
| MED-ACEP | Acepromazine 10 mg tablets (discontinued) | pharmacy | 30 | 12 (2026-11-30) | 0 |
| SUP-SYR3 | Syringes 3 ml | surgery | 200 | 450 (no expiry) | 0 |
| SUP-SYR10 | Syringes 10 ml | surgery | 100 | 80 (no expiry) | 0 |
| SUP-NEED | Needles 23 G | surgery | 300 | 700 (no expiry) | 0 |
| SUP-BAND | Bandage 7.5 cm | surgery | 20 | 20 (no expiry) | 0 |
| SUP-GAUZE | Gauze swabs | surgery | 200 | 150 (no expiry) | 0 |
| SUP-GLOVE-M | Examination gloves, medium (box) | surgery | 10 | 6 (no expiry) | 0 |
| SUP-SUTURE | Sutures 3-0 | surgery | 24 | 30 (2028-06-30) | 0 |
| SUP-CONE-S | Recovery cone, small | front desk | 5 | 7 (no expiry) | 0 |
| SUP-CONE-L | Recovery cone, large | front desk | 5 | 2 (no expiry) | 0 |
| SUP-CHIP | Microchips | pharmacy | 20 | 26 (2029-03-31) | 0 |
| FOOD-RENAL | Renal diet, cat, 1.5 kg | front desk | 6 | 3 (2027-03-31); 2 (2026-10-31) | 0 |
| FOOD-GI | Gastro diet, dog, 2 kg | front desk | 6 | 8 (2027-05-31) | 0 |
| FOOD-OLD | Senior diet, dog, 3 kg (discontinued) | front desk | 4 | 1 (2026-12-31) | 0 |

The three stock-takes before it, for comparison:

**Friday 11 September** (my clipboard count, typed up)

| code | item | where | counted | note |
|---|---|---|---|---|
| VAX-DHPP | DHPP vaccine | pharmacy | 25 | short-dated batch |
| VAX-F3 | F3 vaccine | pharmacy | 40 | box opened |
| VAX-FELV | FeLV vaccine | pharmacy | 23 | short-dated batch |
| VAX-RHDV | RHDV vaccine | pharmacy | 3 | box opened |
| VAX-KC | Kennel cough vaccine | pharmacy | 34 |  |
| MED-MELOX | Meloxicam oral 10 ml | pharmacy | 12 | checked twice |
| MED-AMOX | Amoxicillin 250 mg tablets | pharmacy | 113 | checked twice |
| MED-CLAV | Amoxyclav 500 mg tablets | pharmacy | 75 |  |
| MED-GABA | Gabapentin 100 mg capsules | pharmacy | 51 |  |
| MED-PRED | Prednisolone 5 mg tablets | pharmacy | 236 | ordered |
| MED-OTIC | Ear drops 15 ml | pharmacy | 13 | ordered |
| MED-EYE | Eye ointment 5 g | pharmacy | 37 | checked twice |
| MED-FLEA-S | Flea treatment, small dog | front desk | 23 | checked twice |
| MED-FLEA-L | Flea treatment, large dog | front desk | 45 | checked twice |
| MED-FLEA-C | Flea treatment, cat | front desk | 29 | box opened |
| MED-WORM | Allwormer tablets | front desk | 78 |  |
| MED-ACEP | Acepromazine 10 mg tablets | pharmacy | 34 |  |
| SUP-SYR3 | Syringes 3 ml | surgery | 467 |  |
| SUP-SYR10 | Syringes 10 ml | surgery | 101 |  |
| SUP-NEED | Needles 23 G | surgery | 719 |  |
| SUP-BAND | Bandage 7.5 cm | surgery | 20 |  |
| SUP-GAUZE | Gauze swabs | surgery | 158 | box opened |
| SUP-GLOVE-M | Examination gloves, medium (box) | surgery | 6 | ordered |
| SUP-SUTURE | Sutures 3-0 | surgery | 51 | short-dated batch |
| SUP-CONE-S | Recovery cone, small | front desk | 31 |  |
| SUP-CONE-L | Recovery cone, large | front desk | 4 |  |
| SUP-CHIP | Microchips | pharmacy | 22 |  |
| FOOD-RENAL | Renal diet, cat, 1.5 kg | front desk | 21 | checked twice |
| FOOD-GI | Gastro diet, dog, 2 kg | front desk | 27 | ordered |
| FOOD-OLD | Senior diet, dog, 3 kg | front desk | 0 | checked twice |

**Friday 14 August** (my clipboard count, typed up)

| code | item | where | counted | note |
|---|---|---|---|---|
| VAX-DHPP | DHPP vaccine | pharmacy | 0 |  |
| VAX-F3 | F3 vaccine | pharmacy | 4 | ordered |
| VAX-FELV | FeLV vaccine | pharmacy | 22 |  |
| VAX-RHDV | RHDV vaccine | pharmacy | 29 | ordered |
| VAX-KC | Kennel cough vaccine | pharmacy | 26 | checked twice |
| MED-MELOX | Meloxicam oral 10 ml | pharmacy | 43 | ordered |
| MED-AMOX | Amoxicillin 250 mg tablets | pharmacy | 128 | short-dated batch |
| MED-CLAV | Amoxyclav 500 mg tablets | pharmacy | 77 |  |
| MED-GABA | Gabapentin 100 mg capsules | pharmacy | 28 |  |
| MED-PRED | Prednisolone 5 mg tablets | pharmacy | 230 |  |
| MED-OTIC | Ear drops 15 ml | pharmacy | 8 |  |
| MED-EYE | Eye ointment 5 g | pharmacy | 56 |  |
| MED-FLEA-S | Flea treatment, small dog | front desk | 32 | checked twice |
| MED-FLEA-L | Flea treatment, large dog | front desk | 81 | box opened |
| MED-FLEA-C | Flea treatment, cat | front desk | 40 |  |
| MED-WORM | Allwormer tablets | front desk | 84 |  |
| MED-ACEP | Acepromazine 10 mg tablets | pharmacy | 57 |  |
| SUP-SYR3 | Syringes 3 ml | surgery | 443 | box opened |
| SUP-SYR10 | Syringes 10 ml | surgery | 98 | short-dated batch |
| SUP-NEED | Needles 23 G | surgery | 709 | ordered |
| SUP-BAND | Bandage 7.5 cm | surgery | 59 | checked twice |
| SUP-GAUZE | Gauze swabs | surgery | 182 | checked twice |
| SUP-GLOVE-M | Examination gloves, medium (box) | surgery | 0 | ordered |
| SUP-SUTURE | Sutures 3-0 | surgery | 56 | box opened |
| SUP-CONE-S | Recovery cone, small | front desk | 0 |  |
| SUP-CONE-L | Recovery cone, large | front desk | 47 |  |
| SUP-CHIP | Microchips | pharmacy | 18 | ordered |
| FOOD-RENAL | Renal diet, cat, 1.5 kg | front desk | 61 | checked twice |
| FOOD-GI | Gastro diet, dog, 2 kg | front desk | 0 |  |
| FOOD-OLD | Senior diet, dog, 3 kg | front desk | 49 |  |

**Friday 10 July** (my clipboard count, typed up)

| code | item | where | counted | note |
|---|---|---|---|---|
| VAX-DHPP | DHPP vaccine | pharmacy | 1 | box opened |
| VAX-F3 | F3 vaccine | pharmacy | 91 | checked twice |
| VAX-FELV | FeLV vaccine | pharmacy | 8 |  |
| VAX-RHDV | RHDV vaccine | pharmacy | 39 | short-dated batch |
| VAX-KC | Kennel cough vaccine | pharmacy | 71 |  |
| MED-MELOX | Meloxicam oral 10 ml | pharmacy | 0 | box opened |
| MED-AMOX | Amoxicillin 250 mg tablets | pharmacy | 114 | checked twice |
| MED-CLAV | Amoxyclav 500 mg tablets | pharmacy | 83 |  |
| MED-GABA | Gabapentin 100 mg capsules | pharmacy | 24 |  |
| MED-PRED | Prednisolone 5 mg tablets | pharmacy | 285 | checked twice |
| MED-OTIC | Ear drops 15 ml | pharmacy | 12 |  |
| MED-EYE | Eye ointment 5 g | pharmacy | 42 | checked twice |
| MED-FLEA-S | Flea treatment, small dog | front desk | 5 | checked twice |
| MED-FLEA-L | Flea treatment, large dog | front desk | 103 |  |
| MED-FLEA-C | Flea treatment, cat | front desk | 19 | short-dated batch |
| MED-WORM | Allwormer tablets | front desk | 96 | short-dated batch |
| MED-ACEP | Acepromazine 10 mg tablets | pharmacy | 59 | ordered |
| SUP-SYR3 | Syringes 3 ml | surgery | 479 | box opened |
| SUP-SYR10 | Syringes 10 ml | surgery | 111 | short-dated batch |
| SUP-NEED | Needles 23 G | surgery | 767 |  |
| SUP-BAND | Bandage 7.5 cm | surgery | 39 | short-dated batch |
| SUP-GAUZE | Gauze swabs | surgery | 173 | ordered |
| SUP-GLOVE-M | Examination gloves, medium (box) | surgery | 0 | box opened |
| SUP-SUTURE | Sutures 3-0 | surgery | 74 | short-dated batch |
| SUP-CONE-S | Recovery cone, small | front desk | 33 | short-dated batch |
| SUP-CONE-L | Recovery cone, large | front desk | 46 | checked twice |
| SUP-CHIP | Microchips | pharmacy | 1 | ordered |
| FOOD-RENAL | Renal diet, cat, 1.5 kg | front desk | 76 | ordered |
| FOOD-GI | Gastro diet, dog, 2 kg | front desk | 27 | box opened |
| FOOD-OLD | Senior diet, dog, 3 kg | front desk | 0 | short-dated batch |

## Questions from the developers (1 October) and my answers

**Q: Should units on order count as usable?** No. They aren't on the shelf. But if enough is already coming to take us
over the reorder level, I don't need to order it again, so don't list it (rule 2).

**Q: An item at exactly its reorder level: order or not?** Order. "At or below".

**Q: What about an expiry date of today?** Still usable today: we can use it until the end of the day.

**Q: How should the share be compared? 3 of 6 and 5 of 10 are the same share.** Then by code, as rule 5 says. Please
don't use floating point for it: two items with the same share must come out in code order every time.

**Q: Should the report say which supplier?** Not yet. The suppliers' portal knows who sells what.

**Q: Do you want a total line?** No. One line per item, nothing else, so Rangi's script can read it if it has to.

**Q: Text output format?** Whatever is readable, as long as each line has the code, the name, the usable units and the
reorder level in that order (rule 6) and the "(N on order)" ending. Nobody parses the text.

**Q: Should the report change the stock file?** Never. It only reads it.

## Review meeting, 8 October 2026: minutes

Present: practice manager, head nurse, Anna (front desk), Rangi (IT), the developers.

1. The practice manager walked through the first draft and the stock-take above. The head nurse pointed out that the
   recalled flea treatment from March is still on the front-desk shelf (12 units, waiting for the supplier to collect
   them), and in the draft's rules it counts as usable, which is exactly how we ran out last time.
2. Rangi asked whether the JSON could also say how many to order, so his script can fill in the portal's order form
   without anyone typing numbers. The practice manager said she always orders enough to get back to twice the reorder
   level. The head nurse added that most suppliers sell in packs (syringes in fifties, amoxicillin in hundreds), so
   the number has to be whole packs: the portal rejects anything else.
3. The head nurse asked for the surgery cupboard on its own, and Anna for the front-desk shelf on its own; the practice
   manager wants everything. Agreed: an option to pick one location. Anna types "Front desk" with a capital, so the
   option shouldn't care about case. A location that doesn't exist should be an error, not an empty list (an empty
   list looks like "all OK").
4. Discussed and dropped: a supplier column, a total line, emailing the report automatically.
5. The developers will build it from this spec with the decisions below, with tests, and add it to the front-desk
   guide.

## Usage over the last twelve months

Units used per month (from the pharmacy screen's dispensing log), for context. Not used by the report.

| code | Nov | Dec | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| VAX-DHPP | 0 | 5 | 3 | 9 | 6 | 5 | 3 | 2 | 8 | 3 | 7 | 7 | 58 |
| VAX-F3 | 10 | 6 | 5 | 7 | 6 | 6 | 6 | 6 | 6 | 8 | 6 | 4 | 76 |
| VAX-FELV | 3 | 4 | 3 | 6 | 2 | 4 | 1 | 6 | 2 | 4 | 1 | 2 | 38 |
| VAX-RHDV | 1 | 0 | 1 | 1 | 1 | 3 | 2 | 2 | 3 | 2 | 1 | 3 | 20 |
| VAX-KC | 2 | 5 | 0 | 3 | 7 | 2 | 7 | 6 | 4 | 5 | 5 | 5 | 51 |
| MED-MELOX | 1 | 4 | 3 | 6 | 1 | 3 | 4 | 5 | 2 | 5 | 5 | 3 | 42 |
| MED-AMOX | 49 | 30 | 75 | 79 | 73 | 106 | 30 | 113 | 55 | 19 | 43 | 50 | 722 |
| MED-CLAV | 23 | 0 | 22 | 56 | 37 | 63 | 36 | 59 | 41 | 22 | 56 | 37 | 452 |
| MED-GABA | 36 | 41 | 32 | 38 | 25 | 16 | 32 | 33 | 43 | 22 | 21 | 9 | 348 |
| MED-PRED | 73 | 56 | 93 | 81 | 81 | 4 | 75 | 19 | 41 | 46 | 90 | 37 | 696 |
| MED-OTIC | 5 | 7 | 7 | 5 | 4 | 12 | 3 | 3 | 3 | 6 | 6 | 5 | 66 |
| MED-EYE | 0 | 7 | 6 | 6 | 3 | 4 | 5 | 5 | 8 | 6 | 4 | 7 | 61 |
| MED-FLEA-S | 12 | 8 | 11 | 16 | 18 | 19 | 17 | 18 | 13 | 16 | 18 | 10 | 176 |
| MED-FLEA-L | 13 | 11 | 10 | 4 | 12 | 18 | 10 | 8 | 12 | 11 | 12 | 15 | 136 |
| MED-FLEA-C | 10 | 16 | 8 | 12 | 14 | 14 | 17 | 13 | 9 | 7 | 16 | 6 | 142 |
| MED-WORM | 18 | 25 | 22 | 9 | 34 | 25 | 24 | 30 | 30 | 37 | 30 | 24 | 308 |
| MED-ACEP | 25 | 20 | 6 | 18 | 11 | 15 | 2 | 15 | 16 | 14 | 15 | 25 | 182 |
| SUP-SYR3 | 124 | 56 | 189 | 164 | 148 | 111 | 109 | 130 | 134 | 171 | 160 | 87 | 1583 |
| SUP-SYR10 | 72 | 63 | 52 | 76 | 79 | 96 | 32 | 36 | 30 | 20 | 100 | 62 | 718 |
| SUP-NEED | 97 | 188 | 198 | 231 | 224 | 113 | 217 | 69 | 216 | 295 | 67 | 131 | 2046 |
| SUP-BAND | 11 | 12 | 14 | 15 | 8 | 18 | 4 | 13 | 15 | 16 | 10 | 3 | 139 |
| SUP-GAUZE | 128 | 196 | 60 | 223 | 18 | 70 | 100 | 169 | 11 | 143 | 80 | 124 | 1322 |
| SUP-GLOVE-M | 8 | 0 | 8 | 2 | 2 | 2 | 8 | 4 | 4 | 5 | 5 | 4 | 52 |
| SUP-SUTURE | 6 | 12 | 8 | 6 | 26 | 3 | 15 | 6 | 25 | 10 | 18 | 23 | 158 |
| SUP-CONE-S | 3 | 1 | 1 | 1 | 3 | 3 | 3 | 3 | 4 | 1 | 3 | 1 | 27 |
| SUP-CONE-L | 2 | 1 | 2 | 1 | 3 | 3 | 2 | 4 | 2 | 3 | 0 | 1 | 24 |
| SUP-CHIP | 8 | 14 | 19 | 17 | 16 | 4 | 11 | 8 | 15 | 13 | 19 | 12 | 156 |
| FOOD-RENAL | 3 | 3 | 4 | 1 | 2 | 5 | 2 | 2 | 5 | 4 | 2 | 1 | 34 |
| FOOD-GI | 4 | 4 | 4 | 2 | 1 | 4 | 2 | 3 | 4 | 1 | 3 | 3 | 35 |
| FOOD-OLD | 1 | 1 | 1 | 3 | 2 | 2 | 1 | 1 | 0 | 3 | 2 | 3 | 20 |

## Reorder levels: where they come from

- **VAX-DHPP** (DHPP vaccine): reorder level 10, set in 2023 from the busiest month's use; supplier Provet, delivered in 10 working days.
- **VAX-F3** (F3 vaccine): reorder level 10, set in 2024 from the busiest month's use; supplier Southern Vet, delivered in 7 working days.
- **VAX-FELV** (FeLV vaccine): reorder level 6, set in 2024 from the busiest month's use; supplier Provet, delivered in 5 working days.
- **VAX-RHDV** (RHDV vaccine): reorder level 4, set in 2023 from the busiest month's use; supplier Southern Vet, delivered in 2 working days.
- **VAX-KC** (Kennel cough vaccine): reorder level 8, set in 2024 from the busiest month's use; supplier VetSupply NZ, delivered in 7 working days.
- **MED-MELOX** (Meloxicam oral 10 ml): reorder level 6, set in 2024 from the busiest month's use; supplier VetSupply NZ, delivered in 5 working days.
- **MED-AMOX** (Amoxicillin 250 mg tablets): reorder level 100, set in 2023 from the busiest month's use; supplier VetSupply NZ, delivered in 3 working days, sold in packs of 100.
- **MED-CLAV** (Amoxyclav 500 mg tablets): reorder level 60, set in 2023 from the busiest month's use; supplier Provet, delivered in 5 working days.
- **MED-GABA** (Gabapentin 100 mg capsules): reorder level 50, set in 2024 from the busiest month's use; supplier VetSupply NZ, delivered in 2 working days.
- **MED-PRED** (Prednisolone 5 mg tablets): reorder level 100, set in 2024 from the busiest month's use; supplier Provet, delivered in 5 working days.
- **MED-OTIC** (Ear drops 15 ml): reorder level 10, set in 2023 from the busiest month's use; supplier Southern Vet, delivered in 7 working days, sold in packs of 4.
- **MED-EYE** (Eye ointment 5 g): reorder level 8, set in 2024 from the busiest month's use; supplier Southern Vet, delivered in 5 working days.
- **MED-FLEA-S** (Flea treatment, small dog): reorder level 20, set in 2025 from the busiest month's use; supplier Provet, delivered in 10 working days.
- **MED-FLEA-L** (Flea treatment, large dog): reorder level 20, set in 2024 from the busiest month's use; supplier Animates Wholesale, delivered in 2 working days.
- **MED-FLEA-C** (Flea treatment, cat): reorder level 20, set in 2024 from the busiest month's use; supplier Southern Vet, delivered in 3 working days, sold in packs of 6.
- **MED-WORM** (Allwormer tablets): reorder level 40, set in 2024 from the busiest month's use; supplier VetSupply NZ, delivered in 3 working days.
- **MED-ACEP** (Acepromazine 10 mg tablets): reorder level 30, set in 2025 from the busiest month's use; supplier Provet, delivered in 5 working days.
- **SUP-SYR3** (Syringes 3 ml): reorder level 200, set in 2024 from the busiest month's use; supplier Provet, delivered in 2 working days.
- **SUP-SYR10** (Syringes 10 ml): reorder level 100, set in 2023 from the busiest month's use; supplier Provet, delivered in 2 working days, sold in packs of 50.
- **SUP-NEED** (Needles 23 G): reorder level 300, set in 2024 from the busiest month's use; supplier VetSupply NZ, delivered in 3 working days.
- **SUP-BAND** (Bandage 7.5 cm): reorder level 20, set in 2023 from the busiest month's use; supplier Animates Wholesale, delivered in 5 working days.
- **SUP-GAUZE** (Gauze swabs): reorder level 200, set in 2024 from the busiest month's use; supplier VetSupply NZ, delivered in 10 working days, sold in packs of 100.
- **SUP-GLOVE-M** (Examination gloves, medium (box)): reorder level 10, set in 2025 from the busiest month's use; supplier Animates Wholesale, delivered in 7 working days.
- **SUP-SUTURE** (Sutures 3-0): reorder level 24, set in 2025 from the busiest month's use; supplier Southern Vet, delivered in 5 working days.
- **SUP-CONE-S** (Recovery cone, small): reorder level 5, set in 2024 from the busiest month's use; supplier Animates Wholesale, delivered in 2 working days.
- **SUP-CONE-L** (Recovery cone, large): reorder level 5, set in 2023 from the busiest month's use; supplier Southern Vet, delivered in 2 working days.
- **SUP-CHIP** (Microchips): reorder level 20, set in 2023 from the busiest month's use; supplier Southern Vet, delivered in 3 working days.
- **FOOD-RENAL** (Renal diet, cat, 1.5 kg): reorder level 6, set in 2025 from the busiest month's use; supplier Animates Wholesale, delivered in 2 working days.
- **FOOD-GI** (Gastro diet, dog, 2 kg): reorder level 6, set in 2025 from the busiest month's use; supplier Animates Wholesale, delivered in 5 working days.
- **FOOD-OLD** (Senior diet, dog, 3 kg): reorder level 4, set in 2024 from the busiest month's use; supplier Animates Wholesale, delivered in 7 working days.

## Decisions (8 October 2026)

These replace anything above that disagrees with them.

1. **Recalled batches.** A batch marked `"recalled": true` in the stock file is never usable, whatever its expiry
   date. (Rule 1 now reads: usable units are the units in batches that haven't expired and haven't been recalled.)
2. **How many to order.** Each listed item also gets how many to order: enough units to bring its usable units plus
   the units on order up to twice its reorder level, rounded up to whole packs (the item's `pack_size` in the stock
   file; 1 if it has none).
   - In the text, it comes after the reorder level: code, name, usable units, reorder level, how many to order, in
     that order; the "(N on order)" ending stays at the end.
   - In the JSON, each object gets one more key, "order": the keys are exactly "code", "name", "location", "usable",
     "reorder_level", "on_order", "order".
3. **One location.** `--location NAME` lists only the items kept there: pharmacy, surgery or front desk, in any case
   (`Surgery` works too). Any other location is an error: the command says so and exits with code 2.

Everything else in the first draft stands.
