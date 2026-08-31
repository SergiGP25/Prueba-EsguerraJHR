from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    database_url: str = "postgresql+psycopg://contable:contable@localhost:5432/contable"

    # Orígenes autorizados del frontend, separados por coma. Configurable para no
    # dejar la URL del cliente incrustada en el código.
    cors_origins: str = "http://localhost:3000"

    @property
    def origenes_permitidos(self) -> list[str]:
        return [origen.strip() for origen in self.cors_origins.split(",") if origen.strip()]


settings = Settings()
