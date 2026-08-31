"""Infraestructura de pruebas.

Se usa PostgreSQL real (no SQLite) porque el dominio depende de enums nativos,
`NUMERIC(18,2)` y `SELECT ... FOR UPDATE`: probar contra otro motor validaría
un comportamiento distinto al de producción.

Aislamiento: cada test corre dentro de una transacción externa que se revierte al
final, de modo que el esquema se migra una sola vez por sesión.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_TEST_URL = "postgresql+psycopg://contable:contable@localhost:5433/contable_test"
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", DEFAULT_TEST_URL)

# app.config lee la URL al importarse: se fija antes de importar cualquier módulo de la app.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app.db import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    Cuenta,
    Empresa,
    NaturalezaCuenta,
    Periodo,
    Tercero,
)


def _crear_base_si_falta(url: str) -> None:
    """Crea la base de pruebas conectándose a `postgres` (no se puede crear desde sí misma)."""
    destino = make_url(url)
    admin = create_engine(destino.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        existe = conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": destino.database})
        if not existe:
            conn.execute(text(f'CREATE DATABASE "{destino.database}"'))
    admin.dispose()


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    _crear_base_si_falta(TEST_DATABASE_URL)
    eng = create_engine(TEST_DATABASE_URL)
    # El esquema se construye desde los modelos: las migraciones se validan aparte
    # (el job de CI corre `alembic upgrade head` contra una base limpia).
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db(engine: Engine) -> Iterator[Session]:
    conexion = engine.connect()
    transaccion = conexion.begin()
    # `create_savepoint` hace que los `db.commit()` de los endpoints liberen un SAVEPOINT
    # en vez de cerrar la transacción externa, que es la que se revierte al terminar.
    sesion = sessionmaker(
        bind=conexion,
        autoflush=False,
        autocommit=False,
        join_transaction_mode="create_savepoint",
    )()
    try:
        yield sesion
    finally:
        sesion.close()
        transaccion.rollback()
        conexion.close()


@pytest.fixture()
def client(db: Session) -> Iterator[TestClient]:
    def _get_db_de_prueba() -> Iterator[Session]:
        # Réplica de app.db.get_db (sin cerrar la sesión, que gestiona la fixture `db`)
        # para que una petición fallida deshaga sus cambios igual que en producción.
        try:
            yield db
        except Exception:
            db.rollback()
            raise

    app.dependency_overrides[get_db] = _get_db_de_prueba
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def empresa(db: Session) -> Empresa:
    """Empresa demo con NIT de DV válido (900123456-8) y el plan de cuentas del enunciado."""
    registro = Empresa(nit="900123456", dv="8", razon_social="Esguerra Demo S.A.S.")
    db.add(registro)
    db.flush()
    plan = [
        ("1105", "Caja", NaturalezaCuenta.DEBITO),
        ("2205", "Proveedores", NaturalezaCuenta.CREDITO),
        ("2365", "Retención en la fuente por pagar", NaturalezaCuenta.CREDITO),
        ("2408", "IVA descontable", NaturalezaCuenta.DEBITO),
        ("4135", "Ingresos operacionales", NaturalezaCuenta.CREDITO),
        ("5105", "Gasto operacional", NaturalezaCuenta.DEBITO),
    ]
    db.add_all(
        [
            Cuenta(empresa_id=registro.id, codigo=codigo, nombre=nombre, naturaleza=naturaleza)
            for codigo, nombre, naturaleza in plan
        ]
    )
    db.add(Periodo(empresa_id=registro.id, anio=2025, mes=1))
    db.add(
        Tercero(
            empresa_id=registro.id,
            tipo_doc="NIT",
            num_doc="800197268",
            dv="4",
            nombre="Proveedor Ejemplo S.A.S.",
        )
    )
    db.flush()
    return registro


@pytest.fixture()
def cuentas(db: Session, empresa: Empresa) -> dict[str, Cuenta]:
    from sqlalchemy import select

    filas = db.scalars(select(Cuenta).where(Cuenta.empresa_id == empresa.id)).all()
    return {c.codigo: c for c in filas}


@pytest.fixture()
def tercero(db: Session, empresa: Empresa) -> Tercero:
    from sqlalchemy import select

    return db.scalars(select(Tercero).where(Tercero.empresa_id == empresa.id)).one()
