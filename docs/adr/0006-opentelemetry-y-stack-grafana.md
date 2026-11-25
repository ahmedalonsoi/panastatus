# ADR-0006: OpenTelemetry + Alloy + Prometheus + Loki + Grafana

- **Estado:** Aceptado
- **Fecha:** 2026-11

## Contexto

Un monitor que falla en silencio es peor que no tener monitor: la página diría "todo
operativo" con datos viejos. Necesitamos **observar al propio PanaStatus**: ¿el worker
sigue revisando?, ¿cuántas revisiones fallan?, ¿Telegram acepta los mensajes?

## Decisión

- La aplicación se instrumenta con **OpenTelemetry** (estándar abierto, independiente
  del proveedor). Métricas propias (nombre en Prometheus): `panastatus_checks_total`,
  `panastatus_check_latency_milliseconds`, `panastatus_service_up`,
  `panastatus_ssl_days_left`, `panastatus_events_total`, `panastatus_notifications_total`
  y `panastatus_bot_commands_total`, más las métricas HTTP estándar de FastAPI.
- **Grafana Alloy** recibe OTLP y lo envía a **Prometheus** (receptor OTLP nativo).
  También lee los logs JSON de los contenedores y los envía a **Loki**.
- **Grafana** se configura como código (*provisioning*): fuentes de datos, dashboard y
  alertas versionados en `observability/`.
- Alertas internas a Telegram: *Checker sin revisiones*, *Fallas masivas* (> 50 %, casi
  siempre es nuestra red) y *Envíos a Telegram fallando*.
- Sin `OTEL_EXPORTER_OTLP_ENDPOINT`, la telemetría se desactiva (pruebas y desarrollo).

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| Cliente de Prometheus directo | Ata el código a un backend; OTel permite cambiar a Datadog, Grafana Cloud, etc. sin tocarlo. |
| Servicio SaaS (Datadog, New Relic) | Costo mensual; para un portafolio interesa mostrar el stack abierto. |
| Solo logs | No permite alertas por tasa ni dashboards de tendencia. |

## Consecuencias

- Cinco contenedores más (memoria acotada con límites en producción).
- Grafana, Prometheus y Loki **no se exponen a internet**: se accede por túnel SSH.
- Las mismas prácticas que un equipo de SRE usaría en producción real.
