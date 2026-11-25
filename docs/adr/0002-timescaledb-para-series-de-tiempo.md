# ADR-0002: PostgreSQL + TimescaleDB para las revisiones

- **Estado:** Aceptado
- **Fecha:** 2026-11

## Contexto

Cada revisión genera una fila. Con ~30 servicios cada 3–5 minutos son ~10 000 filas al
día y unos 2 millones en 6 meses. Las consultas típicas son por **tiempo**: "últimas
24 h", "disponibilidad diaria de 90 días", "latencia por hora". Además necesitamos datos
**relacionales** con garantías fuertes: servicios, incidentes (máximo uno abierto por
servicio), suscriptores y post-mortems.

## Decisión

PostgreSQL 17 con la extensión **TimescaleDB**:

- `checks` es una **hypertable** particionada en *chunks* de 7 días: las consultas
  recientes solo leen los chunks recientes.
- **Retención** de 180 días para los checks crudos (`add_retention_policy`): borrar es
  descartar un chunk entero, instantáneo y sin bloat.
- **Agregado continuo** `checks_daily` (días cortados a medianoche de **Panamá**), con
  `materialized_only = false` para incluir también los datos de hoy en tiempo real.
- Las reglas de negocio críticas viven en la base: índice único parcial
  `incidents_one_open_per_service` y la columna calculada `duration`.

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| PostgreSQL sin extensión | Funciona al principio, pero las consultas de 90 días recorrerían millones de filas y borrar datos viejos generaría bloat. |
| Prometheus como base principal | Excelente para métricas, pero no para incidentes, suscriptores ni consultas de negocio; ya se usa para la observabilidad **interna** (ADR-0006). |
| InfluxDB u otra base de series | Una segunda base para operar y respaldar; perderíamos SQL y las garantías relacionales. |

## Consecuencias

- Una sola base para todo, con SQL estándar y un solo respaldo (`pg_dump`).
- Las migraciones usan `psql` y no transacciones globales, porque crear un agregado
  continuo no puede ir dentro de una transacción (ver `db/migrate.sh`).
- Power BI se conecta con SQL normal a vistas del esquema `reporting`.
