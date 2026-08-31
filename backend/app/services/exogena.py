"""Generación de información exógena simplificada.

Reglas implementadas (numeración del enunciado):

10. El NIT del informante se valida con el algoritmo del dígito de verificación.
11. Los movimientos se agrupan por tercero y concepto.
12. El umbral se expresa en UVT y se convierte a pesos con el valor del año gravable;
    los terceros por debajo se excluyen dejando traza en el log y en la generación.
13. Los totales de control se calculan sobre los registros efectivamente incluidos.
14. Cada generación queda registrada con fecha, parámetros e identificador de descarga.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from xml.etree import ElementTree as ET

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import DomainError
from app.core.nit import dv_valido
from app.models import (
    Comprobante,
    Cuenta,
    Empresa,
    ExogenaGeneracion,
    LineaContable,
    Tercero,
)
from app.services.reporting import ESTADOS_CONTABLES
from app.services.uvt import valor_uvt

logger = logging.getLogger(__name__)

CERO = Decimal("0.00")

# Mapeo de cuentas a conceptos DIAN por prefijo del código PUC.
# Es una simplificación consciente: en producción sería una tabla configurable por
# empresa y año gravable, porque los conceptos cambian con cada resolución.
CONCEPTOS_POR_PREFIJO: dict[str, tuple[str, str]] = {
    "4": ("1007", "Ingresos brutos recibidos"),
    "5": ("5001", "Pagos o abonos en cuenta"),
    "6": ("5001", "Pagos o abonos en cuenta"),
    "7": ("5001", "Pagos o abonos en cuenta"),
    "1": ("1010", "Cuentas por cobrar"),
    "2": ("2010", "Cuentas por pagar"),
}
CONCEPTO_POR_DEFECTO = ("5001", "Pagos o abonos en cuenta")

# Cuentas de retención practicada: alimentan `valorRetencion`, no `valorBruto`.
PREFIJOS_RETENCION = ("2365", "2367", "2368")


@dataclass
class RegistroExogena:
    tipo_doc: str
    num_doc: str
    nombre: str
    concepto: str
    valor_bruto: Decimal = CERO
    valor_retencion: Decimal = CERO


@dataclass
class Exclusion:
    tercero: str
    motivo: str
    valor: Decimal = CERO


@dataclass
class ResultadoExogena:
    registros: list[RegistroExogena] = field(default_factory=list)
    exclusiones: list[Exclusion] = field(default_factory=list)

    @property
    def total_valor_bruto(self) -> Decimal:
        return sum((r.valor_bruto for r in self.registros), CERO)

    @property
    def total_retencion(self) -> Decimal:
        return sum((r.valor_retencion for r in self.registros), CERO)


def concepto_de_cuenta(codigo: str) -> tuple[str, str]:
    """Concepto DIAN asociado a una cuenta, deducido del primer dígito del código PUC."""
    return CONCEPTOS_POR_PREFIJO.get(codigo[:1], CONCEPTO_POR_DEFECTO)


def _es_retencion(codigo: str) -> bool:
    return codigo.startswith(PREFIJOS_RETENCION)


def _validar_informante(empresa: Empresa) -> None:
    if not dv_valido(empresa.nit, empresa.dv):
        raise DomainError(
            "NIT_DV_INVALIDO",
            f"El NIT {empresa.nit}-{empresa.dv} del informante no supera la validación "
            "del dígito de verificación. Corrija la empresa antes de generar el archivo.",
        )


def _movimientos_con_tercero(db: Session, empresa_id: int, anio: int):
    """Líneas contabilizadas del año gravable que están asociadas a un tercero."""
    return db.execute(
        select(LineaContable, Cuenta, Tercero)
        .join(Comprobante, LineaContable.comprobante_id == Comprobante.id)
        .join(Cuenta, LineaContable.cuenta_id == Cuenta.id)
        .join(Tercero, LineaContable.tercero_id == Tercero.id)
        .where(
            Comprobante.empresa_id == empresa_id,
            Comprobante.estado.in_(ESTADOS_CONTABLES),
            Comprobante.fecha >= date(anio, 1, 1),
            Comprobante.fecha <= date(anio, 12, 31),
        )
        .order_by(Tercero.num_doc, Cuenta.codigo)
    ).all()


def consolidar(db: Session, empresa: Empresa, anio: int, umbral_pesos: Decimal) -> ResultadoExogena:
    """Agrupa los movimientos por tercero y concepto y aplica el umbral."""
    acumulado: dict[tuple[int, str], RegistroExogena] = {}
    retenciones: dict[int, Decimal] = {}
    terceros: dict[int, Tercero] = {}

    for linea, cuenta, tercero in _movimientos_con_tercero(db, empresa.id, anio):
        terceros[tercero.id] = tercero
        # El valor informado es el movimiento neto de la línea, sin importar su signo contable.
        monto = linea.debito + linea.credito

        if _es_retencion(cuenta.codigo):
            retenciones[tercero.id] = retenciones.get(tercero.id, CERO) + monto
            continue

        codigo_concepto, _ = concepto_de_cuenta(cuenta.codigo)
        clave = (tercero.id, codigo_concepto)
        registro = acumulado.get(clave)
        if registro is None:
            registro = RegistroExogena(
                tipo_doc=tercero.tipo_doc,
                num_doc=tercero.num_doc,
                nombre=tercero.nombre,
                concepto=codigo_concepto,
            )
            acumulado[clave] = registro
        registro.valor_bruto += monto

    # La retención de un tercero se imputa a su registro de mayor valor bruto.
    for tercero_id, retenido in retenciones.items():
        candidatos = [r for (t_id, _), r in acumulado.items() if t_id == tercero_id]
        if candidatos:
            max(candidatos, key=lambda r: r.valor_bruto).valor_retencion += retenido

    resultado = ResultadoExogena()
    for (tercero_id, _), registro in sorted(acumulado.items(), key=lambda kv: (kv[0][1], kv[1].num_doc)):
        tercero = terceros[tercero_id]
        etiqueta = f"{tercero.tipo_doc} {tercero.num_doc} ({tercero.nombre})"

        # El DV del tercero solo se verifica si fue informado: no se penaliza un dato ausente.
        if tercero.tipo_doc.upper() == "NIT" and tercero.dv and not dv_valido(tercero.num_doc, tercero.dv):
            resultado.exclusiones.append(
                Exclusion(etiqueta, "NIT del tercero con dígito de verificación inválido", registro.valor_bruto)
            )
            logger.warning("Exógena %s: excluido %s por DV inválido.", anio, etiqueta)
            continue

        if registro.valor_bruto < umbral_pesos:
            resultado.exclusiones.append(
                Exclusion(etiqueta, f"No supera el umbral de {umbral_pesos:f} pesos", registro.valor_bruto)
            )
            logger.info(
                "Exógena %s: excluido %s con %s (umbral %s).",
                anio,
                etiqueta,
                registro.valor_bruto,
                umbral_pesos,
            )
            continue

        resultado.registros.append(registro)

    return resultado


def construir_xml(empresa: Empresa, anio: int, resultado: ResultadoExogena) -> str:
    """Serializa el resultado en la estructura XML definida por el enunciado."""
    raiz = ET.Element("InformacionExogena", version="1.0")
    ET.SubElement(
        raiz,
        "Informante",
        nit=empresa.nit,
        dv=empresa.dv,
        razonSocial=empresa.razon_social,
        anioGravable=str(anio),
    )

    registros = ET.SubElement(raiz, "Registros")
    for registro in resultado.registros:
        ET.SubElement(
            registros,
            "Registro",
            tipoDoc=registro.tipo_doc,
            numDoc=registro.num_doc,
            nombre=registro.nombre,
            concepto=registro.concepto,
            valorBruto=format(registro.valor_bruto, "f"),
            valorRetencion=format(registro.valor_retencion, "f"),
        )

    ET.SubElement(
        raiz,
        "Totales",
        registros=str(len(resultado.registros)),
        totalValorBruto=format(resultado.total_valor_bruto, "f"),
        totalRetencion=format(resultado.total_retencion, "f"),
    )

    ET.indent(raiz, space="  ")
    return ET.tostring(raiz, encoding="unicode", xml_declaration=True)


def generar(db: Session, empresa_id: int, anio: int, umbral_uvt: Decimal) -> ExogenaGeneracion:
    """Genera el archivo y deja registro de la ejecución para poder re-descargarlo."""
    empresa = db.get(Empresa, empresa_id)
    if empresa is None:
        raise DomainError("EMPRESA_NO_ENCONTRADA", "La empresa no existe.", status_code=404)

    _validar_informante(empresa)

    uvt = valor_uvt(db, anio)
    umbral_pesos = (umbral_uvt * uvt).quantize(Decimal("0.01"))

    resultado = consolidar(db, empresa, anio, umbral_pesos)
    xml = construir_xml(empresa, anio, resultado)

    generacion = ExogenaGeneracion(
        empresa_id=empresa.id,
        anio_gravable=anio,
        umbral_uvt=umbral_uvt,
        valor_uvt=uvt,
        umbral_pesos=umbral_pesos,
        total_registros=len(resultado.registros),
        total_valor_bruto=resultado.total_valor_bruto,
        total_retencion=resultado.total_retencion,
        exclusiones=[
            {"tercero": e.tercero, "motivo": e.motivo, "valor": format(e.valor, "f")}
            for e in resultado.exclusiones
        ],
        nombre_archivo=f"exogena_{empresa.nit}_{anio}.xml",
        xml=xml,
    )
    db.add(generacion)
    db.flush()
    logger.info(
        "Exógena %s generada (id=%s): %s registros, %s excluidos.",
        anio,
        generacion.id,
        generacion.total_registros,
        len(resultado.exclusiones),
    )
    return generacion


def listar_generaciones(db: Session, empresa_id: int | None = None, limite: int = 50):
    consulta = select(ExogenaGeneracion).order_by(ExogenaGeneracion.id.desc()).limit(limite)
    if empresa_id is not None:
        consulta = consulta.where(ExogenaGeneracion.empresa_id == empresa_id)
    return list(db.scalars(consulta).all())
