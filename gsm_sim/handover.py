"""Finite-state, measurement-based handover and coverage-loss model."""
from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import Mapping

import numpy as np

from gsm_sim.localization import TOWERS, expected_rssi

@dataclass(frozen=True)
class CallState:
    serving: str
    candidate: str | None = None
    candidate_count: int = 0
    connected: bool = True

@dataclass(frozen=True)
class Event:
    event: str
    source: str
    target: str
    modeled_delay_ms: int | None
    reason: str

def evaluate_report(
    state: CallState,
    measured_dbm: Mapping[str, float],
    bsc_lookup: Mapping[str, str],
    margin_db: float = 3.0,
    time_to_trigger: int = 2,
    min_target_dbm: float = -105,
    call_floor_dbm: float = -112,
    unavailable_targets: frozenset[str] = frozenset(),
) -> tuple[CallState, Event | None]:
    if time_to_trigger < 1:
        raise ValueError("Time-to-trigger must be at least 1 sample")
    if not state.connected:
        return state, None
    if state.serving not in measured_dbm or not set(measured_dbm).issubset(bsc_lookup):
        raise ValueError("Unknown tower in signal report")
    best, strongest = max(measured_dbm.items(), key=lambda x: x[1])
    if strongest < call_floor_dbm:
        return (CallState(state.serving, connected=False),
                Event("CALL DROPPED", state.serving, "-", None, "All towers below modeled coverage floor"))
    candidates = [(n, v) for n, v in measured_dbm.items() if n != state.serving]
    if not candidates:
        return CallState(state.serving), None
    target, power = max(candidates, key=lambda x: x[1])
    if power < min_target_dbm or power < measured_dbm[state.serving] + margin_db:
        return CallState(state.serving), None
    consecutive = state.candidate_count + 1 if state.candidate == target else 1
    if consecutive < time_to_trigger:
        return CallState(state.serving, target, consecutive), None
    if target in unavailable_targets:
        return (CallState(state.serving),
                Event("TARGET BLOCKED", state.serving, target, None, "Target cell has no available resources"))
    intra = bsc_lookup[state.serving] == bsc_lookup[target]
    return (CallState(target),
            Event("INTRA-BSC" if intra else "INTER-BSC", state.serving, target,
                  120 if intra else 240, "Hysteresis and trigger duration satisfied"))

def route(coverage_hole: bool = False, steps: int = 26) -> list[tuple[float, float]]:
    nodes = [(140.0, 230.0), (1440.0, 220.0), (1450.0, 1450.0)]
    if coverage_hole:
        nodes.append((10000.0, 10000.0))
    positions = []
    for a, b in zip(nodes[:-1], nodes[1:]):
        for i in range(steps):
            fraction = i / (steps - 1)
            positions.append((a[0] + (b[0] - a[0]) * fraction,
                              a[1] + (b[1] - a[1]) * fraction))
    return positions

def simulate_handover(
    seed: int = 42,
    noise_db: float = 1.0,
    margin_db: float = 3.0,
    time_to_trigger: int = 2,
    coverage_hole: bool = False,
    blocked: frozenset[str] = frozenset(),
) -> tuple[list[dict], list[dict]]:
    if noise_db < 0:
        raise ValueError("Noise must be nonnegative")
    rng = np.random.default_rng(seed)
    bsc_lookup = {t.name: t.bsc for t in TOWERS}
    state = CallState(TOWERS[0].name)
    trace, events = [], []
    for step, (x, y) in enumerate(route(coverage_hole)):
        levels = {t.name: expected_rssi(hypot(x - t.x, y - t.y)) +
                  (float(rng.normal(0, noise_db)) if noise_db else 0.0) for t in TOWERS}
        state, event = evaluate_report(
            state, levels, bsc_lookup, margin_db, time_to_trigger,
            unavailable_targets=blocked,
        )
        trace.append(dict(step=step, x_m=x, y_m=y, serving=state.serving,
                          connected=state.connected, **levels))
        if event:
            events.append(dict(step=step, event=event.event, source=event.source,
                               target=event.target, modeled_delay_ms=event.modeled_delay_ms,
                               reason=event.reason))
        if not state.connected:
            break
    return trace, events
