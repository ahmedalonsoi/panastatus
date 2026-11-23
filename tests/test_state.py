"""Tests de la máquina de estados (la lógica más importante del proyecto)."""

from datetime import UTC, datetime, timedelta

from panastatus.checker import CheckResult
from panastatus.state import Event, ServiceState, evaluate

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
PARAMS = {"failure_threshold": 2, "slow_threshold_ms": 3000, "slow_consecutive": 2}


def ok(minute: int = 0, latency: int = 200) -> CheckResult:
    return CheckResult("svc", T0 + timedelta(minutes=minute), True, 200, latency, None, 90)


def fail(minute: int = 0) -> CheckResult:
    return CheckResult("svc", T0 + timedelta(minutes=minute), False, None, None, "timeout", None)


def run(state: ServiceState, *results: CheckResult) -> tuple[ServiceState, list]:
    events = []
    for r in results:
        state, event = evaluate(state, r, **PARAMS)
        events.append(event)
    return state, events


def test_una_sola_falla_no_es_caida():
    state, events = run(ServiceState("up"), fail())
    assert state.status == "up"
    assert events == [None]


def test_dos_fallas_seguidas_confirman_caida_desde_la_primera():
    state, events = run(ServiceState("up"), fail(0), fail(3))
    assert state.status == "down"
    assert events == [None, Event.DOWN]
    # El incidente empieza en la primera falla, no en la que confirma.
    assert state.failing_since == T0


def test_falla_aislada_se_resetea_con_un_ok():
    state, events = run(ServiceState("up"), fail(0), ok(3), fail(6))
    assert state.status == "up"
    assert events == [None, None, None]


def test_caida_no_se_notifica_dos_veces():
    _, events = run(ServiceState("up"), fail(0), fail(3), fail(6), fail(9))
    assert events.count(Event.DOWN) == 1


def test_recuperacion():
    state, events = run(ServiceState("up"), fail(0), fail(3), ok(6))
    assert state.status == "up"
    assert events == [None, Event.DOWN, Event.RECOVERED]
    assert state.failing_since is None


def test_lentitud_requiere_dos_seguidas_y_avisa_una_vez():
    state, events = run(ServiceState("up"), ok(0, 5000), ok(3, 5000), ok(6, 5000), ok(9, 200))
    assert events == [None, Event.SLOW, None, None]
    assert state.status == "up"


def test_servicio_nuevo_caido_desde_el_inicio():
    state, events = run(ServiceState(), fail(0), fail(3))
    assert state.status == "down"
    assert events == [None, Event.DOWN]
