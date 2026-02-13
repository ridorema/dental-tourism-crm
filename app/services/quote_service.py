from decimal import Decimal


def calculate_quote_total(items):
    total = Decimal("0")
    for item in items:
        unit_price = Decimal(str(item.get("unit_price", 0)))
        quantity = Decimal(str(item.get("quantity", 1)))
        total += unit_price * quantity
    return total.quantize(Decimal("0.01"))
