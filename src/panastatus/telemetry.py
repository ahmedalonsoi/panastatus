"""Métricas con OpenTelemetry (observabilidad INTERNA: ¿PanaStatus mismo está sano?).

Flujo:
    worker / api / bot  --OTLP-->  Grafana Alloy  --OTLP-->  Prometheus  -->  Grafana

¿Por qué OpenTelemetry y no la librería de Prometheus directa? OpenTelemetry es el
estándar abierto: el código no sabe a qué backend van las métricas. Mañana se cambia
Prometheus por Datadog, Azure Monitor o Grafana Cloud tocando solo la config de Alloy.

Se activa con la variable estándar OTEL_EXPORTER_OTLP_ENDPOINT (p. ej. http://alloy:4318).
Sin ella, las métricas no van a ningún lado y no cuestan nada (proveedor "no-op"): los
tests y el modo --once funcionan sin Alloy.

Nombres: OpenTelemetry usa puntos (panastatus.checks); Prometheus los traduce a
guiones bajos y agrega la unidad y el sufijo: panastatus_checks_total,
panastatus_check_latency_milliseconds_bucket, etc.
"""

from __future__ import annotations

import logging
import os

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.view import ExplicitBucketHistogramAggregation, View
from opentelemetry.sdk.resources import Resource

from panastatus import __version__

log = logging.getLogger(__name__)

# Cubetas del histograma de latencia (ms). Pensadas para páginas web: la mayoría
# responde entre 100 ms y 3 s; el timeout es 15 s.
LATENCY_BUCKETS_MS = (50, 100, 250, 500, 750, 1000, 1500, 2000, 3000, 5000, 8000, 15000)

_configured = False


def setup(service_name: str) -> None:
    """Configura el proveedor de métricas del proceso. Llamar UNA vez al arrancar."""
    global _configured
    if _configured:
        return
    _configured = True

    if not os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
        log.info("telemetría desactivada (falta OTEL_EXPORTER_OTLP_ENDPOINT)")
        return

    # Import diferido: el exportador solo se carga si de verdad se usa.
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

    # service.name termina como la etiqueta job="panastatus/worker" en Prometheus.
    resource = Resource.create(
        {
            "service.namespace": "panastatus",
            "service.name": service_name,
            "service.version": __version__,
        }
    )
    reader = PeriodicExportingMetricReader(OTLPMetricExporter(), export_interval_millis=15_000)
    views = [
        View(
            instrument_name="panastatus.check.latency",
            aggregation=ExplicitBucketHistogramAggregation(LATENCY_BUCKETS_MS),
        )
    ]
    provider = MeterProvider(resource=resource, metric_readers=[reader], views=views)
    metrics.set_meter_provider(provider)
    log.info("telemetría activada", extra={"service": service_name})


# ---------------------------------------------------------------------------
# Instrumentos. Se crean desde el "meter" global; si setup() no configuró un
# proveedor real, son no-op (no hacen nada) y es seguro llamarlos siempre.
# ---------------------------------------------------------------------------
_meter = metrics.get_meter("panastatus", __version__)

checks = _meter.create_counter(
    "panastatus.checks",
    unit="1",
    description="Revisiones realizadas, por servicio y resultado (ok/fail)",
)
check_latency = _meter.create_histogram(
    "panastatus.check.latency",
    unit="ms",
    description="Latencia de las revisiones exitosas",
)
service_up = _meter.create_gauge(
    "panastatus.service.up",
    unit="",
    description="Estado actual: 1 operativo, 0.5 lento, 0 caído",
)
ssl_days_left = _meter.create_gauge(
    "panastatus.ssl.days_left",
    unit="d",
    description="Días que le quedan al certificado TLS del servicio",
)
events = _meter.create_counter(
    "panastatus.events",
    unit="1",
    description="Eventos de estado: down, recovered, slow",
)
notifications = _meter.create_counter(
    "panastatus.notifications",
    unit="1",
    description="Mensajes de Telegram por resultado (sent, failed, rate_limited, blocked)",
)
bot_commands = _meter.create_counter(
    "panastatus.bot.commands",
    unit="1",
    description="Comandos recibidos por el bot",
)

STATUS_VALUE = {"up": 1.0, "degraded": 0.5, "down": 0.0}
