"""Streamlit user interface for the reproducible GSM-inspired engineering simulator."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from gsm_sim.security import authenticate, encrypt, decrypt
from gsm_sim.localization import TOWERS, locate
from gsm_sim.handover import simulate_handover
from gsm_sim.experiments import localization_trials, handover_trials

st.set_page_config(page_title="GSM Engineering Lab", page_icon="📡", layout="wide")
st.markdown("""
<style>
.block-container {max-width: 1250px; padding-top: 2rem;}
[data-testid="stMetric"] {padding: 14px 16px; border: 1px solid #7894ab50; border-radius: 12px;}
h1 {letter-spacing: -.035em;}
</style>""", unsafe_allow_html=True)

st.title("📡 GSM Security & Mobility Lab")
st.caption("A reproducible, synthetic GSM-inspired engineering simulation — not a live telecom network.")

with st.sidebar:
    st.header("Experiment setup")
    seed = int(st.number_input("Random seed", value=42, min_value=0, max_value=10000000))
    st.info("Repeat an experiment with identical settings and seed to reproduce the results.")
    st.warning("A3/A8 use educational HMAC substitutes. Encryption uses AES-GCM, NOT GSM A5. Handover delays are assumed, not measured.")
    st.divider()
    st.caption("Capstone · Security · Localization · Handover")

home, security, location, handover, validation = st.tabs([
    "🏠 Overview", "🔐 Authentication", "📍 Localization", "📶 Handover", "🧪 Validation"
])

with home:
    st.subheader("One platform. Three independently testable modules.")
    a, b, c = st.columns(3)
    a.metric("Virtual towers", len(TOWERS))
    b.metric("Virtual controllers", len({t.bsc for t in TOWERS}))
    c.metric("Live radio hardware", "Not required")
    st.markdown("""
**Security:** Independent SIM/network challenge responses, mismatch rejection, encrypted-message demonstration.

**Localization:** Cell-ID, GSM Timing Advance bins, and range-based trilateration with realistic-looking noise.

**Mobility:** Received-signal measurement reports, handover hysteresis, time-to-trigger, BSC transitions, blocked target cells, and coverage failure.
""")
    st.code("""Web dashboard
    └─ Python experiment engine
        ├─ Synthetic SIM & network → RAND / demo SRES / demo Kc
        ├─ Virtual BTS measurements → Cell-ID / TA / trilateration
        └─ Mobile route → signal reports → BSC decisions
                    ↓
             Validation & scenario reports""", language="text")
    st.caption("Reported results are calculated from explicit models and assumptions. They are not network-provider measurements.")

with security:
    st.subheader("Module 1 — Authentication & encryption")
    st.write("The network and SIM independently process a 128-bit challenge. Invalid credentials must fail.")
    choice = st.radio("Test subscriber", ["Matching secret", "Wrong secret"], horizontal=True)
    network_secret = bytes.fromhex("00112233445566778899aabbccddeeff")
    mismatched_secret = bytes.fromhex("ffeeddccbbaa99887766554433221100")
    if st.button("Run authentication", type="primary"):
        st.session_state.auth_result = authenticate(
            network_secret,
            network_secret if choice == "Matching secret" else mismatched_secret,
        )
        st.session_state.pop("cipher_demo", None)
    result = st.session_state.get("auth_result")
    if result is not None:
        if result.accepted:
            st.success("PASS — SIM response matches the expected network response.")
        else:
            st.error("REJECTED — SIM response does not match; key is not released.")
        a, b = st.columns(2)
        a.metric("Network SRES", result.network_sres.upper())
        b.metric("SIM SRES", result.sim_sres.upper())
        st.code("RAND: " + result.rand + "\nDEMO Kc: " + (result.kc or "NOT RELEASED"), language="text")
        if result.accepted and result.kc:
            st.markdown("#### Encryption demonstration")
            st.caption("AES-GCM demonstrates confidential and authenticated data exchange. This is NOT a GSM A5 implementation.")
            message = st.text_input("Plaintext", "Hello from the GSM simulator")
            if st.button("Encrypt and decrypt"):
                token = encrypt(message, result.kc)
                st.session_state.cipher_demo = (token, decrypt(token, result.kc))
            if "cipher_demo" in st.session_state:
                token, recovered = st.session_state.cipher_demo
                st.code(token, language="text")
                st.success("Decrypted: " + recovered)
    st.caption("Automated tests also reject altered ciphertext and invalid challenge lengths.")

with location:
    st.subheader("Module 2 — Mobile localization")
    st.write("A synthetic radio environment generates signal readings from a known position. The location estimator sees only measurements; evaluation compares its output with the withheld truth.")
    a, b, c = st.columns(3)
    x = float(a.slider("True X (m)", 0, 1700, 700, 25))
    y = float(b.slider("True Y (m)", 0, 1700, 820, 25))
    shadowing = float(c.slider("RSSI noise σ (dB)", 0.0, 12.0, 3.0, 0.5))
    if st.button("Estimate position", type="primary"):
        st.session_state.location_result = locate((x, y), seed, shadowing)
    r = st.session_state.get("location_result")
    if r:
        a, b, c = st.columns(3)
        a.metric("Cell-ID position error", f"{r.cell_id_error_m:.1f} m")
        b.metric("Trilateration error", f"{r.trilateration_error_m:.1f} m")
        c.metric("Serving-cell TA", f"{r.serving_ta} bins")
        figure = go.Figure()
        figure.add_trace(go.Scatter(x=[t.x for t in TOWERS], y=[t.y for t in TOWERS],
            mode="markers+text", text=[t.name for t in TOWERS], textposition="top center",
            name="Base stations", marker=dict(symbol="triangle-up", size=16)))
        figure.add_trace(go.Scatter(x=[r.truth[0]], y=[r.truth[1]],
            mode="markers", name="Ground truth (evaluator)",
            marker=dict(symbol="circle", size=16)))
        figure.add_trace(go.Scatter(x=[r.cell_id_estimate[0]], y=[r.cell_id_estimate[1]],
            mode="markers", name="Cell-ID estimate",
            marker=dict(symbol="square", size=16)))
        figure.add_trace(go.Scatter(x=[r.trilateration_estimate[0]], y=[r.trilateration_estimate[1]],
            mode="markers", name="Trilateration estimate",
            marker=dict(symbol="x", size=17)))
        figure.update_layout(height=470, title="Position estimates on a synthetic network",
            xaxis_title="X coordinate (m)", yaxis_title="Y coordinate (m)",
            legend=dict(orientation="h", y=-.24))
        figure.update_yaxes(scaleanchor="x", scaleratio=1)
        st.plotly_chart(figure, use_container_width=True)
        st.dataframe(pd.DataFrame([{
            "Tower": m.tower, "RSSI (dBm)": round(m.rssi_dbm, 2),
            "Estimated range (m)": round(m.estimated_range_m, 1),
            "Timing Advance": m.timing_advance,
        } for m in r.readings]), hide_index=True, use_container_width=True)
        st.caption("Timing Advance alone provides a coarse distance bin, not unique geographic coordinates.")

with handover:
    st.subheader("Module 3 — Mobility & GSM-inspired handover")
    st.write("Run a virtual call from BTS-A through BTS-B to BTS-C. Signal levels determine whether hysteresis and time-to-trigger conditions are met.")
    a, b, c = st.columns(3)
    noise = float(a.slider("Shadowing σ (dB)", 0.0, 8.0, 1.0, .5))
    margin = float(b.slider("Handover margin (dB)", 0.0, 12.0, 3.0, .5))
    trigger = int(c.slider("Trigger samples", 1, 10, 2))
    dead_zone = st.checkbox("Add a coverage dead zone")
    blocked = st.checkbox("Block BTS-B resources (failure scenario)")
    if st.button("Run call and handover", type="primary"):
        st.session_state.handover_result = simulate_handover(
            seed=seed, noise_db=noise, margin_db=margin,
            time_to_trigger=trigger, coverage_hole=dead_zone,
            blocked=frozenset({"BTS-B"}) if blocked else frozenset(),
        )
    r = st.session_state.get("handover_result")
    if r:
        trace, events = r
        data = pd.DataFrame(trace)
        st.line_chart(data.set_index("step")[[t.name for t in TOWERS]])
        transfers = [e for e in events if e["event"] in ("INTRA-BSC", "INTER-BSC")]
        drops = [e for e in events if e["event"] == "CALL DROPPED"]
        a, b, c = st.columns(3)
        a.metric("Successful simulated handovers", len(transfers))
        b.metric("Call dropped", "YES" if drops else "NO")
        c.metric("Modeled delay (sum)", f"{sum(e['modeled_delay_ms'] for e in transfers)} ms")
        st.markdown("#### Event and failure log")
        st.dataframe(
            pd.DataFrame(events) if events else pd.DataFrame([{"event": "No transfer reached the configured threshold"}]),
            hide_index=True, use_container_width=True,
        )
        st.download_button("Download measurement trace (CSV)",
            data=data.to_csv(index=False), file_name="gsm_handover_trace.csv", mime="text/csv")
        st.caption("120 ms intra-BSC / 240 ms inter-BSC are explicitly assumed simulation constants, NOT measured GSM latency.")

with validation:
    st.subheader("Reproducible scenario analysis")
    st.write("Run repeated, seeded trials instead of reporting only successful demonstrations.")
    a, b, c = st.columns(3)
    trial_count = int(a.slider("Number of trials", 10, 300, 80, 10))
    test_noise = float(b.slider("Experiment noise σ (dB)", 0.0, 12.0, 4.0, 0.5))
    test_margin = float(c.slider("Handover threshold (dB)", 1.0, 10.0, 3.0, 0.5))
    if st.button("Run reproducible experiments", type="primary"):
        st.session_state.batch_loc = localization_trials(trial_count, seed, test_noise)
        st.session_state.batch_ho = handover_trials(trial_count, seed, test_noise, test_margin, coverage_hole=True)
    loc_trials = st.session_state.get("batch_loc")
    ho_trials = st.session_state.get("batch_ho")
    if loc_trials is not None and ho_trials is not None:
        a, b, c = st.columns(3)
        a.metric("Mean Cell-ID error", f"{loc_trials['cell_id_error_m'].mean():.1f} m")
        b.metric("Mean trilateration error", f"{loc_trials['trilateration_error_m'].mean():.1f} m")
        c.metric("Coverage-hole drop rate", f"{100 * ho_trials['dropped'].mean():.1f}%")
        st.bar_chart(loc_trials[['cell_id_error_m', 'trilateration_error_m']])
        st.dataframe(loc_trials.describe().round(2), use_container_width=True)
        st.download_button("Export localization trials (CSV)",
            loc_trials.to_csv(index=False), "gsm_localization_trials.csv", "text/csv")
        st.download_button("Export handover trials (CSV)",
            ho_trials.to_csv(index=False), "gsm_handover_trials.csv", "text/csv")
    with st.expander("What has (and has not) been validated"):
        st.markdown("""
- Automated tests check good and bad credentials, encryption round-trips, ciphertext tampering, noise-free triangulation, noncollinear geometry, time-to-trigger, intra/inter-BSC transitions, and call drops.
- Model outputs are computed with known formulas and fixed random seeds, rather than hardcoded success messages.
- The reported time values are modeled delays rather than measured network latency.
- RSSI path loss and shadowing are simplified; accuracy and call-drop rates cannot be generalized to live mobile networks.
- Independent laboratory or field datasets are required before claiming real-world telecommunications validity.
""")
