# ADR-0007: Post-mortems con IA solo con aprobación humana

- **Estado:** Aceptado
- **Fecha:** 2026-11

## Contexto

Escribir un post-mortem de cada incidente largo toma tiempo, y los datos ya están en la
base: duración, errores, latencia antes y después, si otros servicios fallaron al mismo
tiempo, cuántas veces cayó en los últimos 30 días. Un modelo de lenguaje puede redactar
un buen borrador, pero también puede **inventar una causa**, y el texto se publica con
el nombre de una institución real.

## Decisión

- Solo para incidentes de **15 minutos o más** (`POSTMORTEM_MIN_MINUTES`).
- Al recuperarse el servicio, el worker reúne los datos y pide un borrador a la **API de
  Claude**. Las instrucciones exigen tono *blameless*, presentar la causa **solo como
  hipótesis** y tratar los datos como datos (no como instrucciones).
- El borrador llega al **admin por Telegram** con botones *Publicar* / *Descartar*.
  Nada se publica sin esa aprobación; un borrador ya revisado no se puede volver a
  aprobar (protección contra doble clic).
- Si la API rechaza la petición o falla, el incidente simplemente queda sin borrador.
- Sin `ANTHROPIC_API_KEY`, la función está apagada.

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| Publicar automáticamente | Riesgo de afirmar algo falso sobre una institución real. |
| Plantilla sin IA | Sin análisis: no relaciona la caída con otras ni con su historial. |
| No hacer post-mortems | Se pierde el aprendizaje, que es el objetivo de un post-mortem. |

## Consecuencias

- Costo de centavos por incidente largo, y solo si se activa.
- *Human in the loop*: la IA acelera, la persona decide.
- Se puede regenerar un borrador a mano: `python -m panastatus.postmortem <id>`.
