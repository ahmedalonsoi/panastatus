# Changelog

Todos los cambios relevantes de este proyecto. Formato basado en
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/); versiones con
[SemVer](https://semver.org/lang/es/).

## [Sin publicar]

### Agregado
- **Educación**: portales de la UTP (eCampus, Virtual, Matrícula), Secretaría Virtual
  de la UP y universidades UNACHI, UDELAS, UMIP, USMA, UIP y Universidad del Istmo.
- Rediseño de la página: tarjeta de estado general, indicadores clave, atajos por
  categoría, insignias de estado, disponibilidad de 90 días ponderada, esqueletos de
  carga, navegación accesible y modo oscuro revisado.
- Historial de incidentes con totales y tiempo medio de recuperación (MTTR).
- Pruebas de la API, del notificador y de integración contra TimescaleDB real.
- Pruebas del frontend con Vitest.
- Verificación de tipos con mypy, cobertura mínima en CI y hooks de pre-commit.
- Documentación: arquitectura, ADR, SLO, seguridad, guía de contribución.

### Cambiado
- La API ordena los servicios según `config/services.yaml`.
- Frontend en Node 24 LTS.
- Trivy escanea solo vulnerabilidades en las imágenes (los secretos los cubre gitleaks).
- Imagen de la aplicación sin caché de uv (505 MB → 396 MB).

### Corregido
- Al pausar un servicio, su incidente abierto se cierra en vez de quedar "En curso"
  para siempre.
- Límites de Oracle Always Free actualizados a 2 OCPU / 12 GB.

## [0.1.0] - 2026-11-23

### Agregado
- Checker asíncrono con confirmación de caídas (2 fallas), incidentes y lentitud.
- PostgreSQL + TimescaleDB (hypertable, agregado continuo, retención).
- Bot de Telegram con suscripciones, `/estado`, `/silencio` y `/stop`.
- API REST de solo lectura con límite de peticiones.
- Página de estado en Next.js servida por Caddy con HTTPS.
- Observabilidad con OpenTelemetry, Alloy, Prometheus, Loki y Grafana.
- Infraestructura como código (OpenTofu, Oracle Cloud) y CI/CD con rollback.
- Post-mortems con IA y aprobación humana; capa de reportes para Power BI.
