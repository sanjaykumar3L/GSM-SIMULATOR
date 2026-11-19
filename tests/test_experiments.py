import pandas as pd
import pytest

from gsm_sim.experiments import localization_trials, handover_trials

def test_reproducible_batch():
    a = localization_trials(trials=15, seed=99, noise_db=4)
    b = localization_trials(trials=15, seed=99, noise_db=4)
    pd.testing.assert_frame_equal(a, b)
    assert (a["cell_id_error_m"] >= 0).all()
    assert (a["trilateration_error_m"] >= 0).all()

def test_dead_zone_reported_in_handover_trials():
    trials = handover_trials(trials=5, seed=2, noise_db=0,
                             margin_db=3, coverage_hole=True)
    assert trials["dropped"].all()

def test_invalid_batch_sizes():
    with pytest.raises(ValueError):
        localization_trials(0, 42, 4)
    with pytest.raises(ValueError):
        handover_trials(0, 42, 4, 3)
