# Política de seguridad

## Reportar una vulnerabilidad

**No abras un issue público.** Usa el reporte privado de GitHub:
*Security → Report a vulnerability* en este repositorio, o escribe a
**panastatus.contacto@gmail.com** con el asunto `SEGURIDAD`.

Incluye qué encontraste, cómo reproducirlo y su impacto. Respondo en un máximo de
**72 horas** y te mantengo al tanto hasta la corrección. Si lo deseas, se te da crédito
en el [CHANGELOG](CHANGELOG.md).

## Alcance

| Dentro | Fuera |
|---|---|
| Este repositorio (código, workflows, configuración) | Los sitios monitoreados (repórtalos a cada institución) |
| La página y la API pública desplegadas desde aquí | Ataques de denegación de servicio o pruebas de carga |
| El bot de Telegram | Ingeniería social |

## Medidas implementadas

**Datos y privacidad**
- Del bot solo se guarda el `chat_id` y la lista de servicios seguidos. `/stop` los borra.
- El rol de reportes `powerbi_reader` solo puede leer el esquema `reporting`; no ve
  suscriptores (verificado por una prueba de integración).

**Aplicación**
- API de **solo lectura** (solo `GET`), con límite de 60 peticiones/min por IP y
  parámetros acotados (por ejemplo, `hours` ≤ 168).
- Todo el SQL usa parámetros (`$1`); nunca concatenación.
- Mensajes de Telegram con `html.escape` para nombres y errores externos.
- Botones de aprobación de post-mortems verificados contra `ADMIN_CHAT_ID` en el
  servidor (no se confía en que el botón llegue solo al admin).
- La salida de la IA nunca se publica sin aprobación humana
  ([ADR-0007](docs/adr/0007-ia-con-revision-humana.md)).

**Web**
- Cabeceras: `Content-Security-Policy` limitada al propio dominio (`default-src 'self'`,
  `frame-ancestors 'none'`, `object-src 'none'`), `Strict-Transport-Security`,
  `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy`; sin cabecera
  `Server`. Sin scripts de terceros; las fuentes se sirven desde el propio dominio.
- Limitación conocida: la CSP permite `'unsafe-inline'` en scripts porque el export
  estático de Next.js inserta scripts en línea. Mejora futura: CSP con *hashes*
  generados en el build.

**Infraestructura**
- Solo Caddy (80/443) se expone a internet. Base de datos, Grafana y Prometheus escuchan
  en `127.0.0.1` y se accede por túnel SSH.
- La imagen de Python corre sin root. Límites de memoria por contenedor en producción.
- Servidor: SSH solo con clave y solo desde la IP del administrador, fail2ban,
  actualizaciones automáticas de seguridad, metadatos de instancia v1 deshabilitados.

**Cadena de suministro**
- Secretos solo en `.env` (ignorado por git) y GitHub Secrets. **gitleaks** revisa todo
  el historial en CI y en pre-commit.
- Imágenes escaneadas con **Trivy** (vulnerabilidades críticas bloquean el despliegue),
  con SBOM y atestación de procedencia.
- Acciones de GitHub fijadas por **SHA**; dependencias e imágenes con versión fija;
  **Dependabot** semanal; `npm audit` en CI.
- El token de GHCR del despliegue es temporal (vence con el job) y viaja por stdin.
