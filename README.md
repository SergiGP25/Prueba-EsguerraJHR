"""
# Motor contable — Prueba técnica

Stack: FastAPI · PostgreSQL · Next.js (frontend a partir del Día 3).

Este README se irá completando cada día. Hoy cubre **Día 1: dominio y reglas de negocio**.

## Qué hay implementado (Día 1)

- Plan de cuentas (CRUD básico).
- Comprobantes en **borrador**, edición y **contabilización atómica**.
- Cierre de período (bloquea nuevos comprobantes de ese mes).
- Validación de partida doble, cuentas activas, valores monetarios y líneas inválidas.

Aún no hay: libro mayor, reversión, frontend ni exógena (Días 2–4).

## Levantar en local

Requisitos: Docker Desktop, Python 3.9+ (en 3.9 se usa `eval-type-backport` para anotaciones modernas).

```bash
cp .env.example .env
docker compose up -d
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
PYTHONPATH=. python scripts/seed.py
uvicorn app.main:app --reload --app-dir .
```

API: http://127.0.0.1:8000  
Docs: http://127.0.0.1:8000/docs

## Cómo probar el corte del Día 1

Con el seed, la empresa tiene `id=1`. Cuentas típicas:

| id (aprox.) | código | nombre |
|-------------|--------|--------|
| 1 | 5105 | Gasto operacional |
| 2 | 2408 | IVA descontable |
| 3 | 2205 | Proveedores |
| 4 | 1105 | Caja |
| 5 | 4135 | Ingresos |

Confirma ids reales con `GET /api/empresas/1/cuentas`.

### 1. Comprobante válido (compra) — debe contabilizar

`POST /api/empresas/1/comprobantes`

```json
{
  "fecha": "2025-01-15",
  "descripcion": "Compra de insumos",
  "lineas": [
    { "cuenta_id": 1, "debito": "1000000.00", "credito": "0.00" },
    { "cuenta_id": 2, "debito": "190000.00", "credito": "0.00" },
    { "cuenta_id": 3, "debito": "0.00", "credito": "1190000.00", "tercero_id": 1 }
  ]
}
```

Luego `POST /api/comprobantes/{id}/contabilizar`. Debe devolver `estado: contabilizado` y un `numero`.

### 2. Desbalanceado — debe rechazar

Crea un borrador Caja 500000 / Ingresos 450000 y contabiliza. Respuesta `422` con código `PARTIDA_DOBLE`.

### 3. Período cerrado — debe rechazar

`POST /api/periodos/{id}/cerrar` sobre 2025-01 y luego intenta crear o contabilizar un comprobante de enero 2025. Código `PERIODO_CERRADO`.

Los montos van como **string** en JSON (`"1000000.00"`), no como number, para no perder precisión en IEEE-754.

## Decisiones de diseño (Día 1)

- **Dinero:** `NUMERIC(18,2)` en PostgreSQL y `Decimal` en Python. El API serializa montos como string.
- **Plan de cuentas plano:** código + nombre + naturaleza + activa. Sin jerarquía PUCx todavía; se puede añadir `cuenta_padre_id` después sin tocar movimientos.
- **Período derivado de la fecha:** al guardar un comprobante se obtiene o crea el período `YYYY-MM`. Si está cerrado, se rechaza.
- **Contabilizar:** una sola transacción de base de datos. Lock `FOR UPDATE` sobre el período al asignar número (base para concurrencia del Día 2).
- **Comprobante contabilizado:** no se puede editar (HTTP 409 `COMPROBANTE_PROTEGIDO`).
