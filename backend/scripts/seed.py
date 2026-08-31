"""Carga datos mínimos para reproducir los escenarios del enunciado.

Es idempotente: si la empresa demo ya existe, no vuelve a insertar nada.
"""

from __future__ import annotations

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Cuenta, Empresa, NaturalezaCuenta, Periodo, Tercero
from app.services import uvt

NIT_DEMO = "900123456"

# Plan de cuentas mínimo para los escenarios del enunciado.
CUENTAS = [
    ("1105", "Caja", NaturalezaCuenta.DEBITO),
    ("2205", "Proveedores", NaturalezaCuenta.CREDITO),
    ("2365", "Retención en la fuente por pagar", NaturalezaCuenta.CREDITO),
    ("2408", "IVA descontable", NaturalezaCuenta.DEBITO),
    ("4135", "Ingresos operacionales", NaturalezaCuenta.CREDITO),
    ("5105", "Gasto operacional", NaturalezaCuenta.DEBITO),
]

TERCEROS = [
    ("NIT", "800197268", "4", "Proveedor Ejemplo S.A.S."),
    ("NIT", "830053105", "3", "Cliente Menor S.A.S."),
]


def seed() -> None:
    db = SessionLocal()
    try:
        existente = db.scalar(select(Empresa).where(Empresa.nit == NIT_DEMO))
        if existente:
            print(f"Empresa ya existe (id={existente.id}). No se duplica el seed.")
            return

        # DV calculado con el algoritmo DIAN: la exógena rechaza informantes con DV inconsistente.
        empresa = Empresa(nit=NIT_DEMO, dv="8", razon_social="Esguerra Demo S.A.S.")
        db.add(empresa)
        db.flush()

        db.add_all(
            [
                Cuenta(empresa_id=empresa.id, codigo=codigo, nombre=nombre, naturaleza=naturaleza)
                for codigo, nombre, naturaleza in CUENTAS
            ]
        )
        db.add_all(
            [
                Tercero(
                    empresa_id=empresa.id,
                    tipo_doc=tipo_doc,
                    num_doc=num_doc,
                    dv=dv,
                    nombre=nombre,
                )
                for tipo_doc, num_doc, dv, nombre in TERCEROS
            ]
        )
        db.add(Periodo(empresa_id=empresa.id, anio=2025, mes=1))
        db.add(Periodo(empresa_id=empresa.id, anio=2025, mes=2))

        # Deja la UVT lista para que la exógena funcione sin pasos previos.
        for anio in (2024, 2025, 2026):
            uvt.sincronizar(db, anio, proveedor=uvt.ProveedorUvtSimulado(), espera_segundos=0)

        db.commit()
        print(f"Seed OK. Empresa id={empresa.id} (NIT {NIT_DEMO}-8)")
        print("Cuentas: " + ", ".join(f"{codigo} {nombre}" for codigo, nombre, _ in CUENTAS))
        print("Períodos abiertos: 2025-01 y 2025-02")
        print("UVT sincronizada para 2024, 2025 y 2026.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
