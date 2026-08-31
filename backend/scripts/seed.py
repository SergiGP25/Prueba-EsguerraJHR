from __future__ import annotations

"""Carga datos mínimos para probar los escenarios del enunciado (compra y desbalance)."""

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Cuenta, Empresa, NaturalezaCuenta, Periodo, Tercero


def seed() -> None:
    db = SessionLocal()
    try:
        existente = db.scalar(select(Empresa).where(Empresa.nit == "900123456"))
        if existente:
            print(f"Empresa ya existe (id={existente.id}). No se duplica el seed.")
            return

        empresa = Empresa(nit="900123456", dv="1", razon_social="Esguerra Demo S.A.S.")
        db.add(empresa)
        db.flush()

        cuentas = [
            Cuenta(empresa_id=empresa.id, codigo="5105", nombre="Gasto operacional", naturaleza=NaturalezaCuenta.DEBITO),
            Cuenta(empresa_id=empresa.id, codigo="2408", nombre="IVA descontable", naturaleza=NaturalezaCuenta.DEBITO),
            Cuenta(empresa_id=empresa.id, codigo="2205", nombre="Proveedores", naturaleza=NaturalezaCuenta.CREDITO),
            Cuenta(empresa_id=empresa.id, codigo="1105", nombre="Caja", naturaleza=NaturalezaCuenta.DEBITO),
            Cuenta(empresa_id=empresa.id, codigo="4135", nombre="Ingresos", naturaleza=NaturalezaCuenta.CREDITO),
        ]
        db.add_all(cuentas)

        db.add(Tercero(empresa_id=empresa.id, tipo_doc="NIT", num_doc="800111222", nombre="Proveedor Ejemplo S.A.S."))
        db.add(Periodo(empresa_id=empresa.id, anio=2025, mes=1))
        db.add(Periodo(empresa_id=empresa.id, anio=2025, mes=2))
        db.commit()
        print(f"Seed OK. Empresa id={empresa.id}")
        print("Cuentas: 5105 Gasto, 2408 IVA, 2205 Proveedores, 1105 Caja, 4135 Ingresos")
        print("Períodos abiertos: 2025-01 y 2025-02")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
