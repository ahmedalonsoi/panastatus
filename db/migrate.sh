#!/bin/sh
# Migraciones de base de datos: aplica en orden los archivos db/migrations/NNN_*.sql que
# aún no se hayan aplicado, y anota cada uno en la tabla schema_migrations.
#
# Lo ejecuta el servicio "migrate" de docker compose ANTES de que arranquen worker, api y
# bot (depends_on: service_completed_successfully). Si una migración falla, el script sale
# con error y la aplicación no arranca con un esquema a medias.
#
# Reglas:
#   - Nunca editar una migración ya aplicada: crear una nueva (002_, 003_...).
#   - Se usa psql (no Python) porque algunas sentencias de TimescaleDB, como crear una
#     continuous aggregate, no pueden ir dentro de una transacción; psql ejecuta cada
#     sentencia por separado.
#
# Variables (las estándar de psql): PGHOST, PGUSER, PGPASSWORD, PGDATABASE.
set -eu

# Sin avisos NOTICE ("ya existe, se omite") en la salida.
export PGOPTIONS="-c client_min_messages=warning"

DIR="$(dirname "$0")/migrations"
PSQL="psql -v ON_ERROR_STOP=1 -X -q -At"

$PSQL -c "CREATE TABLE IF NOT EXISTS schema_migrations (
    version    TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);"

# Línea base: bases creadas antes de existir este script (el esquema se aplicaba con
# docker-entrypoint-initdb.d) ya tienen el 001. Se marca como aplicado sin ejecutarlo.
if [ "$($PSQL -c "SELECT count(*) FROM schema_migrations")" = "0" ] &&
   [ "$($PSQL -c "SELECT to_regclass('public.services') IS NOT NULL")" = "t" ]; then
    $PSQL -c "INSERT INTO schema_migrations (version) VALUES ('001_schema')"
    echo "migrate: base existente; 001_schema marcado como aplicado"
fi

applied=0
for file in "$DIR"/[0-9][0-9][0-9]_*.sql; do
    [ -e "$file" ] || continue
    version="$(basename "$file" .sql)"
    done_already="$($PSQL -c "SELECT 1 FROM schema_migrations WHERE version = '$version'")"
    if [ -z "$done_already" ]; then
        echo "migrate: aplicando $version"
        $PSQL -f "$file" >/dev/null  # sin imprimir los resultados de los SELECT
        $PSQL -c "INSERT INTO schema_migrations (version) VALUES ('$version')"
        applied=$((applied + 1))
    fi
done

echo "migrate: listo ($applied migraciones nuevas)"
