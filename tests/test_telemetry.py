"""Las métricas que registra el worker por cada revisión."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from panastatus import telemetry, worker
from panastatus.checker import CheckResult
from panastatus.config import ServiceConfig


class FakeInstrument:
    """Reemplaza un contador/histograma/gauge y guarda cada llamada."""

    def __init__(self) -> None:
        self.calls: list[tuple[float, dict]] = []

    def add(self, value, attributes=None):
        self.calls.append((value, dict(attributes or {})))

    record = add
    set = add


@pytest.fixture
def fakes(monkeypatch):
    names = ["checks", "check_latency", "service_up", "ssl_days_left", "events"]
    created = {n: FakeInstrument() for n in names}
    for name, fake in created.items():
        monkeypatch.setattr(telemetry, name, fake)
    return created


SERVICE = ServiceConfig(id="utp", name="UTP", category="educacion", url="https://utp.ac.pa")


def result(ok: bool, latency: int | None = 300) -> CheckResult:
    return CheckResult(
        service_id="utp",
        time=datetime.now(UTC),
        ok=ok,
        status_code=200 if ok else None,
        latency_ms=latency if ok else None,
        error=None if ok else "timeout",
        ssl_days_left=90 if ok else None,
    )


def test_revision_exitosa(fakes):
    worker._record_metrics(SERVICE, result(True), "up", None)
    attrs = {"service_id": "utp", "category": "educacion"}
    assert fakes["checks"].calls == [(1, {**attrs, "result": "ok"})]
    assert fakes["check_latency"].calls == [(300, attrs)]
    assert fakes["service_up"].calls == [(1.0, attrs)]
    assert fakes["ssl_days_left"].calls == [(90, attrs)]
    assert fakes["events"].calls == []


def test_caida_registra_evento_y_no_latencia(fakes):
    worker._record_metrics(SERVICE, result(False), "down", "down")
    assert fakes["checks"].calls[0][1]["result"] == "fail"
    assert fakes["check_latency"].calls == []  # la latencia de un fallo no es representativa
    assert fakes["service_up"].calls[0][0] == 0.0
    assert fakes["events"].calls[0][1]["event"] == "down"


def test_setup_sin_endpoint_no_falla(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.setattr(telemetry, "_configured", False)
    telemetry.setup("test")  # no debe lanzar ni intentar conectarse
