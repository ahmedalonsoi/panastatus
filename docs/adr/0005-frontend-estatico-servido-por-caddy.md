# ADR-0005: Next.js exportado estático, servido por Caddy

- **Estado:** Aceptado
- **Fecha:** 2026-11

## Contexto

La página de estado es lo que más tráfico recibe justo cuando **algo se cae** (todos
entran a ver si es general). Debe ser rápida, barata y no depender de un servidor de
aplicaciones adicional. Los datos cambian cada minuto y vienen de la API.

## Decisión

- **Next.js + TypeScript + Tailwind** con `output: "export"`: el build genera HTML, CSS
  y JS estáticos. No hay servidor de Node en producción.
- Los datos se piden en el navegador a `/api/*` con **SWR** (refresco cada 60 s y al
  volver a la pestaña).
- **Caddy** sirve los archivos estáticos, hace de proxy de `/api` hacia FastAPI, obtiene
  el certificado HTTPS automáticamente y agrega cabeceras de seguridad (CSP, HSTS,
  `nosniff`). Los archivos con hash se cachean por un año.

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| Next.js con servidor (SSR) | Un proceso más que operar; el contenido cambia cada minuto y no necesita SEO por petición. |
| Plantillas en FastAPI | Menos estándar en el mercado y peor experiencia de desarrollo para una interfaz rica. |
| Nginx | Caddy obtiene y renueva el certificado solo, con una configuración mucho más corta. |

## Consecuencias

- Producción sirve archivos estáticos: soporta picos de tráfico sin costo extra.
- La CSP se limita al propio dominio porque no hay scripts de terceros. Requiere
  `'unsafe-inline'` para los scripts en línea que genera Next.js; se podría endurecer
  con *hashes* calculados en el build.
- Las rutas dinámicas (por ejemplo, una página por servicio) requieren
  `generateStaticParams`; hoy el detalle se muestra dentro de la misma página.
