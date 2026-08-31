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
