# Reportes en Power BI

PanaStatus expone una **capa de reportes** en el esquema `reporting` de PostgreSQL (migración `db/migrations/002_reporting.sql`). Son vistas ya preparadas para analizar: horas de Panamá, porcentajes y minutos. Power BI se conecta con el rol `powerbi_reader`, que **solo** puede leer ese esquema; no ve suscriptores ni `chat_id` de Telegram.

## Modelo (esquema estrella)

```
                 ┌──────────────────────┐
                 │   dim_service (1)    │
                 └──────────┬───────────┘
        ┌───────────────────┼────────────────────┐
        ▼ (*)               ▼ (*)                ▼ (*)
fact_service_daily    fact_incidents     fact_latency_hourly
 (servicio × día)    (1 por incidente)  (servicio × hora, 30 d)
        ▲ (*)               ▲ (*)
        └──────┬────────────┘
         dim_date (1)  ← tabla calculada en Power BI (DAX)

sla_monthly: resumen mensual por servicio (tabla independiente, para tarjetas y tablas)
```

| Vista | Grano | Columnas clave |
|---|---|---|
| `dim_service` | servicio | `service_id`, `service_name`, `category`, `url` |
| `fact_service_daily` | servicio × día | `date`, `checks`, `ok_checks`, `failed_checks`, `uptime_pct`, `avg_latency_ms` |
| `fact_incidents` | incidente | `started_at_local`, `date`, `start_hour`, `start_weekday`, `duration_minutes`, `cause`, `has_postmortem` |
| `fact_latency_hourly` | servicio × hora | `hour_local`, `p50_ms`, `p95_ms`, `failed_checks` |
| `sla_monthly` | servicio × mes | `uptime_pct`, `est_downtime_minutes`, `incidents`, `mttr_minutes` |

## Opción A: CSV (la más simple, sin conexión)

```bash
uv run python -m panastatus.export_reports        # genera reports/*.csv
```

En Power BI Desktop: **Obtener datos → Texto/CSV**, carga los 5 archivos y sigue con *Relaciones* (abajo).

## Opción B: conexión directa (datos siempre al día)

### 1. Activar el rol (una sola vez, en el servidor)

```bash
ssh deploy@<IP>
cd /opt/panastatus
docker compose -f docker-compose.yml -f deploy/compose.prod.yml exec db \
  psql -U panastatus -c "ALTER ROLE powerbi_reader WITH LOGIN PASSWORD '<contraseña larga>';"
```

En local es lo mismo con `docker compose exec db psql ...`.

### 2. Túnel SSH (la base de datos NO está expuesta a internet)

En producción, la base solo escucha en `127.0.0.1` del servidor. Desde tu PC, abre un túnel y déjalo abierto mientras uses Power BI:

```bash
ssh -N -L 15432:127.0.0.1:5432 deploy@<IP>
```

### 3. Conectar Power BI Desktop

1. **Obtener datos → Base de datos PostgreSQL**.
2. Servidor: `localhost:15432` (en local, sin túnel: `localhost:5432`). Base de datos: `panastatus`.
3. Modo: **Importar**, con actualización programada.
4. Credenciales: *Base de datos*, usuario `powerbi_reader`.
5. Marca las 5 tablas `reporting.*`.

## Relaciones

En *Vista de modelo*:

- `dim_service[service_id]` 1 → * `fact_service_daily[service_id]`, `fact_incidents[service_id]`, `fact_latency_hourly[service_id]`, `sla_monthly[service_id]`.
- `dim_date[Date]` 1 → * `fact_service_daily[date]` y `fact_incidents[date]`.

Tabla de fechas (*Modelado → Nueva tabla*):

```dax
dim_date =
ADDCOLUMNS (
    CALENDAR ( DATE ( 2026, 1, 1 ), TODAY () ),
    "Año", YEAR ( [Date] ),
    "Mes", FORMAT ( [Date], "mmm yyyy" ),
    "MesNum", YEAR ( [Date] ) * 100 + MONTH ( [Date] ),
    "DiaSemana", FORMAT ( [Date], "dddd" )
)
```

Márcala como *tabla de fechas* y ordena `Mes` por `MesNum`.

## Medidas DAX

```dax
-- Disponibilidad ponderada por cantidad de revisiones (no el promedio de porcentajes,
-- que daría el mismo peso a un día con 10 revisiones que a uno con 480).
Disponibilidad % =
DIVIDE ( SUM ( fact_service_daily[ok_checks] ), SUM ( fact_service_daily[checks] ) )

Incidentes = COUNTROWS ( fact_incidents )

Minutos caído = SUM ( fact_incidents[duration_minutes] )

-- MTTR: tiempo medio de recuperación (solo incidentes cerrados)
MTTR (min) =
AVERAGEX ( FILTER ( fact_incidents, NOT fact_incidents[is_open] ), fact_incidents[duration_minutes] )

-- MTBF: tiempo medio entre fallas, en horas, dentro del período filtrado
MTBF (h) =
VAR Horas = DATEDIFF ( MIN ( dim_date[Date] ), MAX ( dim_date[Date] ) + 1, HOUR )
RETURN DIVIDE ( Horas - [Minutos caído] / 60, [Incidentes] )

-- ¿Cumple un objetivo de 99.5 %? (cambia el objetivo según el análisis)
Cumple SLO 99.5 = IF ( [Disponibilidad %] >= 0.995, "✓ Cumple", "✗ No cumple" )

Latencia p95 (ms) = AVERAGE ( fact_latency_hourly[p95_ms] )
```

## Páginas sugeridas

1. **Resumen ejecutivo**: tarjetas con Disponibilidad %, Incidentes, MTTR y MTBF; tabla por servicio con *Cumple SLO* (formato condicional); segmentador por categoría y mes.
2. **Confiabilidad**: disponibilidad diaria por servicio (gráfico de líneas, una categoría a la vez para no saturar) e incidentes por mes (columnas).
3. **Patrones**: matriz `start_weekday` × `start_hour` con el conteo de incidentes (¿hay horarios de mantenimiento?) y top 10 de servicios por minutos caído.
4. **Rendimiento**: `p95_ms` por hora para el servicio elegido, comparado con su `slow_threshold_ms`.

> **Nota de método.** El tiempo caído es una estimación: solo vemos cada sitio cada 1–5 minutos, desde afuera. Una caída de 30 segundos entre dos revisiones no se registra. Conviene mencionarlo en el reporte.
