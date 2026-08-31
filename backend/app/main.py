from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router
from app.config import settings
from app.core.exceptions import DomainError, domain_error_handler

app = FastAPI(
    title="Motor contable",
    description=(
        "Módulo contable: plan de cuentas, comprobantes con partida doble, "
        "reversión, libro mayor e información exógena."
    ),
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origenes_permitidos,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # El frontend lee el nombre del archivo y el id de la generación de exógena.
    expose_headers=["Content-Disposition", "X-Generacion-Id"],
)
app.add_exception_handler(DomainError, domain_error_handler)
app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
