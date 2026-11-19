"""Reproducible batch experiments, with no cherry-picking of successful trials."""
from __future__ import annotations

import numpy as np
import pandas as pd

from gsm_sim.handover import simulate_handover
from gsm_sim.localization import locate

def localization_trials(trials: int, seed: int, noise_db: float) -> pd.DataFrame:
    if not (1 <= trials <= 2000):
        raise ValueError("Number of trials must be in 1..2000")
    rng = np.random.default_rng(seed)
    records = []
    for index in range(trials):
        truth = (float(rng.uniform(150, 1400)), float(rng.uniform(250, 1450)))
        result = locate(truth, seed=seed + index + 1, noise_db=noise_db)
        records.append({"trial": index + 1, "true_x_m": round(truth[0], 2),
                        "true_y_m": round(truth[1], 2), "cell_id_error_m": result.cell_id_error_m,
                        "trilateration_error_m": result.trilateration_error_m})
    return pd.DataFrame(records)

def handover_trials(trials: int, seed: int, noise_db: float, margin_db: float,
                    coverage_hole: bool = False) -> pd.DataFrame:
    if not (1 <= trials <= 2000):
        raise ValueError("Number of trials must be in 1..2000")
    records = []
    for index in range(trials):
        _, events = simulate_handover(seed + index, noise_db, margin_db,
                                      coverage_hole=coverage_hole)
        transfers = [e for e in events if e["event"] in ("INTRA-BSC", "INTER-BSC")]
        drops = [e for e in events if e["event"] == "CALL DROPPED"]
        records.append({"trial": index + 1, "handovers": len(transfers),
                        "dropped": bool(drops),
                        "modeled_delay_ms": sum(e["modeled_delay_ms"] for e in transfers)})
    return pd.DataFrame(records)
