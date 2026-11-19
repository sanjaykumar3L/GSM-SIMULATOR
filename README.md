# 📡 GSM Security & Mobility Engineering Simulator

A browser-based educational engineering simulation with **three modules**: synthetic GSM-style challenge-response authentication, position estimation from simulated BTS measurements, and signal-driven handover decisions.

**Important:** No mobile network or radio hardware is required. All SIMs, base stations and RF measurements are synthetic. Security uses **HMAC-based stand-ins for A3/A8** and an **AES-GCM demonstration, NOT GSM A5**. Handover delays are explicit model assumptions (120 ms and 240 ms), not measurements from an operator.

## Features

| Module | Demonstration | Failure / validation |
|---|---|---|
| Authentication | RAND, simulated SRES, simulated Kc, AES-GCM round-trip | Incorrect subscriber key and tampered ciphertext |
| Localization | Cell-ID, quantized TA and RSSI-based multilateration | Position estimation error with seeded shadowing |
| Handover | BTS/BSC transfers using measured-signal model, margin and trigger | Blocked target, coverage loss, rejected transfer |
| Batch experiments | Repeatable trials and downloadable CSVs | Mean errors, call drops, and model-dependent metrics |

### Quick start

Use **Python 3.11+**. Run in a terminal at repository root:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local URL printed by Streamlit, usually http://localhost:8501.

### Run verification suite

```bash
python -m pytest -q
```

GitHub Actions runs compilation and automated tests when code is pushed. A green CI run indicates tests passed under the chosen model; it is not proof of real-world GSM fidelity.

## Files

```
app.py                       Streamlit dashboard
gsm_sim/security.py          Independent challenge-response + demo encryption
gsm_sim/localization.py      RSSI environment, TA, Cell-ID and trilateration
gsm_sim/handover.py          Handover state machine and synthetic route
gsm_sim/experiments.py       Reproducible batches and summary data
tests/                       Automated correctness and failure scenarios
.github/workflows/tests.yml  CI verification
render.yaml                  Optional Render deployment definition
```

## Deploy to Render

This is a single Streamlit web service. When using Render, choose a Python service with GitHub repo `sanjaykumar3L/GSM-SIMULATOR`:

- Build: `pip install -r requirements.txt`
- Start: `streamlit run app.py --server.address 0.0.0.0 --server.port $PORT --server.headless true`
- Health check: `/_stcore/health`
- Free instance tier if offered and sufficient.

The supplied `render.yaml` can also be used for a Render Blueprint.

## Engineering method and limitations

1. **Truth is withheld from algorithms.** Localization measurements are generated using a known position and a log-distance path-loss model plus seeded Gaussian noise. The estimator only uses the readings and tower positions. A separate evaluator computes distance to truth.
2. **Authentication can fail.** Network and SIM compute their SRES independently, then compare in constant time. Incorrect keys are rejected.
3. **Handover can fail.** A report-based state machine checks target strength, hysteresis, minimum quality, time-to-trigger, coverage loss and resource unavailability.
4. **Reproducibility.** Controlled seeds and scenarios let another person repeat the results.
5. **Tests are necessary, not sufficient.** This does not implement actual GSM A3/A8/A5, full radio-resource signaling, licensed RF transmitters, real SIMs or live carrier behavior. Positioning, handover delays and signal noise are simplified. Comparison to independently measured data or GSM-capable reference equipment would be future validation work.

No real subscriber data, proprietary secrets, telecom interception, or licensed radio operation is used.
