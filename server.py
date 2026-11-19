"""Single-service API for the SignalCore GSM engineering simulation dashboard.

All radio and subscriber inputs are synthetic. Educational GSM-like algorithms
are not a substitute for real GSM A3/A8/A5 or radio network measurements.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from gsm_sim.security import authenticate, encrypt, decrypt
from gsm_sim.localization import TOWERS, locate
from gsm_sim.handover import simulate_handover
from gsm_sim.experiments import localization_trials, handover_trials

ROOT = Path(__file__).resolve().parent
app = FastAPI(title="SignalCore GSM Simulation API", version="2.0.0")
app.mount("/static", StaticFiles(directory=str(ROOT / "web")), name="static")

# Deliberately public, synthetic demonstration credentials; never use for
# subscriber data, production authentication or commercial encryption.
DEMO_NETWORK_SECRET = bytes.fromhex("00112233445566778899aabbccddeeff")
DEMO_WRONG_SECRET = bytes.fromhex("ffeeddccbbaa99887766554433221100")


class AuthRequest(BaseModel):
    scenario: str = Field(default="valid", pattern="^(valid|invalid)$")


class EncryptRequest(BaseModel):
    message: str = Field(default="SignalCore demonstration", max_length=500)


class LocateRequest(BaseModel):
    x: float = Field(default=620, ge=0, le=1800)
    y: float = Field(default=780, ge=0, le=1800)
    noise_db: float = Field(default=3.0, ge=0, le=12)
    seed: int = Field(default=42, ge=0, le=10000000)


class HandoverRequest(BaseModel):
    noise_db: float = Field(default=1.0, ge=0, le=8)
    margin_db: float = Field(default=3.0, ge=0, le=12)
    time_to_trigger: int = Field(default=2, ge=1, le=10)
    coverage_hole: bool = False
    block_bts_b: bool = False
    seed: int = Field(default=42, ge=0, le=10000000)


class BatchRequest(BaseModel):
    trials: int = Field(default=40, ge=5, le=200)
    noise_db: float = Field(default=3.0, ge=0, le=12)
    margin_db: float = Field(default=3.0, ge=0, le=12)
    seed: int = Field(default=42, ge=0, le=10000000)


@app.get("/")
def index():
    return FileResponse(str(ROOT / "web" / "index.html"))


@app.get("/api/health")
def health():
    return {"status": "ok", "mode": "synthetic", "engine": "Python", "version": "2.0.0"}


@app.get("/api/overview")
def overview():
    return {
        "towers": [
            {"id": t.name, "x": t.x, "y": t.y, "bsc": t.bsc}
            for t in TOWERS
        ],
        "tower_count": len(TOWERS),
        "controller_count": len(set(t.bsc for t in TOWERS)),
        "modules": ["Authentication", "Localization", "Handover"],
        "mode": "SYNTHETIC LAB",
        "notes": [
            "No real RF transmissions or commercial SIM credentials",
            "Independent acceptance, range and mobility computations",
            "Explicit assumptions, seeded measurements and negative tests",
        ],
    }


@app.post("/api/authenticate")
def do_authentication(request: AuthRequest):
    result = authenticate(DEMO_NETWORK_SECRET,
        DEMO_NETWORK_SECRET if request.scenario == "valid" else DEMO_WRONG_SECRET)
    return {
        "accepted": result.accepted,
        "rand": result.rand,
        "network_sres": result.network_sres,
        "sim_sres": result.sim_sres,
        "kc": result.kc,
        "steps": [
            {"name": "RAND challenge", "state": "complete", "detail": "128-bit synthetic challenge issued"},
            {"name": "A3-like response", "state": "complete", "detail": "Both parties compute separate HMAC-derived responses"},
            {"name": "Network validation", "state": "passed" if result.accepted else "failed",
             "detail": "Response accepted" if result.accepted else "Mismatch detected; access denied"},
            {"name": "A8-like key derivation", "state": "passed" if result.accepted else "blocked",
             "detail": "64-bit demo Kc released" if result.accepted else "Key withheld on failure"},
        ],
        "disclaimer": "HMAC substitutes are not real GSM A3/A8 implementations.",
    }


@app.post("/api/encryption")
def encryption_demo(request: EncryptRequest):
    """AES-GCM educational demonstration, explicitly not GSM A5."""
    result = authenticate(DEMO_NETWORK_SECRET, DEMO_NETWORK_SECRET)
    if not result.kc:
        raise RuntimeError("Unexpected synthetic authentication failure")
    ciphertext = encrypt(request.message, result.kc)
    return {
        "plaintext": request.message,
        "ciphertext": ciphertext,
        "recovered": decrypt(ciphertext, result.kc),
        "algorithm": "AES-256-GCM demonstration (not GSM A5)",
    }


@app.post("/api/localization")
def localization(request: LocateRequest):
    result = locate((request.x, request.y), seed=request.seed, noise_db=request.noise_db)
    return {
        "truth": {"x": result.truth[0], "y": result.truth[1]},
        "cell_id": {
            "x": result.cell_id_estimate[0], "y": result.cell_id_estimate[1],
            "error_m": round(result.cell_id_error_m, 3),
        },
        "trilateration": {
            "x": result.trilateration_estimate[0], "y": result.trilateration_estimate[1],
            "error_m": round(result.trilateration_error_m, 3),
        },
        "serving_cell": result.serving_cell,
        "serving_ta": result.serving_ta,
        "ta_range_m": result.serving_ta_range_m,
        "measurements": [
            {"tower": m.tower, "rssi_dbm": round(m.rssi_dbm, 2),
             "range_m": round(m.estimated_range_m, 2),
             "ta": m.timing_advance} for m in result.readings
        ],
        "notes": "The estimator receives RSSI measurements only. Truth is used afterward to score error.",
    }


@app.post("/api/handover")
def handover(request: HandoverRequest):
    trace, events = simulate_handover(
        seed=request.seed, noise_db=request.noise_db,
        margin_db=request.margin_db, time_to_trigger=request.time_to_trigger,
        coverage_hole=request.coverage_hole,
        blocked=frozenset({"BTS-B"}) if request.block_bts_b else frozenset(),
    )
    transfers = [e for e in events if e["event"] in ("INTRA-BSC", "INTER-BSC")]
    drops = [e for e in events if e["event"] == "CALL DROPPED"]
    return {
        "trace": trace,
        "events": events,
        "metrics": {
            "handover_count": len(transfers),
            "intra_count": sum(e["event"] == "INTRA-BSC" for e in transfers),
            "inter_count": sum(e["event"] == "INTER-BSC" for e in transfers),
            "call_dropped": len(drops) > 0,
            "modeled_delay_ms": sum(e["modeled_delay_ms"] for e in transfers),
            "samples": len(trace),
        },
        "note": "Handover delays of 120 and 240 ms are model assumptions, not observed latency.",
    }


@app.post("/api/experiments")
def experiments(request: BatchRequest):
    loc = localization_trials(request.trials, request.seed, request.noise_db)
    ho = handover_trials(request.trials, request.seed,
                         request.noise_db, request.margin_db, coverage_hole=True)
    return {
        "trials": request.trials,
        "seed": request.seed,
        "localization": loc.round(3).to_dict(orient="records"),
        "handover": ho.to_dict(orient="records"),
        "summary": {
            "mean_cell_id_error_m": round(float(loc["cell_id_error_m"].mean()), 2),
            "mean_trilateration_error_m": round(float(loc["trilateration_error_m"].mean()), 2),
            "median_trilateration_error_m": round(float(loc["trilateration_error_m"].median()), 2),
            "mean_handover_count": round(float(ho["handovers"].mean()), 2),
            "coverage_hole_drop_rate_pct": round(float(100 * ho["dropped"].mean()), 1),
        },
        "notes": "Synthetic seeded experiments; none of the reported values are carrier field measurements.",
    }
