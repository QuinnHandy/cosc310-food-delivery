"""The one place money is calculated (#92). Used by the cart, and meant for checkout too, so
the price a customer sees and the price they are charged come from the same code.

Uses Decimal so amounts like 0.1 + 0.2 come out as 0.30, then rounds every amount to cents
(half up, as on a receipt).
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def to_money(value: float | int | str | Decimal) -> Decimal:
    """Converts a price to a Decimal rounded to cents. Floats go through str() so 15.5 stays 15.50."""
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class PricedLine:
    unit_price: Decimal
    quantity: int
    line_total: Decimal


@dataclass(frozen=True)
class PriceBreakdown:
    lines: list[PricedLine]
    subtotal: Decimal
    delivery_fee: Decimal
    total: Decimal


def price_lines(lines: list[tuple[float | Decimal, int]], delivery_fee: Decimal) -> PriceBreakdown:
    """Prices (unit_price, quantity) pairs.

    line_total = unit_price x quantity; subtotal = sum of line totals; total = subtotal +
    delivery fee. An empty list costs nothing, not even the delivery fee.
    """
    priced = []
    for unit_price, quantity in lines:
        unit = to_money(unit_price)
        priced.append(PricedLine(unit, quantity, to_money(unit * quantity)))
    subtotal = to_money(sum((line.line_total for line in priced), Decimal("0")))
    fee = to_money(delivery_fee) if priced else to_money(0)
    return PriceBreakdown(priced, subtotal, fee, to_money(subtotal + fee))
