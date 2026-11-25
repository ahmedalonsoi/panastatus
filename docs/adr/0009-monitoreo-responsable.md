# ADR-0009: Reglas de monitoreo responsable validadas en código

- **Estado:** Aceptado
- **Fecha:** 2026-11

## Contexto

PanaStatus hace peticiones a sitios de terceros (bancos, gobierno, universidades) sin
que nos lo hayan pedido. Hay que ser buen ciudadano de internet: no generar carga, no
parecer un ataque, ser identificable y respetar a quien pida no ser monitoreado.

## Decisión

Reglas que **el código hace cumplir** (no solo documentación):

- `interval_seconds` entre **60 y 300**: Pydantic rechaza cualquier otro valor al
  arrancar (`config.py`).
- Una sola petición `GET` por revisión. No se descarga el cuerpo de la respuesta, y el
  vencimiento del certificado TLS se lee de la **misma** conexión.
- Solo URLs públicas. En portales con inicio de sesión (Moodle, matrícula) se consulta
  la página pública de *login*; **nunca** se envían credenciales.
- **User-Agent identificable** con URL explicativa y correo de contacto:
  `PanaStatusBot/x.y (+https://<dominio>/bot/; contacto)`. El worker **no arranca** sin
  `MONITOR_CONTACT`.
- La página `/bot/` explica todo y ofrece **exclusión en 48 horas**. Las exclusiones se
  hacen con `enabled: false` y un comentario con fecha y motivo, sin borrar el historial.
- Los portales universitarios se revisan cada 5 minutos (lo mínimo posible).
- Un sitio que da falsos "caído" por problemas técnicos del lado del cliente (por
  ejemplo, una cadena TLS incompleta que los navegadores sí completan) se **pausa**
  documentando el motivo, en vez de publicar algo engañoso.

## Consecuencias

- Unas 290–1 440 peticiones diarias por sitio: menos que un solo visitante navegando.
- Cualquiera puede auditar qué se monitorea y con qué frecuencia en
  `config/services.yaml`, que es público.
