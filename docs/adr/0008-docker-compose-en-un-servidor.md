# ADR-0008: Docker Compose en un servidor, no Kubernetes

- **Estado:** Aceptado
- **Fecha:** 2026-11

## Contexto

El sistema completo usa unos 3–4 GB de RAM y no necesita escalar horizontalmente: un
worker asíncrono revisa cientos de sitios. El objetivo es un costo cercano a cero y una
operación simple para una sola persona.

## Decisión

- **Docker Compose** define todo el sistema (`docker-compose.yml`) y un archivo de
  producción lo ajusta (`deploy/compose.prod.yml`: imágenes de GHCR, puertos 80/443,
  límites de memoria, respaldo diario).
- El mismo comando levanta todo en local y en el servidor.
- La infraestructura del servidor se describe con **OpenTofu** (`infra/oracle/`) y se
  despliega con **GitHub Actions** por SSH, con verificación de salud y **rollback
  automático** a las imágenes anteriores.

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| Kubernetes (k3s, EKS, GKE) | Complejidad y costo injustificados para un solo nodo; más superficie que operar y asegurar. |
| PaaS (Render, Railway, Fly.io) | Costo mensual por servicio; TimescaleDB y el stack de observabilidad no encajan bien. |
| Servicios sueltos sin contenedores | Entornos distintos entre local y producción. |

## Consecuencias

- Un solo servidor es un punto único de falla: aceptable para este proyecto y mitigado
  con respaldos diarios y un despliegue reproducible desde cero.
- Si algún día hiciera falta alta disponibilidad, las imágenes ya son multi-arquitectura
  y la configuración es declarativa: migrar a Kubernetes sería directo.
