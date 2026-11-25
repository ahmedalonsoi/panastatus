"""Pruebas de la API pública sin base de datos real.

Se reemplazan las funciones de ``panastatus.db`` por versiones falsas (monkeypatch) y se
inyecta un pool falso en ``app.state``. Así se prueba el contrato HTTP (códigos, forma del
JSON, orden, reglas del banner) en milisegundos y sin Docker.

``TestClient(app)`` sin ``with`` NO ejecuta el ``lifespan``: no intenta conectarse a la DB.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from panastatus import api, db

CATEGORIES = {"bancos": "🏦 Bancos", "gobierno": "🏛️ Gobierno", "educacion": "🎓 Educación"}
NOW = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)


def _row(id_: str, name: str, category: str, status: str = "up", **extra) -> dict:
    return {
        "id": id_,
        "name": name,
        "category": category,
        "url": f"https://{id_}.example",
        "status": status,
        "last_checked_at": NOW,
        "last_latency_ms": 120,
        "last_error": None,
        "ssl_days_left": 60,
        "uptime_24h": 1.0,
        "down_since": None,
        **extra,
    }


class FakePool:
    """Lo mínimo que usa /health."""

    def __init__(self, healthy: bool = True):
        self.healthy = healthy

    async def fetchval(self, _sql: str):
        if not self.healthy:
            raise ConnectionError("db caída")
        return 1


@pytest.fixture
def client(monkeypatch):
    rows = [
        _row("utp", "UTP", "educacion"),
        _row("dgi", "DGI", "gobierno"),
        _row("bac", "BAC", "bancos"),
        _row("banistmo", "Banistmo", "bancos"),
    ]

    async def list_services(_pool):
        return rows

    monkeypatch.setattr(db, "list_services", list_services)
    api.app.state.pool = FakePool()
    api.app.state.categories = CATEGORIES
    api.limiter.enabled = False  # el límite de peticiones se prueba aparte, no aquí
    yield TestClient(api.app), rows
    api.limiter.enabled = True


def test_servicios_en_orden_de_categorias_del_yaml(client):
    http, _ = client
    body = http.get("/api/services").json()
    # Orden del YAML (bancos, gobierno, educación) y, dentro, alfabético.
    assert [s["id"] for s in body] == ["bac", "banistmo", "dgi", "utp"]
    assert body[3]["category_label"] == "🎓 Educación"


def test_categoria_desconocida_va_al_final():
    rows = [_row("x", "X", "otra"), _row("a", "A", "bancos")]
    assert [r["id"] for r in api.sort_by_category(rows, CATEGORIES)] == ["a", "x"]


@pytest.mark.parametrize(
    ("statuses", "overall"),
    [
        (["up", "up"], "operational"),
        (["up", "degraded"], "degraded"),
        (["degraded", "down"], "outage"),  # una caída manda sobre la lentitud
        (["unknown", "up"], "operational"),  # "sin datos" no alarma al público
    ],
)
def test_banner_general(client, statuses, overall):
    http, rows = client
    for row, status in zip(rows, statuses, strict=False):
        row["status"] = status
    for row in rows[len(statuses) :]:
        row["status"] = "up"
    body = http.get("/api/summary").json()
    assert body["overall"] == overall
    assert sum(body["counts"].values()) == len(rows)


def test_health_ok_y_db_caida(client):
    http, _ = client
    assert http.get("/health").json()["status"] == "ok"
    api.app.state.pool = FakePool(healthy=False)
    r = http.get("/health")
    assert r.status_code == 503
    assert r.json() == {"status": "error", "db": "down"}


def test_servicio_inexistente_da_404(client, monkeypatch):
    async def get_service(_pool, _id):
        return None

    monkeypatch.setattr(db, "get_service", get_service)
    http, _ = client
    assert http.get("/api/services/no-existe").status_code == 404


def test_parametros_fuera_de_rango_se_rechazan(client):
    http, _ = client
    # hours admite 1..168 (una semana): evita consultas enormes contra la DB.
    assert http.get("/api/services/utp/latency?hours=999").status_code == 422
