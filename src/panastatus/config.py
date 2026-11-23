"""Configuración de PanaStatus.

Hay dos fuentes de configuración, separadas a propósito:

1. ``Settings``: valores de *entorno* (secretos, URLs de conexión). Vienen de variables de
   entorno o del archivo ``.env``, que nunca se sube a git.
2. ``MonitorConfig``: *qué* se monitorea (config/services.yaml). Esto sí va en git: es
   público y cualquiera puede revisar qué páginas consultamos y con qué frecuencia.

Pydantic valida ambas al arrancar: si algo está mal (un intervalo de 10 segundos, una
categoría inexistente, un id duplicado) el programa falla de inmediato con un mensaje
claro, en vez de fallar raro horas después.
"""

from __future__ import annotations

from datetime import timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Annotated

import yaml
from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from panastatus import __version__

# Panamá está en UTC-5 todo el año (no tiene horario de verano), así que un offset fijo
# basta y evitamos depender de la base de datos de zonas horarias del sistema.
PANAMA_TZ = timezone(timedelta(hours=-5), "America/Panama")


class Settings(BaseSettings):
    """Valores de entorno. Cada campo se lee de la variable con el mismo nombre en mayúsculas."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True,  # ADMIN_CHAT_ID= (vacío) se trata como "no definido"
    )

    database_url: str = "postgresql://panastatus:panastatus@localhost:5432/panastatus"
    telegram_bot_token: str | None = None
    admin_chat_id: int | None = None

    monitor_contact: str = ""
    public_url: str = "http://localhost:8000"
    services_file: Path = Path("config/services.yaml")
    # Orígenes con permiso CORS (solo desarrollo), separados por coma en el .env:
    # CORS_ORIGINS=http://localhost:3000
    cors_origins: Annotated[list[str], NoDecode] = []

    # Caída confirmada = N fallas seguidas. Con 2 evitamos falsas alarmas por un
    # timeout aislado (un paquete perdido, un reinicio rápido del servidor, etc.).
    failure_threshold: int = Field(2, ge=1)
    # Igual para lentitud: N revisiones lentas seguidas antes de avisar.
    slow_consecutive: int = Field(2, ge=1)
    request_timeout_seconds: float = Field(15.0, gt=0)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [o.strip() for o in value.split(",") if o.strip()]
        return value

    @property
    def user_agent(self) -> str:
        """User-Agent identificable, con la convención de los bots profesionales
        (como Googlebot): "+URL" apunta a una página que explica qué es el bot y cómo
        pedir la exclusión, y además va el correo de contacto directo.

        Ejemplo: PanaStatusBot/0.1 (+https://panastatus.com/bot/; contacto@...)
        """
        contact = self.monitor_contact or "sin-contacto"
        base = self.public_url.rstrip("/")
        return f"PanaStatusBot/{__version__} (+{base}/bot/; {contact})"


class ServiceConfig(BaseModel):
    """Un servicio a monitorear (una entrada de services.yaml)."""

    # El id se usa en la DB, en la API y en los botones del bot (Telegram limita
    # callback_data a 64 bytes, por eso el máximo de 40 caracteres).
    id: str = Field(pattern=r"^[a-z0-9-]{2,40}$")
    name: str = Field(min_length=1, max_length=80)
    category: str
    url: HttpUrl
    # Regla de monitoreo responsable aplicada en código: entre 1 y 5 minutos.
    interval_seconds: int = Field(180, ge=60, le=300)
    slow_threshold_ms: int = Field(3000, ge=100)
    enabled: bool = True


class MonitorConfig(BaseModel):
    """Contenido completo de services.yaml."""

    categories: dict[str, str]
    services: list[ServiceConfig]

    @model_validator(mode="after")
    def _validate_references(self) -> MonitorConfig:
        seen: set[str] = set()
        for service in self.services:
            if service.id in seen:
                raise ValueError(f"id de servicio duplicado: {service.id}")
            seen.add(service.id)
            if service.category not in self.categories:
                raise ValueError(
                    f"{service.id}: la categoría '{service.category}' no existe en 'categories'"
                )
        return self

    @property
    def enabled_services(self) -> list[ServiceConfig]:
        return [s for s in self.services if s.enabled]


def load_monitor_config(path: Path) -> MonitorConfig:
    with open(path, encoding="utf-8") as f:
        return MonitorConfig.model_validate(yaml.safe_load(f))


@lru_cache
def get_settings() -> Settings:
    """Settings se crea una sola vez por proceso (lru_cache) y se reutiliza."""
    return Settings()
