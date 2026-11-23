"""Acceso a PostgreSQL/TimescaleDB con asyncpg.

Usamos SQL escrito a mano (sin ORM) a propósito: cada consulta es visible y se puede
copiar tal cual a psql para depurarla. Todas usan parámetros ($1, $2...) — nunca
concatenamos texto en el SQL, así no hay inyección SQL.

Las funciones reciben un ``pool`` (conjunto de conexiones reutilizables) o una
``conn`` cuando deben correr dentro de una transacción que controla quien llama.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

import asyncpg

from panastatus.checker import CheckResult
from panastatus.config import ServiceConfig
from panastatus.state import ServiceState


async def create_pool(dsn: str) -> asyncpg.Pool:
    return await asyncpg.create_pool(dsn, min_size=1, max_size=10)


# ---------------------------------------------------------------------------
# Worker (checker)
# ---------------------------------------------------------------------------


async def sync_services(pool: asyncpg.Pool, services: Sequence[ServiceConfig]) -> None:
    """Copia services.yaml a la tabla services. Los que ya no están en el YAML se
    desactivan (no se borran, para no perder su historial)."""
    async with pool.acquire() as conn, conn.transaction():
        for s in services:
            await conn.execute(
                """
                INSERT INTO services (id, name, category, url, interval_seconds,
                                      slow_threshold_ms, enabled)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    category = EXCLUDED.category,
                    url = EXCLUDED.url,
                    interval_seconds = EXCLUDED.interval_seconds,
                    slow_threshold_ms = EXCLUDED.slow_threshold_ms,
                    enabled = EXCLUDED.enabled,
                    updated_at = now()
                """,
                s.id,
                s.name,
                s.category,
                str(s.url),
                s.interval_seconds,
                s.slow_threshold_ms,
                s.enabled,
            )
        await conn.execute(
            "UPDATE services SET enabled = false WHERE NOT (id = ANY($1::text[]))",
            [s.id for s in services],
        )


async def insert_check(conn: asyncpg.Connection, r: CheckResult) -> None:
    await conn.execute(
        """
        INSERT INTO checks (time, service_id, ok, status_code, latency_ms, error, ssl_days_left)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
        r.time,
        r.service_id,
        r.ok,
        r.status_code,
        r.latency_ms,
        r.error,
        r.ssl_days_left,
    )


async def lock_state(conn: asyncpg.Connection, service_id: str) -> ServiceState:
    """Lee el estado del servicio bloqueando la fila (FOR UPDATE) hasta el fin de la
    transacción, para que dos procesos nunca lo actualicen a la vez."""
    row = await conn.fetchrow(
        """
        SELECT status, consecutive_failures, consecutive_slow, failing_since
        FROM services WHERE id = $1 FOR UPDATE
        """,
        service_id,
    )
    return ServiceState(**dict(row)) if row else ServiceState()


async def save_state(
    conn: asyncpg.Connection, service_id: str, s: ServiceState, checked_at: datetime
) -> None:
    await conn.execute(
        """
        UPDATE services SET status = $2, consecutive_failures = $3, consecutive_slow = $4,
               failing_since = $5, last_checked_at = $6
        WHERE id = $1
        """,
        service_id,
        s.status,
        s.consecutive_failures,
        s.consecutive_slow,
        s.failing_since,
        checked_at,
    )


async def open_incident(
    conn: asyncpg.Connection, service_id: str, started_at: datetime, cause: str | None
) -> asyncpg.Record | None:
    # ON CONFLICT ... DO NOTHING: si ya había un incidente abierto (índice único parcial),
    # no se duplica.
    return await conn.fetchrow(
        """
        INSERT INTO incidents (service_id, started_at, cause) VALUES ($1, $2, $3)
        ON CONFLICT (service_id) WHERE resolved_at IS NULL DO NOTHING
        RETURNING id, started_at, resolved_at, duration, cause
        """,
        service_id,
        started_at,
        cause,
    )


async def resolve_incident(
    conn: asyncpg.Connection, service_id: str, resolved_at: datetime
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        UPDATE incidents SET resolved_at = $2
        WHERE service_id = $1 AND resolved_at IS NULL
        RETURNING id, started_at, resolved_at, duration, cause
        """,
        service_id,
        resolved_at,
    )


async def subscribers_for(pool: asyncpg.Pool, service_id: str) -> list[int]:
    """chat_ids suscritos al servicio y que no están en /silencio."""
    rows = await pool.fetch(
        """
        SELECT chat_id FROM subscribers
        WHERE services @> ARRAY[$1::text]
          AND (muted_until IS NULL OR muted_until < now())
        """,
        service_id,
    )
    return [r["chat_id"] for r in rows]


async def delete_subscriber(pool: asyncpg.Pool, chat_id: int) -> None:
    await pool.execute("DELETE FROM subscribers WHERE chat_id = $1", chat_id)


# ---------------------------------------------------------------------------
# Lecturas para la API y el bot
# ---------------------------------------------------------------------------

_SERVICE_SUMMARY_SQL = """
SELECT s.id, s.name, s.category, s.url, s.status, s.last_checked_at,
       last.latency_ms   AS last_latency_ms,
       last.error        AS last_error,
       cert.ssl_days_left,
       u.uptime_24h,
       inc.started_at    AS down_since
FROM services s
-- Última revisión
LEFT JOIN LATERAL (
    SELECT latency_ms, error FROM checks
    WHERE service_id = s.id ORDER BY time DESC LIMIT 1
) last ON true
-- Último dato de certificado conocido (una revisión fallida no trae SSL)
LEFT JOIN LATERAL (
    SELECT ssl_days_left FROM checks
    WHERE service_id = s.id AND ssl_days_left IS NOT NULL
      AND time > now() - INTERVAL '2 days'
    ORDER BY time DESC LIMIT 1
) cert ON true
-- % de revisiones OK en las últimas 24 h
LEFT JOIN LATERAL (
    SELECT avg(ok::int)::float AS uptime_24h FROM checks
    WHERE service_id = s.id AND time > now() - INTERVAL '24 hours'
) u ON true
-- Incidente abierto (si está caído)
LEFT JOIN incidents inc ON inc.service_id = s.id AND inc.resolved_at IS NULL
WHERE s.enabled
"""


async def list_services(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    return await pool.fetch(_SERVICE_SUMMARY_SQL + " ORDER BY s.category, s.name")


async def get_service(pool: asyncpg.Pool, service_id: str) -> asyncpg.Record | None:
    return await pool.fetchrow(_SERVICE_SUMMARY_SQL + " AND s.id = $1", service_id)


async def uptime_windows(pool: asyncpg.Pool, service_id: str) -> dict[str, float | None]:
    """% de disponibilidad en 7, 30 y 90 días, desde el resumen diario."""
    row = await pool.fetchrow(
        """
        SELECT
          sum(ok_count) FILTER (WHERE day > now() - INTERVAL '7 days')::float
            / NULLIF(sum(total) FILTER (WHERE day > now() - INTERVAL '7 days'), 0)  AS d7,
          sum(ok_count) FILTER (WHERE day > now() - INTERVAL '30 days')::float
            / NULLIF(sum(total) FILTER (WHERE day > now() - INTERVAL '30 days'), 0) AS d30,
          sum(ok_count)::float / NULLIF(sum(total), 0)                              AS d90
        FROM checks_daily
        WHERE service_id = $1 AND day > now() - INTERVAL '90 days'
        """,
        service_id,
    )
    return {"7d": row["d7"], "30d": row["d30"], "90d": row["d90"]}


async def daily_uptime(pool: asyncpg.Pool, days: int) -> list[asyncpg.Record]:
    """Una fila por servicio y día (para la barra de 90 días)."""
    return await pool.fetch(
        """
        SELECT service_id,
               (day AT TIME ZONE 'America/Panama')::date AS day,
               total, ok_count, avg_latency_ms
        FROM checks_daily
        WHERE day > now() - make_interval(days => $1)
        ORDER BY service_id, day
        """,
        days,
    )


async def latency_series(pool: asyncpg.Pool, service_id: str, hours: int) -> list[asyncpg.Record]:
    """Latencia promedio y máxima en tramos de 15 minutos."""
    return await pool.fetch(
        """
        SELECT time_bucket(INTERVAL '15 minutes', time) AS bucket,
               avg(latency_ms)::int AS avg_ms,
               max(latency_ms)      AS max_ms,
               count(*) FILTER (WHERE NOT ok) AS failures
        FROM checks
        WHERE service_id = $1 AND time > now() - make_interval(hours => $2)
        GROUP BY bucket ORDER BY bucket
        """,
        service_id,
        hours,
    )


async def list_incidents(
    pool: asyncpg.Pool, limit: int, service_id: str | None = None
) -> list[asyncpg.Record]:
    return await pool.fetch(
        """
        SELECT i.id, i.service_id, s.name AS service_name, i.started_at, i.resolved_at,
               EXTRACT(EPOCH FROM coalesce(i.duration, now() - i.started_at))::int
                   AS duration_seconds,
               i.cause
        FROM incidents i JOIN services s ON s.id = i.service_id
        WHERE ($2::text IS NULL OR i.service_id = $2)
        ORDER BY i.started_at DESC
        LIMIT $1
        """,
        limit,
        service_id,
    )


# ---------------------------------------------------------------------------
# Suscripciones (bot)
# ---------------------------------------------------------------------------


async def toggle_subscription(pool: asyncpg.Pool, chat_id: int, service_id: str) -> bool:
    """Suscribe si no estaba, desuscribe si estaba. Devuelve True si quedó suscrito.
    Todo en una sola sentencia SQL atómica (sin leer-y-luego-escribir)."""
    return await pool.fetchval(
        """
        INSERT INTO subscribers (chat_id, services) VALUES ($1, ARRAY[$2::text])
        ON CONFLICT (chat_id) DO UPDATE SET services =
            CASE WHEN $2::text = ANY(subscribers.services)
                 THEN array_remove(subscribers.services, $2::text)
                 ELSE array_append(subscribers.services, $2::text)
            END
        RETURNING $2::text = ANY(services)
        """,
        chat_id,
        service_id,
    )


async def get_subscriber(pool: asyncpg.Pool, chat_id: int) -> asyncpg.Record | None:
    return await pool.fetchrow(
        "SELECT chat_id, services, muted_until FROM subscribers WHERE chat_id = $1", chat_id
    )


async def set_muted_until(pool: asyncpg.Pool, chat_id: int, until: datetime | None) -> bool:
    """Devuelve False si el chat no tiene suscripciones (no hay nada que silenciar)."""
    status = await pool.execute(
        "UPDATE subscribers SET muted_until = $2 WHERE chat_id = $1", chat_id, until
    )
    return status != "UPDATE 0"
