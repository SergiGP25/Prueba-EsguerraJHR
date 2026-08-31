"""Consultas de lectura del libro mayor.

Se separa de `accounting` porque son responsabilidades distintas: aquí no se muta
estado contable, solo se proyectan los movimientos ya registrados.

Estrategia de saldo acumulado: se calcula en tiempo real a partir de los movimientos,
sin mantener acumulados materializados. Ver README para el análisis de consistencia,
rendimiento y concurrencia.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Comprobante,
    Cuenta,
    EstadoComprobante,
    LineaContable,
    NaturalezaCuenta,
)

CERO = Decimal("0.00")

# Un comprobante en borrador no es un hecho contable: no puede aparecer en el mayor.
# Un comprobante reversado sí: su asiento existió y su espejo lo anula, y ambos deben verse.
ESTADOS_CONTABLES = (EstadoComprobante.CONTABILIZADO, EstadoComprobante.REVERSADO)


@dataclass(frozen=True)
class MovimientoMayor:
    fecha: date
    comprobante_id: int
    numero: int | None
    descripcion: str
    tercero_nombre: str | None
    debito: Decimal
    credito: Decimal
    saldo: Decimal


@dataclass(frozen=True)
class LibroMayor:
    cuenta: Cuenta
    fecha_desde: date
    fecha_hasta: date
    saldo_inicial: Decimal
    movimientos: list[MovimientoMayor]
    total_debito: Decimal
    total_credito: Decimal
    saldo_final: Decimal


def _movimientos_de_cuenta(empresa_id: int, cuenta_id: int) -> Select:
    return (
        select(LineaContable, Comprobante)
        .join(Comprobante, LineaContable.comprobante_id == Comprobante.id)
        .where(
            Comprobante.empresa_id == empresa_id,
            LineaContable.cuenta_id == cuenta_id,
            Comprobante.estado.in_(ESTADOS_CONTABLES),
        )
    )


def _variacion(naturaleza: NaturalezaCuenta, debito: Decimal, credito: Decimal) -> Decimal:
    """Efecto de un movimiento sobre el saldo, según la naturaleza de la cuenta.

    En una cuenta de naturaleza débito el saldo aumenta con débitos; en una de
    naturaleza crédito ocurre lo contrario. Así el saldo se lee siempre en positivo.
    """
    if naturaleza == NaturalezaCuenta.DEBITO:
        return debito - credito
    return credito - debito


def saldo_inicial(db: Session, cuenta: Cuenta, fecha_desde: date) -> Decimal:
    """Saldo acumulado por los movimientos anteriores al rango consultado."""
    fila = db.execute(
        select(
            func.coalesce(func.sum(LineaContable.debito), CERO),
            func.coalesce(func.sum(LineaContable.credito), CERO),
        )
        .select_from(LineaContable)
        .join(Comprobante, LineaContable.comprobante_id == Comprobante.id)
        .where(
            Comprobante.empresa_id == cuenta.empresa_id,
            LineaContable.cuenta_id == cuenta.id,
            Comprobante.estado.in_(ESTADOS_CONTABLES),
            Comprobante.fecha < fecha_desde,
        )
    ).one()
    debito, credito = fila
    return _variacion(cuenta.naturaleza, debito, credito)


def libro_mayor(db: Session, cuenta: Cuenta, fecha_desde: date, fecha_hasta: date) -> LibroMayor:
    inicial = saldo_inicial(db, cuenta, fecha_desde)

    filas = db.execute(
        _movimientos_de_cuenta(cuenta.empresa_id, cuenta.id)
        .where(Comprobante.fecha >= fecha_desde, Comprobante.fecha <= fecha_hasta)
        .options(selectinload(LineaContable.tercero))
        .order_by(Comprobante.fecha, Comprobante.numero, LineaContable.id)
    ).all()

    saldo = inicial
    total_debito = CERO
    total_credito = CERO
    movimientos: list[MovimientoMayor] = []

    for linea, comprobante in filas:
        saldo += _variacion(cuenta.naturaleza, linea.debito, linea.credito)
        total_debito += linea.debito
        total_credito += linea.credito
        movimientos.append(
            MovimientoMayor(
                fecha=comprobante.fecha,
                comprobante_id=comprobante.id,
                numero=comprobante.numero,
                descripcion=linea.descripcion or comprobante.descripcion,
                tercero_nombre=linea.tercero.nombre if linea.tercero else None,
                debito=linea.debito,
                credito=linea.credito,
                saldo=saldo,
            )
        )

    return LibroMayor(
        cuenta=cuenta,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        saldo_inicial=inicial,
        movimientos=movimientos,
        total_debito=total_debito,
        total_credito=total_credito,
        saldo_final=saldo,
    )
