#!/bin/sh
# Despliegue en el servidor (lo llama GitHub Actions por SSH; también sirve a mano):
#
#   sh deploy/deploy.sh <imagen-app> <imagen-web>
#
# 1. Anota las imágenes actuales (para poder volver atrás).
# 2. Descarga las nuevas y reinicia solo lo que cambió (las migraciones corren antes).
# 3. Verifica que la API responda /health. Si no, ROLLBACK a las imágenes anteriores.
set -eu
cd "$(dirname "$0")/.."

NEW_APP="$1"
NEW_WEB="$2"
COMPOSE="docker compose -f docker-compose.yml -f deploy/compose.prod.yml"

[ -f .env ] || { echo "deploy: falta /opt/panastatus/.env (ver deploy/.env.production.example)"; exit 1; }
mkdir -p backups

OLD_APP="$(sed -n 's/^APP_IMAGE=//p' .env)"
OLD_WEB="$(sed -n 's/^WEB_IMAGE=//p' .env)"

set_images() {
    # Reemplaza (o agrega) APP_IMAGE y WEB_IMAGE en el .env.
    for pair in "APP_IMAGE=$1" "WEB_IMAGE=$2"; do
        key="${pair%%=*}"
        if grep -q "^$key=" .env; then
            sed -i "s|^$key=.*|$pair|" .env
        else
            echo "$pair" >> .env
        fi
    done
}

healthy() {
    # Hasta 90 s para que la API arranque y conecte con la DB.
    i=0
    while [ $i -lt 30 ]; do
        if $COMPOSE exec -T api python -c \
            "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" \
            >/dev/null 2>&1; then
            return 0
        fi
        i=$((i + 1))
        sleep 3
    done
    return 1
}

echo "deploy: $NEW_APP / $NEW_WEB"
set_images "$NEW_APP" "$NEW_WEB"
$COMPOSE pull --quiet
$COMPOSE up -d --remove-orphans

if healthy; then
    echo "deploy: OK"
    docker image prune -f >/dev/null # borra imágenes viejas sin usar (ahorra disco)
    exit 0
fi

echo "deploy: la API no respondió /health; volviendo a la versión anterior" >&2
$COMPOSE logs --tail=50 api migrate >&2 || true
if [ -n "$OLD_APP" ] && [ -n "$OLD_WEB" ]; then
    set_images "$OLD_APP" "$OLD_WEB"
    $COMPOSE up -d --remove-orphans
    healthy && echo "deploy: rollback OK ($OLD_APP)" >&2
fi
exit 1
