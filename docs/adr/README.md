# Registro de decisiones de arquitectura (ADR)

Cada archivo documenta **una** decisión importante: el contexto, lo que se decidió, las
alternativas descartadas y sus consecuencias. Formato de Michael Nygard.

Reglas:

- Un ADR aceptado **no se edita**. Si la decisión cambia, se escribe uno nuevo que lo
  reemplaza y se marca el viejo como *Reemplazado por ADR-XXXX*.
- Se escribe cuando la decisión es costosa de revertir o cuando alguien preguntaría
  "¿por qué se hizo así?".

| ADR | Decisión | Estado |
|---|---|---|
| [0001](0001-caida-confirmada-con-dos-fallas.md) | Una caída se confirma con 2 fallas seguidas | Aceptado |
| [0002](0002-timescaledb-para-series-de-tiempo.md) | PostgreSQL + TimescaleDB para las revisiones | Aceptado |
| [0003](0003-sql-explicito-sin-orm.md) | SQL explícito con asyncpg, sin ORM | Aceptado |
| [0004](0004-un-proceso-por-responsabilidad.md) | Worker, API y bot como procesos separados | Aceptado |
| [0005](0005-frontend-estatico-servido-por-caddy.md) | Next.js exportado estático, servido por Caddy | Aceptado |
| [0006](0006-opentelemetry-y-stack-grafana.md) | OpenTelemetry + Alloy + Prometheus + Loki + Grafana | Aceptado |
| [0007](0007-ia-con-revision-humana.md) | Post-mortems con IA solo con aprobación humana | Aceptado |
| [0008](0008-docker-compose-en-un-servidor.md) | Docker Compose en un servidor, no Kubernetes | Aceptado |
| [0009](0009-monitoreo-responsable.md) | Reglas de monitoreo responsable validadas en código | Aceptado |
