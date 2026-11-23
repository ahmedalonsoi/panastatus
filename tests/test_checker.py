"""Tests del checker con respuestas HTTP simuladas (respx): sin red real."""

import httpx
import pytest
import respx

from panastatus.checker import check_service
from panastatus.config import ServiceConfig

SERVICE = ServiceConfig(id="demo", name="Demo", category="x", url="https://demo.example")


@respx.mock
async def test_respuesta_200_es_ok():
    respx.get("https://demo.example/").mock(return_value=httpx.Response(200))
    async with httpx.AsyncClient() as client:
        result = await check_service(client, SERVICE)
    assert result.ok
    assert result.status_code == 200
    assert result.latency_ms is not None
    assert result.error is None


@respx.mock
async def test_error_500_es_falla():
    respx.get("https://demo.example/").mock(return_value=httpx.Response(503))
    async with httpx.AsyncClient() as client:
        result = await check_service(client, SERVICE)
    assert not result.ok
    assert result.error == "HTTP 503"


@respx.mock
async def test_timeout_es_falla_sin_excepcion():
    respx.get("https://demo.example/").mock(side_effect=httpx.ReadTimeout("lento"))
    async with httpx.AsyncClient() as client:
        result = await check_service(client, SERVICE)
    assert not result.ok
    assert result.error == "Tiempo de espera agotado"


@respx.mock
async def test_error_de_dns():
    respx.get("https://demo.example/").mock(
        side_effect=httpx.ConnectError("[Errno 11001] getaddrinfo failed")
    )
    async with httpx.AsyncClient() as client:
        result = await check_service(client, SERVICE)
    assert result.error == "Error de DNS: el dominio no resuelve"


@pytest.mark.parametrize("interval", [30, 59, 301, 3600])
def test_intervalos_fuera_de_1_a_5_minutos_se_rechazan(interval):
    with pytest.raises(ValueError):
        ServiceConfig(
            id="demo",
            name="Demo",
            category="x",
            url="https://x.example",
            interval_seconds=interval,
        )
