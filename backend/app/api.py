from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import DomainError
from app.db import get_db
from app.models import (
    Comprobante,
    Cuenta,
    Empresa,
    ExogenaGeneracion,
    LineaContable,
    Periodo,
    Tercero,
)
from app.schemas import (
    ComprobanteCreate,
    ComprobanteOut,
    ComprobanteUpdate,
    CuentaCreate,
    CuentaOut,
    CuentaUpdate,
    EmpresaCreate,
    EmpresaOut,
    ExogenaGeneracionOut,
    ExogenaGenerarIn,
    LibroMayorOut,
    PeriodoCreate,
    PeriodoOut,
    ReversionCreate,
    TerceroCreate,
    TerceroOut,
    UvtSincronizacionOut,
    UvtValorOut,
)
from app.services import accounting, exogena, reporting, uvt

router = APIRouter(prefix="/api")


def _comprobante_out(comprobante: Comprobante) -> ComprobanteOut:
    total_debito, total_credito = accounting.totales(comprobante)
    payload = ComprobanteOut.model_validate(comprobante)
    return payload.model_copy(
        update={
            "total_debito": format(total_debito, "f"),
            "total_credito": format(total_credito, "f"),
        }
    )


def _empresa_or_404(db: Session, empresa_id: int) -> Empresa:
    empresa = db.get(Empresa, empresa_id)
    if empresa is None:
        raise HTTPException(status_code=404, detail="Empresa no encontrada.")
    return empresa


def _comprobante_or_404(db: Session, comprobante_id: int) -> Comprobante:
    comprobante = accounting.cargar_comprobante(db, comprobante_id)
    if comprobante is None:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado.")
    return comprobante


@router.post("/empresas", response_model=EmpresaOut, status_code=201)
def crear_empresa(payload: EmpresaCreate, db: Session = Depends(get_db)) -> Empresa:
    existe = db.scalar(select(Empresa).where(Empresa.nit == payload.nit))
    if existe:
        raise HTTPException(status_code=409, detail="Ya existe una empresa con ese NIT.")
    empresa = Empresa(**payload.model_dump())
    db.add(empresa)
    db.commit()
    db.refresh(empresa)
    return empresa


@router.get("/empresas", response_model=list[EmpresaOut])
def listar_empresas(db: Session = Depends(get_db)) -> list[Empresa]:
    return list(db.scalars(select(Empresa).order_by(Empresa.id)).all())


@router.get("/empresas/{empresa_id}", response_model=EmpresaOut)
def obtener_empresa(empresa_id: int, db: Session = Depends(get_db)) -> Empresa:
    return _empresa_or_404(db, empresa_id)


@router.post("/empresas/{empresa_id}/cuentas", response_model=CuentaOut, status_code=201)
def crear_cuenta(empresa_id: int, payload: CuentaCreate, db: Session = Depends(get_db)) -> Cuenta:
    _empresa_or_404(db, empresa_id)
    duplicada = db.scalar(
        select(Cuenta).where(Cuenta.empresa_id == empresa_id, Cuenta.codigo == payload.codigo)
    )
    if duplicada:
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese código.")
    cuenta = Cuenta(empresa_id=empresa_id, **payload.model_dump())
    db.add(cuenta)
    db.commit()
    db.refresh(cuenta)
    return cuenta


@router.get("/empresas/{empresa_id}/cuentas", response_model=list[CuentaOut])
def listar_cuentas(empresa_id: int, db: Session = Depends(get_db)) -> list[Cuenta]:
    _empresa_or_404(db, empresa_id)
    return list(db.scalars(select(Cuenta).where(Cuenta.empresa_id == empresa_id).order_by(Cuenta.codigo)).all())


@router.patch("/cuentas/{cuenta_id}", response_model=CuentaOut)
def actualizar_cuenta(cuenta_id: int, payload: CuentaUpdate, db: Session = Depends(get_db)) -> Cuenta:
    cuenta = db.get(Cuenta, cuenta_id)
    if cuenta is None:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada.")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(cuenta, key, value)
    db.commit()
    db.refresh(cuenta)
    return cuenta


@router.post("/empresas/{empresa_id}/periodos", response_model=PeriodoOut, status_code=201)
def crear_periodo(empresa_id: int, payload: PeriodoCreate, db: Session = Depends(get_db)) -> Periodo:
    _empresa_or_404(db, empresa_id)
    existe = db.scalar(
        select(Periodo).where(
            Periodo.empresa_id == empresa_id,
            Periodo.anio == payload.anio,
            Periodo.mes == payload.mes,
        )
    )
    if existe:
        raise HTTPException(status_code=409, detail="El período ya existe.")
    periodo = Periodo(empresa_id=empresa_id, **payload.model_dump())
    db.add(periodo)
    db.commit()
    db.refresh(periodo)
    return periodo


@router.get("/empresas/{empresa_id}/periodos", response_model=list[PeriodoOut])
def listar_periodos(empresa_id: int, db: Session = Depends(get_db)) -> list[Periodo]:
    _empresa_or_404(db, empresa_id)
    return list(
        db.scalars(
            select(Periodo)
            .where(Periodo.empresa_id == empresa_id)
            .order_by(Periodo.anio, Periodo.mes)
        ).all()
    )


@router.post("/periodos/{periodo_id}/cerrar", response_model=PeriodoOut)
def cerrar_periodo(periodo_id: int, db: Session = Depends(get_db)) -> Periodo:
    periodo = db.get(Periodo, periodo_id)
    if periodo is None:
        raise HTTPException(status_code=404, detail="Período no encontrado.")
    cerrado = accounting.cerrar_periodo(db, periodo)
    db.commit()
    db.refresh(cerrado)
    return cerrado


@router.get("/empresas/{empresa_id}/libro-mayor", response_model=LibroMayorOut)
def consultar_libro_mayor(
    empresa_id: int,
    cuenta_id: int = Query(..., description="Cuenta del plan a consultar."),
    fecha_desde: date = Query(...),
    fecha_hasta: date = Query(...),
    db: Session = Depends(get_db),
) -> LibroMayorOut:
    _empresa_or_404(db, empresa_id)
    cuenta = db.get(Cuenta, cuenta_id)
    if cuenta is None or cuenta.empresa_id != empresa_id:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada en la empresa.")
    if fecha_desde > fecha_hasta:
        raise DomainError("RANGO_INVALIDO", "La fecha inicial no puede ser posterior a la final.")
    return LibroMayorOut.model_validate(
        reporting.libro_mayor(db, cuenta, fecha_desde, fecha_hasta)
    )


@router.post("/empresas/{empresa_id}/terceros", response_model=TerceroOut, status_code=201)
def crear_tercero(empresa_id: int, payload: TerceroCreate, db: Session = Depends(get_db)) -> Tercero:
    _empresa_or_404(db, empresa_id)
    tercero = Tercero(empresa_id=empresa_id, **payload.model_dump())
    db.add(tercero)
    db.commit()
    db.refresh(tercero)
    return tercero


@router.get("/empresas/{empresa_id}/terceros", response_model=list[TerceroOut])
def listar_terceros(empresa_id: int, db: Session = Depends(get_db)) -> list[Tercero]:
    _empresa_or_404(db, empresa_id)
    return list(db.scalars(select(Tercero).where(Tercero.empresa_id == empresa_id).order_by(Tercero.nombre)).all())


@router.post("/empresas/{empresa_id}/comprobantes", response_model=ComprobanteOut, status_code=201)
def crear_comprobante(
    empresa_id: int, payload: ComprobanteCreate, db: Session = Depends(get_db)
) -> ComprobanteOut:
    _empresa_or_404(db, empresa_id)
    comprobante = accounting.crear_comprobante_borrador(
        db,
        empresa_id=empresa_id,
        fecha=payload.fecha,
        descripcion=payload.descripcion,
        lineas_in=payload.lineas,
    )
    db.commit()
    return _comprobante_out(comprobante)


@router.get("/empresas/{empresa_id}/comprobantes", response_model=list[ComprobanteOut])
def listar_comprobantes(
    empresa_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[ComprobanteOut]:
    _empresa_or_404(db, empresa_id)
    comprobantes = db.scalars(
        select(Comprobante)
        .options(
            selectinload(Comprobante.lineas).selectinload(LineaContable.cuenta),
            selectinload(Comprobante.periodo),
        )
        .where(Comprobante.empresa_id == empresa_id)
        .order_by(Comprobante.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return [_comprobante_out(c) for c in comprobantes]


@router.get("/comprobantes/{comprobante_id}", response_model=ComprobanteOut)
def obtener_comprobante(comprobante_id: int, db: Session = Depends(get_db)) -> ComprobanteOut:
    return _comprobante_out(_comprobante_or_404(db, comprobante_id))


@router.put("/comprobantes/{comprobante_id}", response_model=ComprobanteOut)
def actualizar_comprobante(
    comprobante_id: int, payload: ComprobanteUpdate, db: Session = Depends(get_db)
) -> ComprobanteOut:
    comprobante = _comprobante_or_404(db, comprobante_id)
    actualizado = accounting.actualizar_comprobante_borrador(
        db,
        comprobante,
        fecha=payload.fecha,
        descripcion=payload.descripcion,
        lineas_in=payload.lineas,
    )
    db.commit()
    return _comprobante_out(actualizado)


@router.post("/comprobantes/{comprobante_id}/contabilizar", response_model=ComprobanteOut)
def contabilizar_comprobante(comprobante_id: int, db: Session = Depends(get_db)) -> ComprobanteOut:
    comprobante = _comprobante_or_404(db, comprobante_id)
    contabilizado = accounting.contabilizar(db, comprobante)
    db.commit()
    return _comprobante_out(contabilizado)


def _respuesta_xml(generacion: ExogenaGeneracion) -> Response:
    return Response(
        content=generacion.xml,
        media_type="application/xml",
        headers={
            "Content-Disposition": f'attachment; filename="{generacion.nombre_archivo}"',
            # Permite al cliente guardar el identificador de la generación tras la descarga.
            "X-Generacion-Id": str(generacion.id),
            "Access-Control-Expose-Headers": "Content-Disposition, X-Generacion-Id",
        },
    )


@router.post("/exogena/generar")
def generar_exogena(payload: ExogenaGenerarIn, db: Session = Depends(get_db)) -> Response:
    """Genera el XML del año gravable y lo retorna como descarga directa.

    El identificador de la generación viaja en la cabecera `X-Generacion-Id` porque
    el cuerpo de la respuesta es el archivo, no un JSON.
    """
    generacion = exogena.generar(
        db,
        empresa_id=payload.empresa_id,
        anio=payload.anio_gravable,
        umbral_uvt=Decimal(payload.umbral_uvt),
    )
    db.commit()
    return _respuesta_xml(generacion)


@router.get("/exogena/historial", response_model=list[ExogenaGeneracionOut])
def listar_historial_exogena(
    empresa_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[ExogenaGeneracionOut]:
    return [
        ExogenaGeneracionOut.model_validate(g) for g in exogena.listar_generaciones(db, empresa_id)
    ]


@router.get("/exogena/historial/{generacion_id}/archivo")
def descargar_exogena(generacion_id: int, db: Session = Depends(get_db)) -> Response:
    """Re-descarga de una generación previa a partir de su identificador."""
    generacion = db.get(ExogenaGeneracion, generacion_id)
    if generacion is None:
        raise HTTPException(status_code=404, detail="Generación no encontrada.")
    return _respuesta_xml(generacion)


@router.post("/uvt/sincronizar", status_code=202)
def sincronizar_uvt(
    tareas: BackgroundTasks,
    anio: int = Query(..., ge=2000, le=2100),
) -> dict[str, str]:
    """Encola la consulta a la fuente externa y responde de inmediato.

    La petición no espera a la fuente: la tarea corre en segundo plano con su propia
    sesión, reintenta ante fallos transitorios y deja registro de la ejecución.
    """
    tareas.add_task(uvt.sincronizar_en_segundo_plano, anio)
    return {
        "estado": "encolada",
        "detalle": f"Sincronización de la UVT {anio} en curso. "
        "Consulte GET /api/uvt/sincronizaciones para ver el resultado.",
    }


@router.get("/uvt", response_model=list[UvtValorOut])
def listar_uvt(db: Session = Depends(get_db)) -> list[UvtValorOut]:
    return [UvtValorOut.model_validate(v) for v in uvt.listar_valores(db)]


@router.get("/uvt/sincronizaciones", response_model=list[UvtSincronizacionOut])
def listar_sincronizaciones_uvt(db: Session = Depends(get_db)) -> list[UvtSincronizacionOut]:
    return [UvtSincronizacionOut.model_validate(s) for s in uvt.listar_sincronizaciones(db)]


@router.post("/comprobantes/{comprobante_id}/revertir", response_model=ComprobanteOut, status_code=201)
def revertir_comprobante(
    comprobante_id: int,
    payload: ReversionCreate | None = None,
    db: Session = Depends(get_db),
) -> ComprobanteOut:
    """Crea y contabiliza el comprobante espejo que anula al original."""
    comprobante = _comprobante_or_404(db, comprobante_id)
    datos = payload or ReversionCreate()
    reversion = accounting.revertir(
        db,
        comprobante,
        fecha=datos.fecha,
        descripcion=datos.descripcion,
    )
    db.commit()
    return _comprobante_out(reversion)
