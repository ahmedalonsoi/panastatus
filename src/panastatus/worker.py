"""Worker: el proceso que revisa los servicios en bucle.

Diseño: una tarea asyncio por servicio, cada una con su propio intervalo. asyncio
permite tener las ~20 tareas "esperando a la red" a la vez en un solo hilo, sin threads.

Flujo de cada revisión:
    checker.check_service()  ->  CheckResult
    en UNA transacción:
        guardar el check
        leer estado (bloqueando la fila) -> state.evaluate() -> guardar estado
        abrir / cerrar incidente si corresponde
    fuera de la transacción: notificar (la red de Telegram no debe retener la DB)

Uso:
    python -m panastatus.worker          # bucle infinito (producción)
    python -m panastatus.worker --once   # revisa todo una vez e imprime; no toca la DB
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import random
import time

import asyncpg
import httpx

from panastatus import db
from panastatus.checker import CheckResult, build_client, check_service
from panastatus.config import ServiceConfig, Settings, get_settings, load_monitor_config
from panastatus.logging_setup import configure_logging
from panastatus.notifier import Notifier
from panastatus.state import evaluate

log = logging.getLogger("panastatus.worker")


async def process_result(
    pool: asyncpg.Pool,
    notifier: Notifier,
    service: ServiceConfig,
    result: CheckResult,
    settings: Settings,
) -> None:
    incident = None
    async with pool.acquire() as conn, conn.transaction():
        await db.insert_check(conn, result)
        state = await db.lock_state(conn, service.id)
        new_state, event = evaluate(
            state,
            result,
            failure_threshold=settings.failure_threshold,
            slow_threshold_ms=service.slow_threshold_ms,
            slow_consecutive=settings.slow_consecutive,
        )
        await db.save_state(conn, service.id, new_state, result.time)
        if event == "down":
            incident = await db.open_incident(
                conn, service.id, new_state.failing_since or result.time, result.error
            )
        elif event == "recovered":
            incident = await db.resolve_incident(conn, service.id, result.time)

    log.info(
        "revisión",
        extra={
            "service_id": service.id,
            "ok": result.ok,
            "status_code": result.status_code,
            "latency_ms": result.latency_ms,
            "error": result.error,
            "status": new_state.status,
        },
    )
    if event:
        await notifier.notify(event, service, result, incident)


async def service_loop(
    service: ServiceConfig,
    client: httpx.AsyncClient,
    pool: asyncpg.Pool,
    notifier: Notifier,
    settings: Settings,
) -> None:
    # Arranque escalonado: si todos los servicios se revisaran en el mismo segundo,
    # tendríamos picos de tráfico (y latencias infladas por competir entre sí).
    await asyncio.sleep(random.uniform(0, min(30, service.interval_seconds)))
    while True:
        started = time.monotonic()
        try:
            result = await check_service(client, service)
            await process_result(pool, notifier, service, result, settings)
        except Exception:
            # Un error inesperado (p. ej. la DB reiniciándose) no debe matar el bucle.
            log.exception("error procesando revisión", extra={"service_id": service.id})
        elapsed = time.monotonic() - started
        await asyncio.sleep(max(1.0, service.interval_seconds - elapsed))


async def run_forever(settings: Settings) -> None:
    if not settings.monitor_contact:
        raise SystemExit(
            "Falta MONITOR_CONTACT en .env: el User-Agent debe incluir un contacto "
            "(regla de monitoreo responsable)."
        )
    monitor = load_monitor_config(settings.services_file)
    services = monitor.enabled_services
    pool = await db.create_pool(settings.database_url)
    try:
        await db.sync_services(pool, monitor.services)
        log.info("worker iniciado", extra={"services": len(services)})
        async with (
            build_client(settings) as client,
            httpx.AsyncClient(timeout=15) as telegram_client,
        ):
            notifier = Notifier(settings, pool, telegram_client)
            async with asyncio.TaskGroup() as tg:
                for service in services:
                    tg.create_task(service_loop(service, client, pool, notifier, settings))
    finally:
        await pool.close()


async def run_once(settings: Settings) -> None:
    """Revisa cada servicio UNA vez y muestra una tabla. Útil para validar URLs nuevas."""
    monitor = load_monitor_config(settings.services_file)
    async with build_client(settings) as client:
        results = await asyncio.gather(
            *(check_service(client, s) for s in monitor.enabled_services)
        )
    print(f"{'servicio':<22}{'ok':<5}{'http':<6}{'ms':>7}{'ssl días':>10}  error")
    for r in results:
        ssl_days = "-" if r.ssl_days_left is None else r.ssl_days_left
        print(
            f"{r.service_id:<22}{'sí' if r.ok else 'NO':<5}{r.status_code or '-'!s:<6}"
            f"{r.latency_ms or '-'!s:>7}{ssl_days!s:>10}  {r.error or ''}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Checker de PanaStatus")
    parser.add_argument("--once", action="store_true", help="revisar una vez y salir")
    args = parser.parse_args()

    configure_logging()
    settings = get_settings()
    try:
        asyncio.run(run_once(settings) if args.once else run_forever(settings))
    except KeyboardInterrupt:
        # Docker Compose envía SIGINT al detener (stop_signal), que Python convierte en
        # KeyboardInterrupt: así cerramos limpio en vez de morir a la fuerza.
        log.info("worker detenido")


if __name__ == "__main__":
    main()
