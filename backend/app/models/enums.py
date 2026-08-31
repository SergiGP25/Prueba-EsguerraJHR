from __future__ import annotations

import enum


class NaturalezaCuenta(str, enum.Enum):
    DEBITO = "debito"
    CREDITO = "credito"


class EstadoPeriodo(str, enum.Enum):
    ABIERTO = "abierto"
    CERRADO = "cerrado"


class EstadoComprobante(str, enum.Enum):
    BORRADOR = "borrador"
    CONTABILIZADO = "contabilizado"
    # El original de una reversión: sigue afectando el libro mayor (junto con su espejo,
    # que lo anula), pero ya no admite otra reversión.
    REVERSADO = "reversado"
