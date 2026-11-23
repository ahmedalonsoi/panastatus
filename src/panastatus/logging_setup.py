"""Logs en formato JSON (una línea = un objeto JSON).

¿Por qué JSON y no texto plano? En la Fase 3 los logs van a Loki/Grafana, y ahí se
puede filtrar por campo: ``{service="worker"} | json | service_id="banistmo"``.
Para agregar campos a un log se usa ``extra``:

    log.info("revisión", extra={"service_id": "utp", "latency_ms": 230})
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

# Atributos que trae todo LogRecord; lo que no esté aquí vino por "extra".
_STANDARD_ATTRS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {
    "message",
    "asctime",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS:
                data[key] = value
        if record.exc_info:
            data["exc"] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=False, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
    # httpx registra cada petición en INFO; demasiado ruido (y expondría el token de
    # Telegram, que va en la URL). Solo advertencias.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
