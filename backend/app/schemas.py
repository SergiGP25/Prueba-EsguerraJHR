from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator

from app.core.money import parse_money
from app.models.enums import EstadoComprobante, EstadoPeriodo, NaturalezaCuenta

# El API expone dinero como string para que JSON no lo convierta a float (IEEE-754).
MoneyStr = Annotated[str, Field(examples=["1000000.00"])]


def _money_a_str(value: Decimal | str | int | None) -> str | None:
    """Normaliza a string con 2 decimales. Se usa en modo `before` en los esquemas de salida.

    Declarar el campo como `str` (y no `Decimal` + serializador) hace que el OpenAPI
    publique `string`, que es lo que realmente viaja por el cable.
    """
    if value is None:
        return None
    return format(parse_money(value), "f")


MoneyOut = Annotated[str, BeforeValidator(_money_a_str), Field(examples=["1000000.00"])]


class EmpresaCreate(BaseModel):
    nit: str = Field(min_length=1, max_length=20)
    dv: str = Field(min_length=1, max_length=1)
    razon_social: str = Field(min_length=1, max_length=255)


class EmpresaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nit: str
    dv: str
    razon_social: str
    created_at: datetime


class CuentaCreate(BaseModel):
    codigo: str = Field(min_length=1, max_length=20)
    nombre: str = Field(min_length=1, max_length=255)
    naturaleza: NaturalezaCuenta
    activa: bool = True


class CuentaUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=255)
    naturaleza: NaturalezaCuenta | None = None
    activa: bool | None = None


class CuentaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: int
    codigo: str
    nombre: str
    naturaleza: NaturalezaCuenta
    activa: bool


class PeriodoCreate(BaseModel):
    anio: int = Field(ge=2000, le=2100)
    mes: int = Field(ge=1, le=12)


class PeriodoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: int
    anio: int
    mes: int
    estado: EstadoPeriodo


class TerceroCreate(BaseModel):
    tipo_doc: str = Field(default="NIT", max_length=10)
    num_doc: str = Field(min_length=1, max_length=20)
    dv: str | None = Field(default=None, min_length=1, max_length=1)
    nombre: str = Field(min_length=1, max_length=255)


class TerceroOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: int
    tipo_doc: str
    num_doc: str
    dv: str | None
    nombre: str


class LineaIn(BaseModel):
    cuenta_id: int
    tercero_id: int | None = None
    debito: MoneyStr = "0.00"
    credito: MoneyStr = "0.00"
    descripcion: str | None = Field(default=None, max_length=255)

    @field_validator("debito", "credito")
    @classmethod
    def validate_money_fields(cls, value: str) -> str:
        parsed = parse_money(value)
        return format(parsed, "f")


class LineaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cuenta_id: int
    tercero_id: int | None
    debito: MoneyOut
    credito: MoneyOut
    descripcion: str | None


class ComprobanteCreate(BaseModel):
    fecha: date
    descripcion: str = Field(min_length=1)
    lineas: list[LineaIn] = Field(default_factory=list)


class ComprobanteUpdate(BaseModel):
    fecha: date | None = None
    descripcion: str | None = Field(default=None, min_length=1)
    lineas: list[LineaIn] | None = None


class ExogenaGenerarIn(BaseModel):
    empresa_id: int
    anio_gravable: int = Field(ge=2000, le=2100)
    # El umbral se expresa en UVT; el backend lo convierte a pesos con la UVT del año.
    umbral_uvt: MoneyStr = "0.00"

    @field_validator("umbral_uvt")
    @classmethod
    def validar_umbral(cls, value: str) -> str:
        umbral = parse_money(value)
        if umbral < Decimal("0.00"):
            raise ValueError("El umbral no puede ser negativo.")
        return format(umbral, "f")


class ExclusionOut(BaseModel):
    tercero: str
    motivo: str
    valor: str


class ExogenaGeneracionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: int
    anio_gravable: int
    umbral_uvt: MoneyOut
    valor_uvt: MoneyOut
    umbral_pesos: MoneyOut
    total_registros: int
    total_valor_bruto: MoneyOut
    total_retencion: MoneyOut
    exclusiones: list[ExclusionOut]
    nombre_archivo: str
    created_at: datetime


class UvtValorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    anio: int
    valor: MoneyOut
    fuente: str
    actualizado_en: datetime


class UvtSincronizacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    anio: int
    exitosa: bool
    intentos: int
    valor: MoneyOut | None
    fuente: str
    detalle: str | None
    created_at: datetime


class MovimientoMayorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fecha: date
    comprobante_id: int
    numero: int | None
    descripcion: str
    tercero_nombre: str | None
    debito: MoneyOut
    credito: MoneyOut
    saldo: MoneyOut


class LibroMayorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cuenta: CuentaOut
    fecha_desde: date
    fecha_hasta: date
    saldo_inicial: MoneyOut
    movimientos: list[MovimientoMayorOut]
    total_debito: MoneyOut
    total_credito: MoneyOut
    saldo_final: MoneyOut


class ReversionCreate(BaseModel):
    """Parámetros opcionales de una reversión: por defecto usa la fecha del original."""

    fecha: date | None = None
    descripcion: str | None = Field(default=None, min_length=1)


class ComprobanteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: int
    periodo_id: int
    numero: int | None
    fecha: date
    descripcion: str
    estado: EstadoComprobante
    reversa_comprobante_id: int | None = None
    lineas: list[LineaOut]
    total_debito: MoneyOut = "0.00"
    total_credito: MoneyOut = "0.00"
