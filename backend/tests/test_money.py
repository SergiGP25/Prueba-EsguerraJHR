"""Precisión monetaria (Escenario 5): ningún valor puede pasar por float."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.core.money import is_positive_money, parse_money


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("1000000", "1000000.00"),
        ("1190000.50", "1190000.50"),
        ("0", "0.00"),
        (Decimal("190000.19"), "190000.19"),
        (1000, "1000.00"),
    ],
)
def test_parse_money_normaliza_a_dos_decimales(entrada, esperado):
    assert format(parse_money(entrada), "f") == esperado


@pytest.mark.parametrize("entrada", ["1000.123", "0.001"])
def test_parse_money_rechaza_decimales_excesivos(entrada):
    with pytest.raises(ValueError):
        parse_money(entrada)


@pytest.mark.parametrize("entrada", ["abc", "", "NaN", "Infinity", True])
def test_parse_money_rechaza_valores_no_numericos(entrada):
    with pytest.raises(ValueError):
        parse_money(entrada)


def test_suma_de_montos_no_pierde_precision():
    """El caso clásico donde float fallaría: 0.1 + 0.2 != 0.3."""
    total = parse_money("0.10") + parse_money("0.20")
    assert total == parse_money("0.30")


def test_is_positive_money():
    assert is_positive_money(parse_money("0.01"))
    assert not is_positive_money(parse_money("0.00"))
    assert not is_positive_money(parse_money("-5.00"))
