#!/bin/sh
# Aplica las migraciones pendientes antes de exponer la API: el contenedor arranca
# siempre con el esquema al día y `docker compose up` no requiere pasos manuales.
set -e

echo "Aplicando migraciones..."
alembic upgrade head

exec "$@"
