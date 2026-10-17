"""ClinicMaster 4 invoice totals (Devonport). Amounts are dollars as floats, as ClinicMaster stores them.

GST: 12.5% until 30 September 2010, 15% from 1 October 2010."""
import datetime

GST_CHANGE = datetime.date(2010, 10, 1)
CONSULT_FEE = 85.0
MEMBER_DISCOUNT = 0.075   # PetCover, from 2024 (Devonport applies it by hand)
LOYALTY_DISCOUNT = 0.05   # "Gold card" clients, discontinued 2021


def gst_rate(day):
    return 0.125 if day < GST_CHANGE else 0.15


def gst(amount, day):
    """GST on an amount, to the cent."""
    return round(amount * gst_rate(day), 2)


def line_total(price, quantity=1, discount=0.0):
    """ClinicMaster discounted each line's price, then rounded."""
    return round(price * quantity * (1 - discount), 2)


def invoice_total(lines, day, gold_card=False):
    """lines: (description, price, quantity). Returns (subtotal, gst, total) in dollars."""
    discount = LOYALTY_DISCOUNT if gold_card else 0.0
    subtotal = sum(line_total(price, quantity, discount) for _, price, quantity in lines)
    tax = gst(subtotal, day)
    return round(subtotal, 2), tax, round(subtotal + tax, 2)


def print_invoice(client_name, lines, day, gold_card=False):
    subtotal, tax, total = invoice_total(lines, day, gold_card)
    print("Invoice for %s, %s" % (client_name, day.strftime("%d/%m/%Y")))
    for description, price, quantity in lines:
        print("  %-40s %3d %10.2f" % (description[:40], quantity, line_total(price, quantity)))
    if gold_card:
        print("  %-40s     (5%% applied to each line)" % "Gold card discount")
    print("  %-40s     %10.2f" % ("Subtotal", subtotal))
    print("  %-40s     %10.2f" % ("GST %.1f%%" % (gst_rate(day) * 100), tax))
    print("  %-40s     %10.2f" % ("Total", total))
