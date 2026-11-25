# SLO de PanaStatus

PanaStatus mide la disponibilidad de otros, así que **el propio monitor también necesita
objetivos medibles**. Este documento define los indicadores (SLI), los objetivos (SLO),
el presupuesto de errores y qué alerta protege cada uno.

> Vocabulario. **SLI**: lo que se mide (por ejemplo, % de minutos con revisiones).
> **SLO**: el objetivo para ese SLI en una ventana (≥ 99 % en 30 días). **Presupuesto de
> errores**: lo que se puede fallar sin incumplir el SLO (100 % − SLO).

## Objetivos

| # | Qué le importa al usuario | SLI (cómo se mide) | SLO (30 días) | Presupuesto |
|---|---|---|---|---|
| 1 | **Los datos están al día** | % de minutos en que hubo al menos una revisión en los últimos 10 min: `sum(increase(panastatus_checks_total[10m])) > 0` | **99 %** | ~7 h 12 min |
| 2 | **La página responde** | % de peticiones a `/api/*` sin error 5xx (métricas HTTP de FastAPI) | **99.5 %** | 0.5 % de las peticiones |
| 3 | **La página es rápida** | % de peticiones a `/api/*` respondidas en menos de 500 ms | **95 %** | 5 % de las peticiones |
| 4 | **Los avisos llegan** | % de envíos a Telegram con resultado `sent` sobre el total (`panastatus_notifications_total`) | **99 %** | 1 % de los envíos |
| 5 | **Las caídas se anuncian a tiempo** | Tiempo desde la 1.ª falla hasta el aviso | **≤ 2 intervalos** del servicio (por diseño, [ADR-0001](adr/0001-caida-confirmada-con-dos-fallas.md)) | — |

Los SLO están por debajo del 100 % a propósito: un solo servidor sin redundancia no puede
prometer más, y prometer de más es la forma más rápida de perder la confianza.

## Alertas que los protegen

Definidas como código en
[`observability/grafana/provisioning/alerting/alerts.yaml`](../observability/grafana/provisioning/alerting/alerts.yaml)
y enviadas al admin por Telegram:

| Alerta | Protege | Condición |
|---|---|---|
| **Checker sin revisiones** | SLO 1 | Cero revisiones en una ventana de 10 min, sostenido 5 min |
| **Fallas masivas** | SLO 1 (calidad de los datos) | Más del 50 % de las revisiones fallan (ventana de 10 min, sostenido 5 min): casi siempre es nuestra red, no 28 sitios a la vez |
| **Envíos a Telegram fallando** | SLO 4 | Más de 3 envíos fallidos en 15 minutos |

Qué hacer ante cada una: [docs/operacion.md](operacion.md).

## Política de presupuesto de errores

- **Presupuesto sano** (< 50 % consumido): se trabaja normal en funciones nuevas.
- **Presupuesto en riesgo** (50–100 %): se priorizan arreglos de confiabilidad sobre
  funciones nuevas, y cada despliegue requiere revisión manual.
- **Presupuesto agotado**: congelamiento de cambios que no sean de confiabilidad hasta
  que la ventana de 30 días se recupere. Se escribe un post-mortem *blameless* del
  incidente que lo agotó.

## Límites conocidos de la medición

- Se mide **desde afuera** y desde **un solo punto** de internet: una falla de ruta
  entre nuestro servidor y un sitio puede verse como caída de ese sitio.
- Una caída más corta que el intervalo de revisión (1–5 min) puede no registrarse.
- El tiempo caído es una **estimación** con resolución de un intervalo.

Estos límites se explican también en la página pública y en los reportes de Power BI.
