from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Comprobante, Cuenta, Empresa, Periodo, Tercero
from app.schemas import (
    ComprobanteCreate,
    ComprobanteOut,
    ComprobanteUpdate,
    CuentaCreate,
    CuentaOut,
    CuentaUpdate,
    EmpresaCreate,
    EmpresaOut,
    PeriodoCreate,
    PeriodoOut,
    TerceroCreate,
    TerceroOut,
)
from app.services import accounting

router = APIRouter(prefix="/api")


def _comprobante_out(comprobante: Comprobante) -> ComprobanteOut:
    total_debito, total_credito = accounting.totales(comprobante)
    payload = ComprobanteOut.model_validate(comprobante)
    return payload.model_copy(update={"total_debito": total_debito, "total_credito": total_credito})


def _empresa_or_404(db: Session, empresa_id: int) -> Empresa:
    empresa = db.get(Empresa, empresa_id)
    if empresa is None:
        raise HTTPException(status_code=404, detail="Empresa no encontrada.")
    return empresa


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
def listar_comprobantes(empresa_id: int, db: Session = Depends(get_db)) -> list[ComprobanteOut]:
    _empresa_or_404(db, empresa_id)
    ids = list(db.scalars(select(Comprobante.id).where(Comprobante.empresa_id == empresa_id).order_by(Comprobante.id)).all())
    return [_comprobante_out(accounting.cargar_comprobante(db, cid)) for cid in ids]


@router.get("/comprobantes/{comprobante_id}", response_model=ComprobanteOut)
def obtener_comprobante(comprobante_id: int, db: Session = Depends(get_db)) -> ComprobanteOut:
    comprobante = accounting.cargar_comprobante(db, comprobante_id)
    if comprobante is None:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado.")
    return _comprobante_out(comprobante)


@router.put("/comprobantes/{comprobante_id}", response_model=ComprobanteOut)
def actualizar_comprobante(
    comprobante_id: int, payload: ComprobanteUpdate, db: Session = Depends(get_db)
) -> ComprobanteOut:
    comprobante = accounting.cargar_comprobante(db, comprobante_id)
    if comprobante is None:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado.")
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
    comprobante = accounting.cargar_comprobante(db, comprobante_id)
    if comprobante is None:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado.")
    contabilizado = accounting.contabilizar(db, comprobante)
    db.commit()
    return _comprobante_out(contabilizado)
