# ADR-0004: Worker, API y bot como procesos separados

- **Estado:** Aceptado
- **Fecha:** 2026-11

## Contexto

El sistema tiene tres trabajos con perfiles muy distintos:

1. **Revisar** sitios y alertar (crítico, siempre activo).
2. **Servir** la API pública (tráfico variable, expuesto a internet).
3. **Conversar** con usuarios de Telegram (interactivo).

## Decisión

Una sola imagen de Docker y **tres contenedores** con distinto comando: `worker`, `api`
y `bot`. Comparten la base de datos, no memoria.

- El worker **envía** las alertas por HTTP directo a la API de Telegram, sin depender
  del proceso del bot. Si el bot falla, las alertas siguen saliendo.
- Dentro del worker, **una tarea asyncio por servicio**, cada una con su intervalo y un
  desfase aleatorio inicial (*jitter*) para no revisar todo a la vez.
- El estado de cada servicio se lee con `SELECT ... FOR UPDATE`, así dos procesos nunca
  lo actualizan a la vez.

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| Un solo proceso con todo | Un error en el bot o un pico de tráfico en la API afectaría las revisiones. |
| Cola de mensajes (Redis, RabbitMQ) | Otra pieza que operar sin necesidad a esta escala; la DB ya coordina. |
| Celery / cron para las revisiones | asyncio maneja cientos de revisiones concurrentes en un solo proceso liviano. |

## Consecuencias

- Cada proceso se reinicia, escala y observa por separado (métricas con `service.name`).
- Un solo `Dockerfile` y un solo conjunto de dependencias.
