-- Esquema de PanaStatus.
-- PostgreSQL ejecuta este archivo automáticamente la PRIMERA vez que arranca el contenedor
-- (todo lo que esté en /docker-entrypoint-initdb.d). Si cambias el esquema después, hay que
-- aplicar el cambio a mano o recrear el volumen (docker compose down -v; borra los datos).

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ---------------------------------------------------------------------------
-- services: catálogo (sincronizado desde config/services.yaml al arrancar el worker)
-- + el estado actual de cada servicio (la "máquina de estados" del checker).
-- ---------------------------------------------------------------------------
CREATE TABLE services (
    id                   TEXT PRIMARY KEY,
    name                 TEXT        NOT NULL,
    category             TEXT        NOT NULL,
    url                  TEXT        NOT NULL,
    interval_seconds     INT         NOT NULL,
    slow_threshold_ms    INT         NOT NULL,
    enabled              BOOLEAN     NOT NULL DEFAULT TRUE,
    status               TEXT        NOT NULL DEFAULT 'unknown'
                         CHECK (status IN ('unknown', 'up', 'degraded', 'down')),
    consecutive_failures INT         NOT NULL DEFAULT 0,
    consecutive_slow     INT         NOT NULL DEFAULT 0,
    failing_since        TIMESTAMPTZ,            -- hora de la 1.ª falla de la racha actual
    last_checked_at      TIMESTAMPTZ,
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- checks: una fila por revisión. Es una serie de tiempo que crece sin parar
-- (~20 servicios × 480 revisiones/día ≈ 10 000 filas/día), por eso es una
-- *hypertable* de TimescaleDB: por dentro se parte en "chunks" por tiempo, así las
-- consultas de "últimas 24 h" solo leen los chunks recientes y borrar datos viejos
-- es instantáneo (se descarta el chunk entero).
-- ---------------------------------------------------------------------------
CREATE TABLE checks (
    time          TIMESTAMPTZ NOT NULL,
    service_id    TEXT        NOT NULL REFERENCES services (id),
    ok            BOOLEAN     NOT NULL,
    status_code   INT,
    latency_ms    INT,
    error         TEXT,
    ssl_days_left INT
);
SELECT create_hypertable('checks', 'time', chunk_time_interval => INTERVAL '7 days');
CREATE INDEX checks_service_time_idx ON checks (service_id, time DESC);

-- Retención: los checks crudos se guardan 180 días. El resumen diario (abajo) se queda.
SELECT add_retention_policy('checks', INTERVAL '180 days');

-- Resumen diario precalculado (continuous aggregate). La barra de 90 días de la página
-- lee de aquí en vez de recorrer ~900 000 checks crudos. Los días se cortan a medianoche
-- de Panamá, no de UTC.
CREATE MATERIALIZED VIEW checks_daily
WITH (timescaledb.continuous, timescaledb.materialized_only = false) AS
SELECT
    service_id,
    time_bucket(INTERVAL '1 day', time, 'America/Panama') AS day,
    count(*)                         AS total,
    count(*) FILTER (WHERE ok)       AS ok_count,
    avg(latency_ms) FILTER (WHERE ok) AS avg_latency_ms
FROM checks
GROUP BY service_id, day
WITH NO DATA;

SELECT add_continuous_aggregate_policy('checks_daily',
    start_offset      => INTERVAL '3 days',
    end_offset        => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

-- ---------------------------------------------------------------------------
-- incidents: se abre al confirmar la caída y se cierra al recuperarse.
-- ---------------------------------------------------------------------------
CREATE TABLE incidents (
    id          BIGSERIAL PRIMARY KEY,
    service_id  TEXT        NOT NULL REFERENCES services (id),
    started_at  TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ,
    cause       TEXT,
    -- Columna calculada: la DB la mantiene sola, nunca puede quedar desfasada.
    duration    INTERVAL GENERATED ALWAYS AS (resolved_at - started_at) STORED
);
-- Garantía a nivel de DB: como máximo UN incidente abierto por servicio.
CREATE UNIQUE INDEX incidents_one_open_per_service
    ON incidents (service_id) WHERE resolved_at IS NULL;
CREATE INDEX incidents_started_idx ON incidents (started_at DESC);

-- ---------------------------------------------------------------------------
-- postmortems: borrador con IA (Fase 4) que el admin revisa antes de publicar.
-- ---------------------------------------------------------------------------
CREATE TABLE postmortems (
    id          BIGSERIAL PRIMARY KEY,
    incident_id BIGINT      NOT NULL UNIQUE REFERENCES incidents (id) ON DELETE CASCADE,
    draft       TEXT        NOT NULL,
    status      TEXT        NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft', 'approved', 'rejected')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    reviewed_at TIMESTAMPTZ
);

-- ---------------------------------------------------------------------------
-- subscribers: privacidad por diseño. Solo guardamos el chat_id (necesario para
-- escribirle) y qué servicios sigue. Nada de nombres, usernames ni teléfonos.
-- muted_until implementa /silencio.
-- ---------------------------------------------------------------------------
CREATE TABLE subscribers (
    chat_id     BIGINT PRIMARY KEY,
    services    TEXT[]      NOT NULL DEFAULT '{}',
    muted_until TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Índice GIN: hace rápida la consulta "¿quién sigue el servicio X?" (services @> ARRAY['x']).
CREATE INDEX subscribers_services_idx ON subscribers USING GIN (services);
