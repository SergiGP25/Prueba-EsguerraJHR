"""Reglas de los catálogos maestros: plan de cuentas y terceros.

Ninguno de los dos se borra. Una cuenta se inactiva (y deja de poder usarse al
contabilizar) y un tercero se corrige, porque ambos están referenciados por
movimientos ya registrados: borrarlos rompería el libro mayor y la auditoría.

El dígito de verificación vive aquí y no en la ruta porque es una regla de negocio
compartida por el alta y la edición, y porque debe viajar como `DomainError` para que
el frontend pueda traducirla por código.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import DomainError
from app.core.nit import calcular_dv, normalizar
from app.models import Cuenta, Tercero
from app.schemas import CuentaCreate, CuentaUpdate, TerceroCreate, TerceroUpdate

# El DV solo aplica al NIT; para cédulas y pasaportes no existe.
TIPO_DOC_CON_DV = "NIT"


def _resolver_dv(tipo_doc: str, num_doc: str, dv: str | None) -> str | None:
    """Calcula el DV cuando no viene informado y rechaza el que no corresponde.

    Un DV mal capturado excluye al tercero de la información exógena sin avisar,
    y el error solo se descubre meses después. Se corta en el momento del registro.
    """
    if tipo_doc.upper() != TIPO_DOC_CON_DV:
        return None

    try:
        correcto = calcular_dv(num_doc)
    except ValueError as exc:
        raise DomainError("TERCERO_DV_INVALIDO", f"El NIT '{num_doc}' no es válido: {exc}") from exc

    if dv is None or not dv.strip():
        return correcto

    if normalizar(dv) != correcto:
        raise DomainError(
            "TERCERO_DV_INVALIDO",
            f"El dígito de verificación informado ({dv}) no corresponde al NIT {num_doc}: "
            f"el correcto es {correcto}.",
        )
    return correcto


def _exigir_codigo_libre(db: Session, empresa_id: int, codigo: str, excluir_id: int | None = None) -> None:
    consulta = select(Cuenta).where(Cuenta.empresa_id == empresa_id, Cuenta.codigo == codigo)
    if excluir_id is not None:
        consulta = consulta.where(Cuenta.id != excluir_id)
    if db.scalar(consulta) is not None:
        raise DomainError(
            "CUENTA_DUPLICADA",
            f"Ya existe una cuenta con el código {codigo} en la empresa.",
            status_code=409,
        )


def _exigir_documento_libre(
    db: Session,
    empresa_id: int,
    tipo_doc: str,
    num_doc: str,
    excluir_id: int | None = None,
) -> None:
    """Comprueba la unicidad antes de insertar.

    Sin esto, el choque contra `uq_tercero_doc` sale como IntegrityError sin manejar,
    es decir un 500 en un camino que desde el formulario es perfectamente normal.
    """
    consulta = select(Tercero).where(
        Tercero.empresa_id == empresa_id,
        Tercero.tipo_doc == tipo_doc,
        Tercero.num_doc == num_doc,
    )
    if excluir_id is not None:
        consulta = consulta.where(Tercero.id != excluir_id)
    if db.scalar(consulta) is not None:
        raise DomainError(
            "TERCERO_DUPLICADO",
            f"Ya existe un tercero con documento {tipo_doc} {num_doc} en la empresa.",
            status_code=409,
        )


def crear_cuenta(db: Session, empresa_id: int, datos: CuentaCreate) -> Cuenta:
    _exigir_codigo_libre(db, empresa_id, datos.codigo)
    cuenta = Cuenta(empresa_id=empresa_id, **datos.model_dump())
    db.add(cuenta)
    db.flush()
    return cuenta


def actualizar_cuenta(db: Session, cuenta: Cuenta, datos: CuentaUpdate) -> Cuenta:
    """El código no se edita: es la clave del PUC con la que se referencian los reportes."""
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(cuenta, campo, valor)
    db.flush()
    return cuenta


def crear_tercero(db: Session, empresa_id: int, datos: TerceroCreate) -> Tercero:
    _exigir_documento_libre(db, empresa_id, datos.tipo_doc, datos.num_doc)
    tercero = Tercero(
        empresa_id=empresa_id,
        tipo_doc=datos.tipo_doc,
        num_doc=datos.num_doc,
        dv=_resolver_dv(datos.tipo_doc, datos.num_doc, datos.dv),
        nombre=datos.nombre,
    )
    db.add(tercero)
    db.flush()
    return tercero


def actualizar_tercero(db: Session, tercero: Tercero, datos: TerceroUpdate) -> Tercero:
    cambios = datos.model_dump(exclude_unset=True)

    tipo_doc = cambios.get("tipo_doc", tercero.tipo_doc)
    num_doc = cambios.get("num_doc", tercero.num_doc)

    if (tipo_doc, num_doc) != (tercero.tipo_doc, tercero.num_doc):
        _exigir_documento_libre(db, tercero.empresa_id, tipo_doc, num_doc, excluir_id=tercero.id)

    # Si el documento cambia y no se informa un DV nuevo, se recalcula: conservar el
    # anterior dejaría un par NIT/DV incoherente.
    dv = cambios["dv"] if "dv" in cambios else (tercero.dv if num_doc == tercero.num_doc else None)

    tercero.tipo_doc = tipo_doc
    tercero.num_doc = num_doc
    tercero.dv = _resolver_dv(tipo_doc, num_doc, dv)
    if "nombre" in cambios:
        tercero.nombre = cambios["nombre"]

    db.flush()
    return tercero
