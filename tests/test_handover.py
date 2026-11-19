from gsm_sim.handover import CallState, evaluate_report, simulate_handover

BC = {"BTS-A":"BSC-1", "BTS-B":"BSC-1", "BTS-C":"BSC-2"}

def test_two_reports_required_before_handover():
    first, event = evaluate_report(
        CallState("BTS-A"), {"BTS-A": -96, "BTS-B": -84, "BTS-C": -109},
        BC, time_to_trigger=2,
    )
    assert first.serving == "BTS-A" and first.candidate == "BTS-B"
    assert event is None
    second, event = evaluate_report(
        first, {"BTS-A": -96, "BTS-B": -84, "BTS-C": -109},
        BC, time_to_trigger=2,
    )
    assert second.serving == "BTS-B"
    assert event.event == "INTRA-BSC" and event.modeled_delay_ms == 120

def test_inter_bsc_transition():
    state, event = evaluate_report(
        CallState("BTS-B"), {"BTS-A": -108, "BTS-B": -95, "BTS-C": -80},
        BC, time_to_trigger=1,
    )
    assert state.serving == "BTS-C"
    assert event.event == "INTER-BSC" and event.modeled_delay_ms == 240

def test_hysteresis_prevents_chattering():
    state, event = evaluate_report(
        CallState("BTS-A"), {"BTS-A": -93, "BTS-B": -92, "BTS-C": -110},
        BC, margin_db=3, time_to_trigger=1,
    )
    assert state.serving == "BTS-A" and event is None

def test_coverage_hole_drops_call():
    state, event = evaluate_report(
        CallState("BTS-A"), {"BTS-A": -120, "BTS-B": -119, "BTS-C": -118},
        BC,
    )
    assert not state.connected
    assert event.event == "CALL DROPPED"

def test_blocked_target_does_not_connect():
    state, event = evaluate_report(
        CallState("BTS-A"), {"BTS-A": -99, "BTS-B": -80, "BTS-C": -110},
        BC, time_to_trigger=1, unavailable_targets=frozenset({"BTS-B"}),
    )
    assert state.serving == "BTS-A"
    assert event.event == "TARGET BLOCKED"

def test_route_has_intra_and_inter_bsc_events():
    trace, events = simulate_handover(noise_db=0, margin_db=3, seed=42)
    assert len(trace) > 20
    types = [e["event"] for e in events]
    assert "INTRA-BSC" in types
    assert "INTER-BSC" in types

def test_dead_zone_route_has_call_drop():
    trace, events = simulate_handover(noise_db=0, coverage_hole=True)
    assert any(e["event"] == "CALL DROPPED" for e in events)
    assert trace[-1]["connected"] is False
