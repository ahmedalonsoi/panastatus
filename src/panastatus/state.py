"""Máquina de estados de un servicio: decide cuándo hay caída, recuperación o lentitud.

Es una función PURA (sin red, sin DB, sin reloj): recibe el estado anterior y el
resultado de la revisión, y devuelve el estado nuevo + el evento a notificar (si hay).
Por eso se puede probar exhaustivamente con tests simples (tests/test_state.py).

Estados:
    unknown  -> todavía no sabemos (recién agregado)
    up       -> funciona
    degraded -> funciona pero lento (N revisiones lentas seguidas)
    down     -> caída confirmada (N fallas seguidas)

Reglas:
- Una sola falla NO cambia el estado público: puede ser un fallo de red puntual.
  Con ``failure_threshold`` (2) fallas seguidas -> "down" y se emite DOWN (abre incidente).
- Estando "down", la primera revisión OK -> "up" y se emite RECOVERED (cierra incidente).
  Recuperarse con 1 éxito es intencional: avisar rápido que ya volvió es lo que más
  valora el usuario, y si vuelve a caer se abre otro incidente.
- Lentitud: ``slow_consecutive`` revisiones OK pero lentas seguidas -> "degraded" y se
  emite SLOW una sola vez (no en cada revisión, para no hacer spam).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from panastatus.checker import CheckResult


class Event(StrEnum):
    DOWN = "down"
    RECOVERED = "recovered"
    SLOW = "slow"


@dataclass(frozen=True, slots=True)
class ServiceState:
    status: str = "unknown"
    consecutive_failures: int = 0
    consecutive_slow: int = 0
    failing_since: datetime | None = None


def evaluate(
    state: ServiceState,
    result: CheckResult,
    *,
    failure_threshold: int,
    slow_threshold_ms: int,
    slow_consecutive: int,
) -> tuple[ServiceState, Event | None]:
    # --- La revisión falló ---
    if not result.ok:
        failures = state.consecutive_failures + 1
        # El incidente "empieza" en la PRIMERA falla de la racha, no en la que lo confirma.
        failing_since = state.failing_since or result.time
        if failures >= failure_threshold and state.status != "down":
            return ServiceState("down", failures, 0, failing_since), Event.DOWN
        # Falla aún no confirmada (o ya estaba caído): el estado público no cambia.
        return ServiceState(state.status, failures, 0, failing_since), None

    # --- La revisión fue OK ---
    is_slow = result.latency_ms is not None and result.latency_ms > slow_threshold_ms
    slow = state.consecutive_slow + 1 if is_slow else 0

    if state.status == "down":
        return ServiceState("up", 0, slow, None), Event.RECOVERED

    if slow >= slow_consecutive:
        event = Event.SLOW if state.status != "degraded" else None
        return ServiceState("degraded", 0, slow, None), event

    return ServiceState("up", 0, slow, None), None
