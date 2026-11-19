from math import isclose

import pytest

from gsm_sim.localization import (
    TOWERS, Tower, expected_rssi, rssi_range, quantized_ta,
    locate, simulate_radio, trilaterate,
)

def test_no_noise_recovers_ground_truth():
    result = locate((650.0, 770.0), seed=42, noise_db=0)
    assert result.trilateration_error_m < .01
    assert result.cell_id_error_m >= 0

def test_seed_gives_reproducible_noisy_results():
    a = locate((600.0, 940.0), seed=88, noise_db=5)
    b = locate((600.0, 940.0), seed=88, noise_db=5)
    assert a == b

def test_distance_signal_transform_reversible():
    assert isclose(rssi_range(expected_rssi(750)), 750, abs_tol=1e-7)

def test_timing_advance_is_quantized_and_capped():
    assert quantized_ta(0) == 0
    assert quantized_ta(550) == 1
    assert quantized_ta(100000) == 63

def test_collinear_sites_not_accepted():
    towers = (Tower("X", 0, 0, "C"), Tower("Y", 300, 0, "C"), Tower("Z", 600, 0, "C"))
    readings = simulate_radio((100, 200), seed=1, noise_db=0, towers=towers)
    with pytest.raises(ValueError):
        trilaterate(readings, towers)

def test_insufficient_towers_not_accepted():
    readings = simulate_radio((450, 450), seed=1, noise_db=0)
    with pytest.raises(ValueError):
        trilaterate(readings[:2])
