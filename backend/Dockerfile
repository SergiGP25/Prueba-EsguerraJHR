# Imagen del backend. La etapa `dev` añade las dependencias de prueba y la usa CI/pytest;
# la etapa final `runtime` es la que se publica y ejecuta en docker compose.
FROM python:3.12-slim AS base

# No se define PYTHONPATH=/app a propósito: el directorio `alembic/` de las migraciones
# taparía al paquete instalado del mismo nombre. Los scripts se ejecutan como módulos
# (`python -m scripts.seed`), que sí añade el directorio de trabajo a sys.path.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini pyproject.toml ./
COPY alembic ./alembic
COPY app ./app
COPY scripts ./scripts


FROM base AS dev

COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY tests ./tests


FROM base AS runtime

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh \
    && useradd --create-home --uid 1000 contable \
    && chown -R contable:contable /app
USER contable

EXPOSE 8000
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
