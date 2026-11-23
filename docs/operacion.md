# Runbook de operación

Atajo usado en este documento (en el servidor, dentro de `/opt/panastatus`):

```bash
alias dc='docker compose -f docker-compose.yml -f deploy/compose.prod.yml'
```

En local, `dc` es simplemente `docker compose`.

## Estado rápido

```bash
dc ps                                  # todo debe estar "running" (migrate: "exited (0)")
dc logs --tail=100 worker              # últimas revisiones
curl -s https://tudominio.com/health   # {"status":"ok",...}
```

Grafana (por túnel, ver `docs/despliegue.md`) → dashboard **PanaStatus — Operación**.

## Alertas internas (llegan por Telegram desde Grafana)

| Alerta | Qué significa | Qué hacer |
|---|---|---|
| **Checker sin revisiones** | El worker no registra revisiones desde hace 10 min | `dc ps worker` → `dc logs --tail=200 worker`. Si murió: `dc up -d worker`. Si la DB no responde: `dc logs db`. |
| **Fallas masivas** | Más del 50 % de las revisiones fallan | Casi siempre es **nuestra** red o el DNS, no 18 sitios a la vez. Prueba en el servidor `curl -I https://www.google.com` y `resolvectl status`. No anuncies caídas hasta descartarlo. |
| **Envíos a Telegram fallando** | Telegram rechaza los mensajes | `dc logs worker \| grep telegram`. Un 401 indica que el token fue revocado: genera uno nuevo con @BotFather y actualiza `.env`. |

## Logs útiles (Grafana → Explore → Loki)

```logql
{service="worker"} | json | level="error"
{service="worker"} | json | msg="revisión" | service_id="utp" | ok="false"
{service="web"} | json | status >= 500
```

## Respaldos

El servicio `backup` hace un `pg_dump` diario en `/opt/panastatus/backups/` y conserva los últimos 14.

**Copia fuera del servidor** (recomendado una vez por semana, desde tu PC):

```bash
scp deploy@<IP>:/opt/panastatus/backups/$(ssh deploy@<IP> 'ls -1t /opt/panastatus/backups | head -1') .
```

### Restaurar

```bash
dc stop worker api bot
dc exec -T db pg_restore --clean --if-exists -U panastatus -d panastatus < backups/panastatus-AAAAMMDD-HHMM.dump
dc up -d
```

Practica una restauración en local al menos una vez: un respaldo que nunca se probó no es un respaldo.

## Cambios frecuentes

- **Agregar un servicio**: edita `config/services.yaml`, valida con `uv run python -m panastatus.worker --once` y haz push. El despliegue lo aplica.
- **Excluir un sitio (pedido del dueño)**: `enabled: false` con un comentario de fecha y motivo, en menos de 48 h.
- **Cambiar el esquema de la DB**: crea `db/migrations/00N_descripcion.sql`. **Nunca** edites una migración ya aplicada.
- **Regenerar un post-mortem**: `dc exec worker python -m panastatus.postmortem <incident_id>`.
- **Rotar un secreto**: cambia el valor en `.env` y ejecuta `dc up -d` (los contenedores leen el `.env` al recrearse).

## Problemas comunes

| Síntoma | Causa probable | Solución |
|---|---|---|
| La página carga pero sin datos | La API no responde | `dc logs api`; `dc ps migrate` debe salir con código 0 |
| Certificado no válido | El DNS no apunta a la IP, o el puerto 80 está cerrado | `nslookup dominio`; `dc logs web \| grep -i acme` |
| Disco lleno | Logs o imágenes viejas | `df -h`; `docker system df`; `docker image prune -a` |
| No puedo entrar por SSH | Cambió tu IP pública | Actualiza `admin_cidr` y ejecuta `tofu apply` (solo cambia el firewall) |
