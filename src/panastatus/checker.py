"""Checker: hace UNA revisión de un servicio y devuelve el resultado.

Este módulo no sabe nada de base de datos ni de alertas: recibe un servicio, hace la
petición y devuelve un ``CheckResult``. Separarlo así lo hace fácil de probar (los tests
simulan respuestas HTTP sin red) y fácil de razonar.

Qué medimos en cada revisión:
- Disponibilidad: ¿respondió con un código HTTP < 400?
- Latencia: tiempo hasta recibir los *encabezados* de la respuesta (incluye DNS, TCP,
  TLS y redirecciones). No descargamos el cuerpo: es más liviano para el sitio y para
  nosotros, y la latencia de encabezados es lo que siente el usuario al "abrir" la página.
- Vigencia SSL: días que le quedan al certificado. Se lee de la MISMA conexión HTTPS,
  sin hacer una petición extra (monitoreo responsable).
"""

from __future__ import annotations

import ssl
import time
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from panastatus.config import ServiceConfig, Settings


@dataclass(frozen=True, slots=True)
class CheckResult:
    service_id: str
    time: datetime  # en UTC; se convierte a hora de Panamá solo al mostrar
    ok: bool
    status_code: int | None
    latency_ms: int | None
    error: str | None
    ssl_days_left: int | None


def build_client(settings: Settings) -> httpx.AsyncClient:
    """Cliente HTTP compartido por todas las revisiones."""
    return httpx.AsyncClient(
        headers={"User-Agent": settings.user_agent},
        timeout=httpx.Timeout(settings.request_timeout_seconds),
        follow_redirects=True,  # muchos sitios redirigen / -> /es/ o http -> https
        max_redirects=5,
    )


def _ssl_days_left(response: httpx.Response) -> int | None:
    """Días restantes del certificado del servidor que respondió.

    httpx expone el socket de la conexión en ``response.extensions["network_stream"]``
    mientras la respuesta está abierta. De ahí sacamos el objeto SSL y su certificado.
    Si no es HTTPS (o en los tests, donde no hay red real) devolvemos None.
    """
    stream = response.extensions.get("network_stream")
    if stream is None:
        return None
    ssl_object = stream.get_extra_info("ssl_object")
    if ssl_object is None:
        return None
    cert = ssl_object.getpeercert()
    if not cert or "notAfter" not in cert:
        return None
    expires_at = ssl.cert_time_to_seconds(cert["notAfter"])
    return int((expires_at - time.time()) // 86400)


def _describe_connect_error(exc: Exception) -> str:
    """Traduce errores de conexión a algo entendible para el público."""
    text = str(exc)
    if "CERTIFICATE_VERIFY_FAILED" in text or "certificate" in text.lower():
        return f"Certificado SSL inválido: {text}"
    if "getaddrinfo" in text or "Name or service not known" in text or "nodename" in text:
        return "Error de DNS: el dominio no resuelve"
    if "refused" in text.lower():
        return "Conexión rechazada"
    return f"Error de conexión: {text or type(exc).__name__}"


async def check_service(client: httpx.AsyncClient, service: ServiceConfig) -> CheckResult:
    """Revisa un servicio una vez. Nunca lanza excepciones de red: las convierte en
    un resultado con ok=False y un mensaje de error."""
    checked_at = datetime.now(UTC)
    start = time.perf_counter()
    error: str
    try:
        # stream() devuelve en cuanto llegan los encabezados; al salir del "with" se cierra
        # la conexión sin descargar el cuerpo de la página.
        async with client.stream("GET", str(service.url)) as response:
            latency_ms = int((time.perf_counter() - start) * 1000)
            ok = response.status_code < 400
            return CheckResult(
                service_id=service.id,
                time=checked_at,
                ok=ok,
                status_code=response.status_code,
                latency_ms=latency_ms,
                error=None if ok else f"HTTP {response.status_code}",
                ssl_days_left=_ssl_days_left(response),
            )
    except httpx.TimeoutException:
        error = "Tiempo de espera agotado"
    except httpx.ConnectError as exc:
        error = _describe_connect_error(exc)
    except httpx.TooManyRedirects:
        error = "Demasiadas redirecciones"
    except httpx.HTTPError as exc:
        error = f"{type(exc).__name__}: {exc}"

    return CheckResult(
        service_id=service.id,
        time=checked_at,
        ok=False,
        status_code=None,
        latency_ms=None,
        error=error[:500],
        ssl_days_left=None,
    )
