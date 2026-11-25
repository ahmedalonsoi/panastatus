"""API pública de solo lectura (FastAPI) + página de estado.

Rutas:
    GET /health                         ¿la API y la DB responden? (para Docker/monitoreo)
    GET /api/summary                    banner general
    GET /api/services                   todos los servicios con su estado actual
    GET /api/services/{id}              detalle + disponibilidad 7/30/90 días
    GET /api/services/{id}/latency      latencia en tramos de 15 min (24 h por defecto)
    GET /api/uptime/daily               barra de 90 días de TODOS los servicios (1 petición)
    GET /api/incidents                  incidentes recientes
    GET /api/docs                       documentación interactiva (Swagger), gratis con FastAPI

La página pública (Next.js, carpeta frontend/) la sirve Caddy, no esta API.

Límite de peticiones: 60 por minuto por IP (slowapi). Protege la DB de abusos.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import Annotated

import asyncpg
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from panastatus import __version__, db, telemetry
from panastatus.config import get_settings, load_monitor_config

# --- Modelos de respuesta: documentan la API en /api/docs y filtran qué se expone ---


class ServiceOut(BaseModel):
    id: str
    name: str
    category: str
    category_label: str
    url: str
    status: str
    last_checked_at: datetime | None
    last_latency_ms: int | None
    last_error: str | None
    ssl_days_left: int | None
    uptime_24h: float | None
    down_since: datetime | None


class ServiceDetailOut(ServiceOut):
    uptime: dict[str, float | None]


class SummaryOut(BaseModel):
    overall: str  # "operational" | "degraded" | "outage"
    counts: dict[str, int]
    last_checked_at: datetime | None


class DailyPoint(BaseModel):
    day: date
    total: int
    ok_count: int
    uptime: float
    avg_latency_ms: float | None


class LatencyPoint(BaseModel):
    bucket: datetime
    avg_ms: int | None
    max_ms: int | None
    failures: int


class IncidentOut(BaseModel):
    id: int
    service_id: str
    service_name: str
    started_at: datetime
    resolved_at: datetime | None
    duration_seconds: int
    cause: str | None
    postmortem: str | None = None  # análisis aprobado por el admin (Fase 4)


# --- Aplicación ---


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Se ejecuta al arrancar y al apagar: abre y cierra el pool de conexiones."""
    settings = get_settings()
    app.state.pool = await db.create_pool(settings.database_url)
    monitor = load_monitor_config(settings.services_file)
    app.state.categories = monitor.categories
    app.state.service_order = {s.id: i for i, s in enumerate(monitor.services)}
    yield
    await app.state.pool.close()


# Métricas: se configuran ANTES de crear la app para que la instrumentación de FastAPI
# use el proveedor real (http_server_request_duration_seconds por ruta y código).
telemetry.setup("api")

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

app = FastAPI(
    title="PanaStatus API",
    version=__version__,
    description="Disponibilidad de servicios web de Panamá. Solo lectura.",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)
# /health lo consulta Docker cada pocos segundos: no lo medimos para no ensuciar las métricas.
FastAPIInstrumentor.instrument_app(app, excluded_urls="health")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS: en producción la página y la API comparten dominio y no hace falta. En desarrollo
# la página corre en localhost:3000 (npm run dev) y la API en :8000, así que el navegador
# exige permiso explícito. Solo GET: la API es de solo lectura.
_cors = get_settings().cors_origins
if _cors:
    app.add_middleware(
        CORSMiddleware, allow_origins=_cors, allow_methods=["GET"], allow_headers=["*"]
    )


def get_pool(request: Request) -> asyncpg.Pool:
    return request.app.state.pool


Pool = Annotated[asyncpg.Pool, Depends(get_pool)]


def _service_out(request: Request, row: asyncpg.Record) -> dict:
    data = dict(row)
    data["category_label"] = request.app.state.categories.get(row["category"], row["category"])
    return data


@app.get("/health", tags=["sistema"])
@limiter.exempt
async def health(pool: Pool):
    try:
        await pool.fetchval("SELECT 1")
    except Exception:
        return JSONResponse({"status": "error", "db": "down"}, status_code=503)
    return {"status": "ok", "version": __version__}


@app.get("/api/about", tags=["sistema"])
async def about():
    """Identidad del bot (la usa la página /bot/). Sale de la misma configuración que
    el checker, así la página y el User-Agent real nunca se contradicen."""
    settings = get_settings()
    return {"contact": settings.monitor_contact, "user_agent": settings.user_agent}


@app.get("/api/summary", response_model=SummaryOut, tags=["estado"])
async def summary(pool: Pool):
    rows = await db.list_services(pool)
    counts = {"up": 0, "degraded": 0, "down": 0, "unknown": 0}
    for r in rows:
        counts[r["status"]] += 1
    if counts["down"]:
        overall = "outage"
    elif counts["degraded"]:
        overall = "degraded"
    else:
        overall = "operational"
    last = max((r["last_checked_at"] for r in rows if r["last_checked_at"]), default=None)
    return {"overall": overall, "counts": counts, "last_checked_at": last}


def sort_by_category(
    rows: list, categories: dict[str, str], service_order: dict[str, int] | None = None
) -> list:
    """Ordena como en services.yaml: primero por categoría y luego por posición del servicio.

    La DB ordena alfabéticamente por la llave de la categoría; aquí se respeta el orden que
    eligió quien edita la configuración (Bancos, Gobierno, Educación...; y dentro de
    Educación, la UTP y sus portales juntos). Lo que no esté en el YAML va al final, por nombre.
    """
    cat_order = {key: i for i, key in enumerate(categories)}
    svc_order = service_order or {}
    last = len(svc_order) + len(rows)
    return sorted(
        rows,
        key=lambda r: (
            cat_order.get(r["category"], len(cat_order)),
            svc_order.get(r["id"], last),
            r["name"].lower(),
        ),
    )


@app.get("/api/services", response_model=list[ServiceOut], tags=["estado"])
async def services(request: Request, pool: Pool):
    state = request.app.state
    rows = sort_by_category(await db.list_services(pool), state.categories, state.service_order)
    return [_service_out(request, r) for r in rows]


@app.get("/api/services/{service_id}", response_model=ServiceDetailOut, tags=["estado"])
async def service_detail(service_id: str, request: Request, pool: Pool):
    row = await db.get_service(pool, service_id)
    if row is None:
        raise HTTPException(404, "Servicio no encontrado")
    return {**_service_out(request, row), "uptime": await db.uptime_windows(pool, service_id)}


@app.get("/api/services/{service_id}/latency", response_model=list[LatencyPoint], tags=["métricas"])
async def latency(service_id: str, pool: Pool, hours: int = Query(24, ge=1, le=168)):
    return [dict(r) for r in await db.latency_series(pool, service_id, hours)]


@app.get("/api/uptime/daily", response_model=dict[str, list[DailyPoint]], tags=["métricas"])
async def uptime_daily(pool: Pool, days: int = Query(90, ge=1, le=90)):
    result: dict[str, list[dict]] = {}
    for r in await db.daily_uptime(pool, days):
        result.setdefault(r["service_id"], []).append(
            {**dict(r), "uptime": r["ok_count"] / r["total"] if r["total"] else 1.0}
        )
    return result


@app.get("/api/incidents", response_model=list[IncidentOut], tags=["incidentes"])
async def incidents(
    pool: Pool,
    limit: int = Query(30, ge=1, le=200),
    service_id: str | None = None,
):
    return [dict(r) for r in await db.list_incidents(pool, limit, service_id)]
