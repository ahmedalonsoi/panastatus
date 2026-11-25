"""Pruebas de integración contra PostgreSQL + TimescaleDB reales.

Prueban lo que un mock no puede: las restricciones del esquema (índice único parcial),
el SQL real y las migraciones. Necesitan una base YA migrada y vacía:

    TEST_DATABASE_URL=postgresql://user:pass@localhost:5432/panastatus_test

Sin esa variable se omiten (así ``pytest`` sigue funcionando sin Docker). En CI se
levanta TimescaleDB como servicio y se ejecuta ``db/migrate.sh`` antes (ver ci.yml).

ATENCIÓN: cada prueba VACÍA las tablas. Nunca apuntes TEST_DATABASE_URL a una base real.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import pytest

from panastatus import db
from panastatus.checker import CheckResult
from panastatus.config import ServiceConfig

DSN = os.environ.get("TEST_DATABASE_URL")
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DSN, reason="TEST_DATABASE_URL no definida"),
]

UTP = ServiceConfig(id="utp", name="UTP", category="educacion", url="https://utp.ac.pa")
UP = ServiceConfig(id="up", name="UP", category="educacion", url="https://www.up.ac.pa")


@pytest.fixture
async def pool():
    assert DSN is not None
    pool = await db.create_pool(DSN)
    await pool.execute(
        "TRUNCATE postmortems, incidents, checks, subscribers, services RESTART IDENTITY CASCADE"
    )
    yield pool
    await pool.close()


async def test_sync_inserta_y_desactiva_lo_que_sale_del_yaml(pool):
    await db.sync_services(pool, [UTP, UP])
    await db.sync_services(pool, [UTP])  # UP se quitó del YAML
    rows = {r["id"]: r["enabled"] for r in await pool.fetch("SELECT id, enabled FROM services")}
    assert rows == {"utp": True, "up": False}  # se desactiva, no se borra (conserva historial)


async def test_solo_un_incidente_abierto_por_servicio(pool):
    await db.sync_services(pool, [UTP])
    now = datetime.now(UTC)
    async with pool.acquire() as conn:
        first = await db.open_incident(conn, "utp", now, "HTTP 503")
        second = await db.open_incident(conn, "utp", now, "HTTP 503")
        assert first is not None
        assert second is None  # el índice único parcial lo impide, incluso con carreras
        closed = await db.resolve_incident(conn, "utp", now + timedelta(minutes=20))
    assert closed["duration"] == timedelta(minutes=20)  # columna calculada por la DB


async def test_pausar_un_servicio_cierra_su_incidente(pool):
    await db.sync_services(pool, [UTP])
    async with pool.acquire() as conn:
        await db.open_incident(conn, "utp", datetime.now(UTC), "HTTP 503")
    await pool.execute("UPDATE services SET status = 'down' WHERE id = 'utp'")

    await db.sync_services(pool, [UTP.model_copy(update={"enabled": False})])

    inc = await pool.fetchrow("SELECT resolved_at, cause FROM incidents WHERE service_id = 'utp'")
    assert inc["resolved_at"] is not None
    assert inc["cause"] == "HTTP 503 · cerrado al pausar el monitoreo"
    assert await pool.fetchval("SELECT status FROM services WHERE id = 'utp'") == "unknown"


async def test_resumen_calcula_disponibilidad_24h_y_ultimo_error(pool):
    await db.sync_services(pool, [UTP])
    now = datetime.now(UTC)
    async with pool.acquire() as conn:
        for minutes_ago, ok in [(30, True), (20, True), (10, True), (1, False)]:
            await db.insert_check(
                conn,
                CheckResult(
                    "utp",
                    now - timedelta(minutes=minutes_ago),
                    ok,
                    200 if ok else 503,
                    150 if ok else None,
                    None if ok else "HTTP 503",
                    60 if ok else None,
                ),
            )
    s = await db.get_service(pool, "utp")
    assert s["uptime_24h"] == pytest.approx(0.75)
    assert s["last_error"] == "HTTP 503"
    assert s["ssl_days_left"] == 60  # la revisión fallida no trae SSL: se usa el último conocido


async def test_suscripcion_se_alterna_de_forma_atomica(pool):
    await db.sync_services(pool, [UTP])
    assert await db.toggle_subscription(pool, 42, "utp") is True
    assert await db.subscribers_for(pool, "utp") == [42]
    assert await db.toggle_subscription(pool, 42, "utp") is False
    assert await db.subscribers_for(pool, "utp") == []


async def test_rol_de_power_bi_no_ve_datos_personales(pool):
    """powerbi_reader solo puede leer el esquema reporting (privacidad del bot)."""
    can_read = await pool.fetchval(
        "SELECT has_table_privilege('powerbi_reader', 'public.subscribers', 'SELECT')"
    )
    can_report = await pool.fetchval(
        "SELECT has_table_privilege('powerbi_reader', 'reporting.fact_incidents', 'SELECT')"
    )
    assert can_read is False
    assert can_report is True
