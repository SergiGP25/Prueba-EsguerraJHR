from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import DomainError
from app.core.money import is_positive_money, parse_money
from app.models import (
    Comprobante,
    Cuenta,
    EstadoComprobante,
    EstadoPeriodo,
    LineaContable,
    Periodo,
    Tercero,
)
from app.schemas import LineaIn


def obtener_o_crear_periodo(db: Session, empresa_id: int, fecha) -> Periodo:
    periodo = db.scalar(
        select(Periodo).where(
            Periodo.empresa_id == empresa_id,
            Periodo.anio == fecha.year,
            Periodo.mes == fecha.month,
        )
    )
    if periodo is None:
        periodo = Periodo(
            empresa_id=empresa_id,
            anio=fecha.year,
            mes=fecha.month,
            estado=EstadoPeriodo.ABIERTO,
        )
        db.add(periodo)
        db.flush()
    return periodo


def _lineas_desde_input(db: Session, empresa_id: int, lineas_in: list[LineaIn]) -> list[LineaContable]:
    result: list[LineaContable] = []
    for linea in lineas_in:
        cuenta = db.get(Cuenta, linea.cuenta_id)
        if cuenta is None or cuenta.empresa_id != empresa_id:
            raise DomainError("CUENTA_NO_ENCONTRADA", "La cuenta no existe en la empresa.")
        if linea.tercero_id is not None:
            tercero = db.get(Tercero, linea.tercero_id)
            if tercero is None or tercero.empresa_id != empresa_id:
                raise DomainError("TERCERO_NO_ENCONTRADO", "El tercero no existe en la empresa.")
        result.append(
            LineaContable(
                cuenta_id=linea.cuenta_id,
                tercero_id=linea.tercero_id,
                debito=parse_money(linea.debito),
                credito=parse_money(linea.credito),
                descripcion=linea.descripcion,
            )
        )
    return result


def crear_comprobante_borrador(
    db: Session,
    empresa_id: int,
    fecha,
    descripcion: str,
    lineas_in: list[LineaIn],
) -> Comprobante:
    periodo = obtener_o_crear_periodo(db, empresa_id, fecha)
    if periodo.estado == EstadoPeriodo.CERRADO:
        raise DomainError(
            "PERIODO_CERRADO",
            f"El período {periodo.anio}-{periodo.mes:02d} está cerrado. No se pueden registrar comprobantes.",
            status_code=409,
        )
    comprobante = Comprobante(
        empresa_id=empresa_id,
        periodo_id=periodo.id,
        fecha=fecha,
        descripcion=descripcion,
        estado=EstadoComprobante.BORRADOR,
        lineas=_lineas_desde_input(db, empresa_id, lineas_in),
    )
    db.add(comprobante)
    db.flush()
    db.refresh(comprobante)
    return cargar_comprobante(db, comprobante.id)


def actualizar_comprobante_borrador(
    db: Session,
    comprobante: Comprobante,
    fecha,
    descripcion: str | None,
    lineas_in: list[LineaIn] | None,
) -> Comprobante:
    if comprobante.estado != EstadoComprobante.BORRADOR:
        raise DomainError(
            "COMPROBANTE_PROTEGIDO",
            "Un comprobante contabilizado no puede modificarse. Use una reversión.",
            status_code=409,
        )
    if fecha is not None:
        periodo = obtener_o_crear_periodo(db, comprobante.empresa_id, fecha)
        if periodo.estado == EstadoPeriodo.CERRADO:
            raise DomainError(
                "PERIODO_CERRADO",
                f"El período {periodo.anio}-{periodo.mes:02d} está cerrado. No se pueden registrar comprobantes.",
                status_code=409,
            )
        comprobante.fecha = fecha
        comprobante.periodo_id = periodo.id
    if descripcion is not None:
        comprobante.descripcion = descripcion
    if lineas_in is not None:
        comprobante.lineas.clear()
        db.flush()
        comprobante.lineas.extend(_lineas_desde_input(db, comprobante.empresa_id, lineas_in))
    db.flush()
    return cargar_comprobante(db, comprobante.id)


def validar_para_contabilizar(db: Session, comprobante: Comprobante) -> None:
    if comprobante.estado != EstadoComprobante.BORRADOR:
        raise DomainError(
            "ESTADO_INVALIDO",
            "Solo se puede contabilizar un comprobante en estado borrador.",
            status_code=409,
        )

    lineas = list(comprobante.lineas)
    if len(lineas) < 2:
        raise DomainError("LINEAS_INSUFICIENTES", "El comprobante debe tener al menos dos líneas.")

    total_debito = Decimal("0.00")
    total_credito = Decimal("0.00")

    for idx, linea in enumerate(lineas, start=1):
        debito = parse_money(linea.debito)
        credito = parse_money(linea.credito)
        debito_positivo = is_positive_money(debito)
        credito_positivo = is_positive_money(credito)

        if debito_positivo and credito_positivo:
            raise DomainError(
                "DEBITO_Y_CREDITO",
                f"La línea {idx} no puede tener débito y crédito simultáneamente.",
            )
        if not debito_positivo and not credito_positivo:
            raise DomainError(
                "VALOR_INVALIDO",
                f"La línea {idx} debe tener un débito o un crédito mayor a cero.",
            )
        if debito < Decimal("0.00") or credito < Decimal("0.00"):
            raise DomainError("VALOR_INVALIDO", f"La línea {idx} no puede tener valores negativos.")

        cuenta = db.get(Cuenta, linea.cuenta_id)
        if cuenta is None or cuenta.empresa_id != comprobante.empresa_id:
            raise DomainError("CUENTA_NO_ENCONTRADA", f"La cuenta de la línea {idx} no existe en la empresa.")
        if not cuenta.activa:
            raise DomainError(
                "CUENTA_INACTIVA",
                f"La cuenta {cuenta.codigo} ({cuenta.nombre}) está inactiva.",
            )

        total_debito += debito
        total_credito += credito

    if total_debito != total_credito:
        raise DomainError(
            "PARTIDA_DOBLE",
            f"El comprobante no cuadra: débitos {format(total_debito, 'f')} ≠ créditos {format(total_credito, 'f')}.",
        )

    periodo = db.get(Periodo, comprobante.periodo_id)
    if periodo is None:
        raise DomainError("PERIODO_NO_ENCONTRADO", "El período del comprobante no existe.")
    if periodo.estado == EstadoPeriodo.CERRADO:
        raise DomainError(
            "PERIODO_CERRADO",
            f"El período {periodo.anio}-{periodo.mes:02d} está cerrado. No se pueden contabilizar comprobantes.",
            status_code=409,
        )


def contabilizar(db: Session, comprobante: Comprobante) -> Comprobante:
    """Contabiliza de forma atómica: validación + número + cambio de estado en una sola transacción.

    El lock sobre el período (FOR UPDATE) evita que dos contabilizaciones concurrentes
    asignen el mismo número. La numeración se profundiza en el Día 2.
    """
    periodo = db.execute(
        select(Periodo).where(Periodo.id == comprobante.periodo_id).with_for_update()
    ).scalar_one()
    comprobante.periodo = periodo

    validar_para_contabilizar(db, comprobante)

    max_numero = db.scalar(
        select(func.coalesce(func.max(Comprobante.numero), 0)).where(
            Comprobante.empresa_id == comprobante.empresa_id,
            Comprobante.periodo_id == comprobante.periodo_id,
        )
    )
    comprobante.numero = int(max_numero) + 1
    comprobante.estado = EstadoComprobante.CONTABILIZADO
    db.flush()
    return cargar_comprobante(db, comprobante.id)


def cerrar_periodo(db: Session, periodo: Periodo) -> Periodo:
    if periodo.estado == EstadoPeriodo.CERRADO:
        raise DomainError("PERIODO_YA_CERRADO", "El período ya está cerrado.", status_code=409)
    periodo.estado = EstadoPeriodo.CERRADO
    db.flush()
    return periodo


def cargar_comprobante(db: Session, comprobante_id: int) -> Comprobante | None:
    return db.scalar(
        select(Comprobante)
        .options(
            selectinload(Comprobante.lineas).selectinload(LineaContable.cuenta),
            selectinload(Comprobante.periodo),
        )
        .where(Comprobante.id == comprobante_id)
    )


def totales(comprobante: Comprobante) -> tuple[Decimal, Decimal]:
    debito = sum((parse_money(l.debito) for l in comprobante.lineas), Decimal("0.00"))
    credito = sum((parse_money(l.credito) for l in comprobante.lineas), Decimal("0.00"))
    return debito, credito
