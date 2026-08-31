"""Dígito de verificación del NIT (algoritmo DIAN).

Funciones puras, sin dependencias de base de datos ni de framework: son la parte
del dominio más fácil de probar y la que no debe cambiar si cambia la persistencia.
"""

from __future__ import annotations

# Pesos oficiales, aplicados de derecha a izquierda sobre los dígitos del NIT.
PESOS = (3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71)


def normalizar(nit: str) -> str:
    """Deja solo los dígitos: acepta entradas con puntos, guiones o espacios."""
    return "".join(c for c in nit if c.isdigit())


def calcular_dv(nit: str) -> str:
    """Calcula el dígito de verificación de un NIT.

    Ejemplo conocido: 890903938 → 8.
    """
    digitos = normalizar(nit)
    if not digitos:
        raise ValueError("El NIT no contiene dígitos.")
    if len(digitos) > len(PESOS):
        raise ValueError(f"El NIT no puede superar {len(PESOS)} dígitos.")

    # `strict=False`: los NIT son más cortos que la tabla de pesos y se emparejan por la derecha.
    suma = sum(int(digito) * peso for digito, peso in zip(reversed(digitos), PESOS, strict=False))
    residuo = suma % 11
    # Residuos 0 y 1 se usan tal cual; el resto se complementa a 11.
    return str(residuo if residuo < 2 else 11 - residuo)


def dv_valido(nit: str, dv: str) -> bool:
    """Indica si el par NIT/DV es consistente. Nunca lanza: entradas basura son inválidas."""
    try:
        return calcular_dv(nit) == normalizar(dv)
    except ValueError:
        return False
