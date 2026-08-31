from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.core.money import parse_money
from app.models.enums import EstadoComprobante, EstadoPeriodo, NaturalezaCuenta

# El API expone dinero como string para que JSON no lo convierta a float (IEEE-754).
MoneyStr = Annotated[str, Field(examples=["1000000.00"])]


class MoneyMixin(BaseModel):
    @field_serializer("debito", "credito", "total_debito", "total_credito", "diferencia", check_fields=False)
    def serialize_money(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
        return format(value, "f")


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
    nombre: str = Field(min_length=1, max_length=255)


class TerceroOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: int
    tipo_doc: str
    num_doc: str
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
    debito: Decimal
    credito: Decimal
    descripcion: str | None

    @field_serializer("debito", "credito")
    def serialize_amounts(self, value: Decimal) -> str:
        return format(value, "f")


class ComprobanteCreate(BaseModel):
    fecha: date
    descripcion: str = Field(min_length=1)
    lineas: list[LineaIn] = Field(default_factory=list)


class ComprobanteUpdate(BaseModel):
    fecha: date | None = None
    descripcion: str | None = Field(default=None, min_length=1)
    lineas: list[LineaIn] | None = None


class ComprobanteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: int
    periodo_id: int
    numero: int | None
    fecha: date
    descripcion: str
    estado: EstadoComprobante
    lineas: list[LineaOut]
    total_debito: Decimal = Decimal("0.00")
    total_credito: Decimal = Decimal("0.00")

    @field_serializer("total_debito", "total_credito")
    def serialize_totals(self, value: Decimal) -> str:
        return format(value, "f")
