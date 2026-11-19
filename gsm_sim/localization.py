"""Reproducible localization experiments with withheld truth and noisy RSSI."""
from __future__ import annotations

from dataclasses import dataclass
from math import hypot, log10
from typing import Sequence

import numpy as np
from scipy.optimize import least_squares

TA_METRES_PER_STEP = 550.0
REFERENCE_RSSI_DBM = -30.0
LOSS_EXPONENT = 2.2

@dataclass(frozen=True)
class Tower:
    name: str
    x: float
    y: float
    bsc: str

TOWERS = (
    Tower("BTS-A", 100.0, 200.0, "BSC-1"),
    Tower("BTS-B", 1450.0, 200.0, "BSC-1"),
    Tower("BTS-C", 1450.0, 1500.0, "BSC-2"),
    Tower("BTS-D", 100.0, 1500.0, "BSC-2"),
)

@dataclass(frozen=True)
class RadioReading:
    tower: str
    rssi_dbm: float
    estimated_range_m: float
    timing_advance: int

@dataclass(frozen=True)
class PositionResult:
    truth: tuple[float, float]
    cell_id_estimate: tuple[float, float]
    trilateration_estimate: tuple[float, float]
    cell_id_error_m: float
    trilateration_error_m: float
    serving_cell: str
    serving_ta: int
    serving_ta_range_m: float
    readings: tuple[RadioReading, ...]

def expected_rssi(distance_m: float) -> float:
    """Log-distance propagation model. One metre is the minimum modeled distance."""
    return REFERENCE_RSSI_DBM - 10 * LOSS_EXPONENT * log10(max(1.0, distance_m))

def rssi_range(rssi_dbm: float) -> float:
    return 10 ** ((REFERENCE_RSSI_DBM - rssi_dbm) / (10 * LOSS_EXPONENT))

def quantized_ta(distance_m: float) -> int:
    """Classic GSM-inspired approximate radial distance bin, never 2D position."""
    return min(63, max(0, int(round(distance_m / TA_METRES_PER_STEP))))

def simulate_radio(
    truth: tuple[float, float], seed: int, noise_db: float, towers: Sequence[Tower] = TOWERS
) -> tuple[RadioReading, ...]:
    if noise_db < 0:
        raise ValueError("Noise must be nonnegative")
    rng = np.random.default_rng(seed)
    readings = []
    for tower in towers:
        distance = hypot(truth[0] - tower.x, truth[1] - tower.y)
        observed = expected_rssi(distance) + (float(rng.normal(0, noise_db)) if noise_db else 0.0)
        readings.append(RadioReading(tower.name, observed, rssi_range(observed), quantized_ta(distance)))
    return tuple(readings)

def trilaterate(readings: Sequence[RadioReading], towers: Sequence[Tower] = TOWERS) -> tuple[float, float]:
    if len(readings) < 3:
        raise ValueError("Three or more cells are required for 2D estimation")
    tower_map = {t.name: t for t in towers}
    if any(r.tower not in tower_map for r in readings) or len({r.tower for r in readings}) != len(readings):
        raise ValueError("Readings must identify distinct known towers")
    points = np.array([(tower_map[r.tower].x, tower_map[r.tower].y) for r in readings], dtype=float)
    if np.linalg.matrix_rank(points[1:] - points[0]) < 2:
        raise ValueError("Tower geometry is collinear")
    ranges = np.array([r.estimated_range_m for r in readings], dtype=float)
    if not np.all(np.isfinite(ranges)) or np.any(ranges <= 0):
        raise ValueError("Invalid estimated ranges")
    result = least_squares(
        lambda p: np.linalg.norm(points - p, axis=1) - ranges,
        x0=points.mean(axis=0), max_nfev=350,
    )
    return float(result.x[0]), float(result.x[1])

def locate(
    truth: tuple[float, float], seed: int = 42, noise_db: float = 3.0,
    towers: Sequence[Tower] = TOWERS,
) -> PositionResult:
    # Only the synthetic measurement generator and evaluator access ground truth.
    readings = simulate_radio(truth, seed, noise_db, towers)
    serving = max(readings, key=lambda r: r.rssi_dbm)
    serving_tower = next(t for t in towers if t.name == serving.tower)
    cell_est = (serving_tower.x, serving_tower.y)
    multi_est = trilaterate(readings, towers)
    return PositionResult(
        truth, cell_est, multi_est,
        hypot(cell_est[0] - truth[0], cell_est[1] - truth[1]),
        hypot(multi_est[0] - truth[0], multi_est[1] - truth[1]),
        serving.tower, serving.timing_advance, serving.timing_advance * TA_METRES_PER_STEP,
        readings,
    )
