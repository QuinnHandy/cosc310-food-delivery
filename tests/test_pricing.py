"""The shared pricing function (#92)."""

from decimal import Decimal

from app.services.pricing import price_lines, to_money

FEE = Decimal("4.99")


def test_empty_cart_costs_nothing_not_even_delivery():
    result = price_lines([], FEE)
    assert result.subtotal == Decimal("0.00")
    assert result.delivery_fee == Decimal("0.00")
    assert result.total == Decimal("0.00")


def test_one_line():
    result = price_lines([(15.5, 2)], FEE)
    assert result.lines[0].line_total == Decimal("31.00")
    assert result.subtotal == Decimal("31.00")
    assert result.total == Decimal("35.99")


def test_several_lines_are_summed():
    result = price_lines([(15.5, 1), (7.0, 3), (14.25, 2)], FEE)
    assert [line.line_total for line in result.lines] == [Decimal("15.50"), Decimal("21.00"), Decimal("28.50")]
    assert result.subtotal == Decimal("65.00")
    assert result.total == Decimal("69.99")


def test_no_float_rounding_noise():
    # 0.1 + 0.2 is 0.30000000000000004 in floats
    result = price_lines([(0.1, 1), (0.2, 1)], Decimal("0"))
    assert result.subtotal == Decimal("0.30")
    assert float(result.subtotal) == 0.3


def test_amounts_round_half_up_to_cents():
    assert to_money(2.675) == Decimal("2.68")  # as a float 2.675 is slightly below, str() keeps it
    assert to_money("0.005") == Decimal("0.01")
    # The unit price is rounded to cents first, so the line is 3.33 x 3, as the customer sees it.
    assert price_lines([(3.333, 3)], Decimal("0")).lines[0].line_total == Decimal("9.99")
