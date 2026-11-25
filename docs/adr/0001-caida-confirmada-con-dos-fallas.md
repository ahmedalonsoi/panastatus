# ADR-0001: Una caída se confirma con 2 fallas seguidas

- **Estado:** Aceptado
- **Fecha:** 2026-11

## Contexto

Revisamos sitios externos desde un solo punto de internet. Una sola revisión fallida
puede deberse a un paquete perdido, un reinicio rápido del servidor del sitio, un
balanceador que rota o un problema de nuestra propia red. Si cada falla aislada abriera
un incidente y enviara un aviso, los usuarios recibirían falsas alarmas y dejarían de
confiar en el bot (fatiga de alertas).

## Decisión

- Una caída se **confirma** con `failure_threshold = 2` revisiones fallidas **seguidas**.
- El incidente **empieza** en la hora de la **primera** falla de la racha, no en la que
  lo confirma (la duración no se subestima).
- La **recuperación** se confirma con **una** revisión exitosa: avisar rápido que el
  servicio volvió es lo que más valora el usuario; si recae, se abre otro incidente.
- La lentitud usa la misma idea: `slow_consecutive = 2` revisiones lentas seguidas.

Toda la lógica vive en `state.py` como **función pura** (sin red, DB ni reloj), probada
exhaustivamente en `tests/test_state.py`.

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| Alertar a la primera falla | Demasiadas falsas alarmas. |
| 3 o más fallas | Con intervalos de 3–5 min, una caída real tardaría 10–15 min en anunciarse. |
| Revisar desde varias regiones y votar | Lo ideal, pero multiplica el costo y la carga sobre los sitios; queda como mejora futura. |

## Consecuencias

- Una caída real se anuncia entre 1 y 2 intervalos después de empezar (3–10 min).
- Las caídas más cortas que un intervalo pueden no detectarse (limitación documentada
  en la página y en `docs/powerbi.md`).
- El umbral es configurable (`FAILURE_THRESHOLD`) sin tocar código.
