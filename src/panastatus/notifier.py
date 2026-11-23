"""Envío de avisos por Telegram (caída, recuperación, lentitud).

El worker no usa la librería python-telegram-bot: para *enviar* basta un POST a la API
HTTP de Telegram. El bot interactivo (bot.py) es un proceso aparte. Así, si el bot se
cae, las alertas siguen saliendo.

A quién se envía:
- Al admin (ADMIN_CHAT_ID): todos los eventos de todos los servicios.
- A los suscriptores del servicio que no estén en /silencio.
"""

from __future__ import annotations

import asyncio
import html
import logging
from datetime import timedelta

import asyncpg
import httpx

from panastatus import db
from panastatus.checker import CheckResult
from panastatus.config import PANAMA_TZ, ServiceConfig, Settings
from panastatus.state import Event

log = logging.getLogger(__name__)


def format_duration(td: timedelta) -> str:
    total = int(td.total_seconds())
    hours, rem = divmod(total, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours:
        return f"{hours} h {minutes} min"
    if minutes:
        return f"{minutes} min"
    return f"{seconds} s"


def format_message(
    event: Event,
    service: ServiceConfig,
    result: CheckResult,
    incident: asyncpg.Record | dict | None,
) -> str:
    """Arma el texto del aviso (HTML de Telegram). html.escape evita que un nombre o un
    mensaje de error con < > & rompa el formato."""
    name = html.escape(service.name)
    if event is Event.DOWN:
        since = incident["started_at"] if incident else result.time
        return (
            f"🔴 <b>{name} está caído</b>\n"
            f"Error: {html.escape(result.error or 'desconocido')}\n"
            f"Desde: {since.astimezone(PANAMA_TZ):%H:%M} (hora de Panamá)\n"
            f"{html.escape(str(service.url))}"
        )
    if event is Event.RECOVERED:
        duration = ""
        if incident and incident["duration"] is not None:
            duration = f"\nDuración de la caída: {format_duration(incident['duration'])}"
        return f"🟢 <b>{name} se recuperó</b>{duration}"
    # Event.SLOW
    return (
        f"🟡 <b>{name} está lento</b>\n"
        f"Latencia: {result.latency_ms} ms (normal: menos de {service.slow_threshold_ms} ms)"
    )


class Notifier:
    def __init__(self, settings: Settings, pool: asyncpg.Pool, client: httpx.AsyncClient):
        self.settings = settings
        self.pool = pool
        self.client = client

    async def notify(
        self,
        event: Event,
        service: ServiceConfig,
        result: CheckResult,
        incident: asyncpg.Record | None,
    ) -> None:
        text = format_message(event, service, result, incident)
        log.info("evento", extra={"event": str(event), "service_id": service.id})

        admin = self.settings.admin_chat_id
        if admin:
            await self.send(admin, text)

        for chat_id in await db.subscribers_for(self.pool, service.id):
            if chat_id == admin:
                continue  # ya lo recibió
            await self.send(chat_id, text)
            await asyncio.sleep(0.05)  # Telegram permite ~30 mensajes/s; vamos holgados

    async def send(self, chat_id: int, text: str) -> None:
        token = self.settings.telegram_bot_token
        if not token:
            log.info("telegram desactivado; aviso solo en log", extra={"text": text})
            return

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        for attempt in range(3):
            try:
                response = await self.client.post(url, json=payload)
            except httpx.HTTPError as exc:
                log.warning("fallo enviando a telegram", extra={"error": str(exc)})
                await asyncio.sleep(2 * (attempt + 1))
                continue

            if response.status_code == 200:
                return
            if response.status_code == 429:
                # Telegram nos dice cuánto esperar.
                retry_after = response.json().get("parameters", {}).get("retry_after", 5)
                await asyncio.sleep(retry_after)
                continue
            if response.status_code == 403 and chat_id != self.settings.admin_chat_id:
                # El usuario bloqueó el bot o lo sacaron del grupo: borramos su chat_id.
                await db.delete_subscriber(self.pool, chat_id)
                log.info("suscriptor eliminado (403)", extra={"chat_id": chat_id})
                return
            log.warning(
                "telegram rechazó el mensaje",
                extra={"status": response.status_code, "body": response.text[:300]},
            )
            return
