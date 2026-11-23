# PanaStatus

Monitor público de disponibilidad de servicios web de Panamá (bancos, gobierno, UTP, servicios globales).
Proyecto de portafolio para un puesto de Analista de Soluciones (Soporte de Aplicaciones, Observabilidad y Confiabilidad).
Yo (Ahmed) debo entender cada pieza: explica las decisiones importantes y deja el código claro y comentado.

## Qué hace
- Checker: revisa cada servicio cada 1–5 min (HTTP, latencia, vigencia SSL). Caída confirmada = 2 fallas seguidas.
- Incidentes: se abren al confirmar caída, se cierran al recuperarse, con duración.
- Bot de Telegram público: /start, /servicios (suscribirse con botones), /estado [servicio], /missuscripciones, /silencio, /stop. Avisos de caída, recuperación y lentitud. Funciona en grupos.
- Página pública de estado: banner general, servicios por categoría, barra de 90 días, latencia 24 h, incidentes.
- API FastAPI solo lectura + /health, con límite de peticiones.
- Post-mortems: borrador con IA para incidentes > 15 min, revisado por el admin.

## Stack
Python 3.12 + uv, asyncio, httpx, Pydantic · FastAPI · python-telegram-bot · PostgreSQL + TimescaleDB ·
Front: Astro o Next.js + Tailwind · OpenTelemetry → Grafana Alloy → Prometheus + Loki → Grafana ·
Docker Compose + Caddy (HTTPS) · GitHub Actions + GHCR + Ruff + pytest · OpenTofu · Oracle Cloud o Azure · Power BI para reportes.

## Tablas
services, checks (hypertable), incidents, postmortems, subscribers (solo chat_id y suscripciones).

## Reglas
- Monitoreo responsable: solo páginas públicas, sin login, 1 petición cada 1–5 min, User-Agent identificable con contacto.
- Secretos solo en .env (nunca en git) y GitHub Secrets.
- Servicios definidos en config/services.yaml.

## Plan
Fase 1 Base: checker + PostgreSQL/TimescaleDB + Docker Compose + alertas al admin.
Fase 2 Producto: bot con suscripciones, API, página pública.
Fase 3 Producción: nube con OpenTofu, CI/CD, HTTPS, observabilidad interna. → Lanzamiento público.
Fase 4 Análisis: post-mortems con IA, Power BI, README.