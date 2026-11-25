"""Avisos por Telegram: formato del mensaje y manejo de las respuestas de la API.

La API de Telegram se simula con respx (sin red) y ``asyncio.sleep`` se reemplaza para
que los reintentos no hagan esperar a la suite.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx

from panastatus import db, notifier
from panastatus.checker import CheckResult
from panastatus.config import ServiceConfig, Settings
from panastatus.notifier import Notifier, format_duration, format_message
from panastatus.state import Event

TOKEN = "123:abc"
SEND_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
ADMIN = 1000
SERVICE = ServiceConfig(id="utp", name="UTP <Sede>", category="educacion", url="https://utp.ac.pa")
T0 = datetime(2026, 11, 24, 17, 0, tzinfo=UTC)  # 12:00 en Panamá


def _result(ok: bool = False, error: str | None = "HTTP 503", latency: int | None = None):
    return CheckResult("utp", T0, ok, 503 if not ok else 200, latency, error, 60)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    async def instant(_seconds):
        return None

    monkeypatch.setattr(notifier.asyncio, "sleep", instant)


@pytest.fixture
def deleted(monkeypatch) -> list[int]:
    """Registra los chat_id que el notificador borra (en vez de tocar una DB real)."""
    calls: list[int] = []

    async def delete_subscriber(_pool, chat_id):
        calls.append(chat_id)

    monkeypatch.setattr(db, "delete_subscriber", delete_subscriber)
    return calls


def _notifier(client: httpx.AsyncClient, token: str | None = TOKEN) -> Notifier:
    settings = Settings(telegram_bot_token=token, admin_chat_id=ADMIN, _env_file=None)
    return Notifier(settings, pool=None, client=client)


# --- Formato -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("td", "expected"),
    [
        (timedelta(seconds=42), "42 s"),
        (timedelta(minutes=7), "7 min"),
        (timedelta(hours=2, minutes=5), "2 h 5 min"),
    ],
)
def test_format_duration(td, expected):
    assert format_duration(td) == expected


def test_caida_escapa_html_y_usa_hora_de_panama():
    text = format_message(Event.DOWN, SERVICE, _result(error="<script>"), {"started_at": T0})
    assert "UTP &lt;Sede&gt; está caído" in text  # el nombre no rompe el HTML de Telegram
    assert "&lt;script&gt;" in text
    assert "12:00 (hora de Panamá)" in text


def test_recuperacion_incluye_duracion():
    incident = {"started_at": T0, "duration": timedelta(minutes=18)}
    text = format_message(Event.RECOVERED, SERVICE, _result(ok=True, error=None), incident)
    assert "se recuperó" in text and "18 min" in text


def test_lentitud_compara_con_el_umbral():
    text = format_message(Event.SLOW, SERVICE, _result(ok=True, error=None, latency=4200), None)
    assert "4200 ms" in text and str(SERVICE.slow_threshold_ms) in text


# --- Envío -------------------------------------------------------------------


@respx.mock
async def test_envio_exitoso():
    route = respx.post(SEND_URL).mock(return_value=httpx.Response(200, json={"ok": True}))
    async with httpx.AsyncClient() as client:
        await _notifier(client).send(42, "hola")
    assert route.call_count == 1
    body = route.calls[0].request.content.decode()
    assert '"chat_id":42' in body.replace(" ", "") and '"parse_mode":"HTML"' in body.replace(
        " ", ""
    )


@respx.mock
async def test_429_respeta_retry_after_y_reintenta():
    route = respx.post(SEND_URL).mock(
        side_effect=[
            httpx.Response(429, json={"parameters": {"retry_after": 3}}),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    async with httpx.AsyncClient() as client:
        await _notifier(client).send(42, "hola")
    assert route.call_count == 2


@respx.mock
async def test_error_de_red_reintenta_como_maximo_3_veces():
    route = respx.post(SEND_URL).mock(side_effect=httpx.ConnectError("sin red"))
    async with httpx.AsyncClient() as client:
        await _notifier(client).send(42, "hola")  # no lanza: un aviso fallido no tumba el worker
    assert route.call_count == 3


@respx.mock
async def test_403_de_suscriptor_lo_borra(deleted):
    respx.post(SEND_URL).mock(return_value=httpx.Response(403))
    async with httpx.AsyncClient() as client:
        await _notifier(client).send(42, "hola")
    assert deleted == [42]


@respx.mock
async def test_403_del_admin_nunca_lo_borra(deleted):
    respx.post(SEND_URL).mock(return_value=httpx.Response(403))
    async with httpx.AsyncClient() as client:
        await _notifier(client).send(ADMIN, "hola")
    assert deleted == []


async def test_sin_token_no_llama_a_telegram():
    async with httpx.AsyncClient() as client, respx.mock(assert_all_called=False) as mock:
        route = mock.post(SEND_URL)
        await _notifier(client, token=None).send(42, "hola")
    assert route.call_count == 0


@respx.mock
async def test_notify_no_duplica_el_aviso_al_admin_suscrito(monkeypatch):
    async def subscribers_for(_pool, _service_id):
        return [ADMIN, 7, 8]

    monkeypatch.setattr(db, "subscribers_for", subscribers_for)
    route = respx.post(SEND_URL).mock(return_value=httpx.Response(200, json={"ok": True}))
    async with httpx.AsyncClient() as client:
        await _notifier(client).notify(Event.DOWN, SERVICE, _result(), {"started_at": T0})
    chat_ids = sorted(
        int(c.request.content.decode().split('"chat_id":')[1].split(",")[0]) for c in route.calls
    )
    assert chat_ids == [7, 8, ADMIN]  # el admin recibe UNA sola vez
