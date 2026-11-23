-- Capa de reportes para Power BI (y cualquier herramienta de BI).
--
-- ¿Por qué vistas en un esquema aparte y no conectar Power BI a las tablas?
-- - Contrato estable: si cambian las tablas internas, se ajusta la vista y los reportes
--   siguen funcionando.
-- - Datos ya listos para analizar: horas de Panamá, porcentajes, minutos.
-- - Seguridad: el rol powerbi_reader SOLO puede leer este esquema (nada de suscriptores
--   ni chat_id de Telegram).
--
-- Modelo estrella para Power BI:
--   dim_service ──┬── fact_service_daily   (1 fila por servicio y día)
--                 ├── fact_incidents       (1 fila por incidente)
--                 └── fact_latency_hourly  (1 fila por servicio y hora, últimos 30 días)
--   + sla_monthly (resumen mensual precalculado)

CREATE SCHEMA IF NOT EXISTS reporting;

-- Dimensión: servicios ------------------------------------------------------
CREATE OR REPLACE VIEW reporting.dim_service AS
SELECT id AS service_id, name AS service_name, category, url, enabled,
       interval_seconds, slow_threshold_ms
FROM services;

-- Hecho: disponibilidad diaria (desde el agregado continuo, muy liviano) -----
CREATE OR REPLACE VIEW reporting.fact_service_daily AS
SELECT service_id,
       (day AT TIME ZONE 'America/Panama')::date                       AS date,
       total                                                            AS checks,
       ok_count                                                         AS ok_checks,
       total - ok_count                                                 AS failed_checks,
       round(100.0 * ok_count / NULLIF(total, 0), 3)                    AS uptime_pct,
       round(avg_latency_ms::numeric, 0)                                AS avg_latency_ms
FROM checks_daily;

-- Hecho: incidentes -----------------------------------------------------------
CREATE OR REPLACE VIEW reporting.fact_incidents AS
SELECT i.id                                                            AS incident_id,
       i.service_id,
       (i.started_at AT TIME ZONE 'America/Panama')                    AS started_at_local,
       (i.resolved_at AT TIME ZONE 'America/Panama')                   AS resolved_at_local,
       (i.started_at AT TIME ZONE 'America/Panama')::date              AS date,
       extract(hour FROM i.started_at AT TIME ZONE 'America/Panama')::int AS start_hour,
       extract(isodow FROM i.started_at AT TIME ZONE 'America/Panama')::int AS start_weekday, -- 1 = lunes
       round(extract(epoch FROM coalesce(i.duration, now() - i.started_at)) / 60.0, 1)
                                                                        AS duration_minutes,
       i.resolved_at IS NULL                                            AS is_open,
       i.cause,
       pm.status = 'approved'                                           AS has_postmortem
FROM incidents i
LEFT JOIN postmortems pm ON pm.incident_id = i.id;

-- Hecho: latencia por hora (percentiles), últimos 30 días ----------------------
CREATE OR REPLACE VIEW reporting.fact_latency_hourly AS
SELECT service_id,
       (time_bucket(INTERVAL '1 hour', time) AT TIME ZONE 'America/Panama') AS hour_local,
       count(*)                                                         AS checks,
       count(*) FILTER (WHERE NOT ok)                                   AS failed_checks,
       percentile_cont(0.50) WITHIN GROUP (ORDER BY latency_ms)
           FILTER (WHERE ok)::int                                       AS p50_ms,
       percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms)
           FILTER (WHERE ok)::int                                       AS p95_ms
FROM checks
WHERE time > now() - INTERVAL '30 days'
GROUP BY service_id, time_bucket(INTERVAL '1 hour', time);

-- Resumen mensual tipo SLA ------------------------------------------------------
-- MTTR = tiempo medio de recuperación. Tiempo caído estimado = revisiones fallidas ×
-- intervalo del servicio (aproximación honesta: solo vemos el sitio cada 1–5 min).
CREATE OR REPLACE VIEW reporting.sla_monthly AS
WITH daily AS (
    SELECT service_id, date_trunc('month', date)::date AS month,
           sum(checks) AS checks, sum(ok_checks) AS ok_checks
    FROM reporting.fact_service_daily
    GROUP BY service_id, date_trunc('month', date)
), inc AS (
    SELECT service_id, date_trunc('month', date)::date AS month,
           count(*) AS incidents, round(avg(duration_minutes), 1) AS mttr_minutes
    FROM reporting.fact_incidents
    WHERE NOT is_open
    GROUP BY service_id, date_trunc('month', date)
)
SELECT d.service_id, d.month,
       round(100.0 * d.ok_checks / NULLIF(d.checks, 0), 3)               AS uptime_pct,
       round((d.checks - d.ok_checks) * s.interval_seconds / 60.0, 0)    AS est_downtime_minutes,
       coalesce(inc.incidents, 0)                                        AS incidents,
       inc.mttr_minutes
FROM daily d
JOIN services s ON s.id = d.service_id
LEFT JOIN inc ON inc.service_id = d.service_id AND inc.month = d.month;

-- Rol de solo lectura para Power BI -------------------------------------------------
-- Se crea SIN login: la contraseña nunca va en git. Para activarlo (una vez, por psql):
--   ALTER ROLE powerbi_reader WITH LOGIN PASSWORD '<contraseña larga>';
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'powerbi_reader') THEN
        CREATE ROLE powerbi_reader NOLOGIN;
    END IF;
END
$$;

-- Las vistas se ejecutan con los permisos de su dueño, así que basta con dar acceso al
-- esquema reporting: el rol NO tiene permiso sobre las tablas de public.
GRANT USAGE ON SCHEMA reporting TO powerbi_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA reporting TO powerbi_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA reporting GRANT SELECT ON TABLES TO powerbi_reader;
-- Defensa adicional: nada en public, y consultas largas cortadas a los 60 s.
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM powerbi_reader;
ALTER ROLE powerbi_reader SET statement_timeout = '60s';
