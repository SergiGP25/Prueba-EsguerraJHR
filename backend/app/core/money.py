from __future__ import annotations

from decimal import Decimal, InvalidOperation

# Precisión monetaria colombiana: 2 decimales (pesos y centavos).
# Nunca usamos float: el valor llega como str/Decimal y se cuantiza de forma explícita.
MONEY_QUANT = Decimal("0.01")
MONEY_MAX_DIGITS = 18
MONEY_DECIMAL_PLACES = 2


def parse_money(value: str | Decimal | int) -> Decimal:
    """Convierte un valor a Decimal con exactamente 2 decimales.

    Rechaza más de 2 decimales (regla de "decimales excesivos") y cualquier
    representación que no sea un número decimal exacto.
    """
    if isinstance(value, bool):
        raise ValueError("El valor monetario no es válido.")
    try:
        raw = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("El valor monetario no es un número válido.") from exc

    if not raw.is_finite():
        raise ValueError("El valor monetario no es finito.")

    quantized = raw.quantize(MONEY_QUANT)
    if quantized != raw:
        raise ValueError("Los valores monetarios no pueden tener más de 2 decimales.")
    return quantized


def is_positive_money(value: Decimal) -> bool:
    return value > Decimal("0.00")
