"""Tests voor de rekenkern (geen Home Assistant nodig)."""

from datetime import date, datetime
import importlib.util
from pathlib import Path
import sys

import pytest

_spec = importlib.util.spec_from_file_location(
    "calc",
    Path(__file__).parents[1]
    / "custom_components/marstek_capacity_monitor/calc.py",
)
calc = importlib.util.module_from_spec(_spec)
sys.modules["calc"] = calc
_spec.loader.exec_module(calc)

T0 = datetime(2026, 10, 18, 8, 0).timestamp()


def simulate(tracker, soc_from, soc_to, kwh, t0, steps=None, invert=False):
    """Laat de SOC lineair lopen en het DC-vermogen zo dat er precies `kwh`
    door de cellen gaat. Geeft (records, eindtijd)."""
    delta = soc_to - soc_from
    steps = steps or int(abs(delta))
    dur_s = steps * 60.0
    power = (kwh * 3_600_000.0 / dur_s) * (1 if delta > 0 else -1)
    if invert:  # sensor that reports charging as negative
        power = -power
    out = []
    t = t0
    tracker.update_power(power, t)
    for i in range(1, steps + 1):
        t = t0 + i * 60.0
        tracker.tick(t)
        r = tracker.update_soc(soc_from + delta * i / steps, t)
        if r:
            out.append(r)
    tracker.update_power(0.0, t)
    return out, t


def test_usable_capacity_split():
    s = calc.BatterySpec()  # datasheet default: DoD 90 %
    assert s.nominal_kwh == 5.12
    assert round(s.usable_kwh, 2) == 4.61
    assert round(s.usable_band_pct) == 90
    own = calc.BatterySpec(reserve_kwh=0.61)  # 88 % usable band (reserve 0.61 kWh)
    assert round(own.usable_kwh, 2) == 4.51
    assert round(own.usable_band_pct) == 88


def test_full_discharge_gives_mt1_example():
    """MT1 18-10-2026: 4,42 kWh DC over 89 punten -> 4,37 kWh (97%)."""
    tr = calc.SwingTracker()
    tr.update_soc(100, T0)
    recs, t = simulate(tr, 100, 11, 4.42, T0)
    assert recs == []  # zwaai sluit pas bij terugloop van 3 punten
    recs, _ = simulate(tr, 11, 30, 1.0, t)
    assert len(recs) == 1
    r = recs[0]
    assert r["direction"] == "discharge"
    assert r["soc_start"] == 100 and r["soc_end"] == 11
    assert r["e_dc_kwh"] == pytest.approx(4.42, abs=0.01)
    assert calc.is_full_discharge(r)
    spec = calc.BatterySpec(reserve_kwh=0.61, purchase_date=date(2024, 2, 1))
    cap = calc.capacity_from_record(spec, r)
    assert cap == pytest.approx(4.37, abs=0.01)


def test_small_swing_not_recorded():
    tr = calc.SwingTracker()
    tr.update_soc(60, T0)
    recs, t = simulate(tr, 60, 50, 0.5, T0)
    recs2, _ = simulate(tr, 50, 70, 1.0, t)
    assert recs == [] and recs2 == []


def test_charge_swing_recorded_but_not_full_discharge():
    tr = calc.SwingTracker()
    tr.update_soc(20, T0)
    _, t = simulate(tr, 20, 90, 3.6, T0)
    recs, _ = simulate(tr, 90, 80, 0.5, t)
    assert len(recs) == 1
    assert recs[0]["direction"] == "charge"
    assert not calc.is_full_discharge(recs[0])


def test_data_gap_invalidates_swing():
    tr = calc.SwingTracker()
    tr.update_soc(100, T0)
    _, t = simulate(tr, 100, 50, 2.5, T0)
    t += 3600  # een uur geen vermogenswaarde (HA herstart)
    tr.update_power(-1000, t)
    _, t = simulate(tr, 50, 10, 2.0, t)
    recs, _ = simulate(tr, 10, 30, 1.0, t)
    assert len(recs) == 1
    assert recs[0]["valid"] is False
    assert not calc.is_full_discharge(recs[0])


def test_cycle_line_only():
    s = calc.BatterySpec(purchase_date=date(2024, 2, 1))
    assert calc.cycle_expected_pct(s, 6000) == pytest.approx(80)
    assert calc.cycle_expected_pct(s, 300) == pytest.approx(99)
    # no time line: age does not lower the expectation
    assert calc.expected_pct(s, date(2033, 1, 1), 300) == pytest.approx(99)
    assert s.warranty_end == date(2034, 2, 1)


def test_classify_colours():
    s = calc.BatterySpec()
    assert calc.classify(s, None, 99) == "no_measurement"
    assert calc.classify(s, 99.5, 99) == "good"
    assert calc.classify(s, 94.0, 99) == "good"  # within 5 points
    assert calc.classify(s, 93.9, 99) == "attention"
    assert calc.classify(s, 75.1, 99) == "attention"
    assert calc.classify(s, 75.0, 99) == "critical"  # 75 % and lower is red
    assert calc.classify(s, 60.0, 80) == "critical"


def test_evaluate_median_status_and_trend():
    spec = calc.BatterySpec(reserve_kwh=0.61, purchase_date=date(2024, 2, 1))
    now = datetime(2026, 10, 20, 12, 0)
    recs = []
    for i, (kwh, month) in enumerate([(4.42, 8), (4.30, 9), (4.40, 10), (4.10, 10)]):
        ts = datetime(2026, month, 5 + i, 18, 0).timestamp()
        recs.append(
            {
                "ts": ts,
                "direction": "discharge",
                "soc_start": 100,
                "soc_end": 12,
                "delta_soc": 88,
                "e_dc_kwh": kwh,
                "valid": True,
                "cumulative_discharge_kwh": 100.0 + i * 10,
            }
        )
    res = calc.evaluate(spec, recs, 1353.0, now)  # 1353 kWh / 4.51 = 300 cycles
    assert res["nominal_kwh"] == 5.12
    assert res["usable_kwh"] == 4.51
    # mediaan van de laatste 3 (4.30, 4.40, 4.10) = 4.30
    assert res["measured_kwh"] == pytest.approx(4.30, abs=0.01)
    assert res["measurement_count"] == 3
    assert res["status"] == "good"
    assert res["cycles"] == pytest.approx(300, abs=1)
    assert res["expected_pct"] == pytest.approx(99.0, abs=0.1)
    assert res["red_pct"] == 75
    assert res["margin_kwh"] == pytest.approx(-0.16, abs=0.01)  # slightly below, still green
    assert [m["month"] for m in res["trend"]] == ["2026-10", "2026-09", "2026-08"]
    assert res["trend"][0]["n"] == 2
    assert res["trend"][0]["status"] in ("good", "attention")
    assert res["warranty_end"] == date(2034, 2, 1)


def test_evaluate_without_measurement():
    spec = calc.BatterySpec(purchase_date=date(2025, 5, 1))
    res = calc.evaluate(spec, [], 0.0, datetime(2026, 10, 20))
    assert res["status"] == "no_measurement"
    assert res["measured_kwh"] is None
    assert res["expected_pct"] == pytest.approx(100.0)


def test_status_thresholds():
    spec = calc.BatterySpec(reserve_kwh=0.61)
    now = datetime(2026, 10, 20)
    def rec(kwh):
        return {"ts": now.timestamp() - 86400, "direction": "discharge",
                "soc_start": 99, "soc_end": 11, "delta_soc": 88,
                "e_dc_kwh": kwh, "valid": True}
    assert calc.evaluate(spec, [rec(4.40)], 0, now)["status"] == "good"
    assert calc.evaluate(spec, [rec(3.60)], 0, now)["status"] == "attention"
    assert calc.evaluate(spec, [rec(3.38)], 0, now)["status"] == "critical"


def test_auto_sign_detects_inverted_sensor():
    """A sensor that shows charging as negative is detected on the first
    swing and corrected; the measurement itself is still right."""
    tr = calc.SwingTracker(auto_sign=True)
    tr.update_soc(100, T0)
    _, t = simulate(tr, 100, 11, 4.42, T0, invert=True)
    recs, t = simulate(tr, 11, 40, 1.5, t, invert=True)
    assert len(recs) == 1
    r = recs[0]
    assert r["sign_corrected"] is True
    assert r["direction"] == "discharge"
    assert r["e_dc_kwh"] == pytest.approx(4.42, abs=0.01)
    assert tr.s["sign"] == -1 and tr.s["sign_confirmed"]
    assert tr.cumulative_discharge_kwh == pytest.approx(4.42, abs=0.01)
    # following swings are counted correctly without further flips
    recs, _ = simulate(tr, 40, 90, 2.5, t, invert=True)
    recs, _ = simulate(tr, 90, 70, 0.9, _, invert=True)
    assert recs[0]["direction"] == "charge"
    assert recs[0]["e_dc_kwh"] == pytest.approx(1.5 + 2.5, abs=0.02)
    assert "sign_corrected" not in recs[0]


def test_auto_sign_keeps_correct_sensor():
    tr = calc.SwingTracker(auto_sign=True)
    tr.update_soc(100, T0)
    _, t = simulate(tr, 100, 11, 4.42, T0)
    recs, _ = simulate(tr, 11, 40, 1.5, t)
    assert tr.s["sign"] == 1 and tr.s["sign_confirmed"]
    assert "sign_corrected" not in recs[0]


def test_fixed_sign_is_never_flipped():
    tr = calc.SwingTracker(auto_sign=False)
    tr.update_soc(100, T0)
    _, t = simulate(tr, 100, 11, 4.42, T0, invert=True)
    recs, _ = simulate(tr, 11, 40, 1.5, t, invert=True)
    assert tr.s["sign"] == 1
    assert recs[0]["valid"] is False  # no energy in the discharge bucket


def test_last_full_charge_and_discharge():
    spec = calc.BatterySpec(reserve_kwh=0.61)
    now = datetime(2026, 10, 20)
    t1 = datetime(2026, 10, 10, 18).timestamp()
    t2 = datetime(2026, 10, 12, 14).timestamp()
    recs = [
        {"ts": t1, "direction": "discharge", "soc_start": 100, "soc_end": 11, "delta_soc": 89, "e_dc_kwh": 4.42, "valid": True},
        {"ts": t2, "direction": "charge", "soc_start": 11, "soc_end": 100, "delta_soc": 89, "e_dc_kwh": 4.6, "valid": True},
        {"ts": t2 + 3600, "direction": "charge", "soc_start": 40, "soc_end": 100, "delta_soc": 60, "e_dc_kwh": 3.1, "valid": True},
    ]
    res = calc.evaluate(spec, recs, 0, now)
    assert res["last_full_discharge"].timestamp() == pytest.approx(t1)
    assert res["last_full_charge"].timestamp() == pytest.approx(t2)  # the 40 -> 100 charge is not full
    assert res["last_full_discharge"].tzinfo is not None
    empty = calc.evaluate(spec, [], 0, now)
    assert empty["last_full_discharge"] is None and empty["last_full_charge"] is None


def test_cell_tracker_rearms_below_90():
    from custom_components.marstek_capacity_monitor.calc import CellBalanceTracker

    t = CellBalanceTracker()
    assert t.update(97, 0, 3450, 3430, 0) is None  # rest starts
    rec = t.update(97, 0, 3450, 3430, 301)
    assert rec["spread_mv"] == 20
    assert t.update(97, 0, 3450, 3400, 1000) is None  # same charge: no second sample
    t.update(85, -800, 3300, 3290, 2000)  # discharged below 90 %: re-armed
    t.update(98, 10, 3460, 3440, 3000)
    assert t.update(98, 10, 3460, 3440, 3301)["spread_mv"] == 20


def test_to_mv_units():
    from custom_components.marstek_capacity_monitor.calc import to_mv

    assert to_mv(3.31, "V") == 3310
    assert to_mv(3310, "mV") == 3310
    assert to_mv(3.31, None) == 3310


def test_measurement_phase():
    from custom_components.marstek_capacity_monitor.calc import measurement_phase

    assert measurement_phase({"soc": 40})["phase"] == "waiting_full_charge"
    assert measurement_phase({"soc": 96})["phase"] == "ready"
    running = measurement_phase(
        {"soc": 60, "swing": {"direction": "discharge", "start": {"soc": 97}, "valid": True}}
    )
    assert running["phase"] == "full_discharge_running" and running["from_soc"] == 97


def test_interrupted_only_for_full_discharge():
    from custom_components.marstek_capacity_monitor.calc import measurement_phase

    # restart while idle at 63 %: nothing to report
    idle = measurement_phase({"soc": 63, "swing": {"direction": None, "start": {"soc": 63}, "valid": False, "reason": "restart"}})
    assert "interrupted" not in idle
    broken = measurement_phase({"soc": 50, "swing": {"direction": "discharge", "start": {"soc": 97}, "valid": False, "reason": "data_gap"}})
    assert broken["interrupted"] == "data_gap"


def test_prune_keeps_full_discharges_for_years():
    prune_records = calc.prune_records
    recs = []
    for i in range(4000):
        full = i % 10 == 0
        recs.append({
            "ts": i, "direction": "discharge", "valid": True,
            "soc_start": 98 if full else 80, "soc_end": 10 if full else 50,
        })
    out = prune_records(recs, max_other=500, max_full=3000)
    assert sum(1 for r in out if r["soc_start"] == 98) == 400  # all 400 full ones kept
    assert len(out) == 900
    assert [r["ts"] for r in out] == sorted(r["ts"] for r in out)


def _restart(tr, down_s, t):
    """Save/load like Home Assistant does, then start again `down_s` later."""
    tr2 = calc.SwingTracker(dict(tr.s))
    tr2.start_after_restart(t + down_s)
    return tr2


def test_short_restart_is_bridged():
    tr = calc.SwingTracker()
    tr.update_soc(100, T0)
    _, t = simulate(tr, 100, 50, 2.5, T0)
    tr.s["power_w"] = -3000.0  # still discharging when HA stops (simulate ends at 0 W)
    tr = _restart(tr, 60, t)
    _, t = simulate(tr, 50, 11, 1.95, t + 120)  # first new value 2 min after stop
    recs, _ = simulate(tr, 11, 30, 1.0, t)
    assert len(recs) == 1
    r = recs[0]
    assert r["valid"] is True and calc.is_full_discharge(r)
    assert r["bridged_s"] == 120
    # gap: average of 3000 W before and 3000 W after, for 120 s = 0.1 kWh
    assert r["e_dc_kwh"] == pytest.approx(2.5 + 0.1 + 1.95, abs=0.01)


def test_unavailable_first_then_value_is_bridged():
    tr = calc.SwingTracker()
    tr.update_soc(100, T0)
    _, t = simulate(tr, 100, 50, 2.5, T0)
    tr.s["power_w"] = -3000.0
    tr = _restart(tr, 30, t)
    tr.update_power(None, t + 40)  # ESPHome not connected yet
    tr.tick(t + 60)
    assert tr.s["bridge"] is not None
    _, t = simulate(tr, 50, 11, 1.95, t + 90)
    recs, _ = simulate(tr, 11, 30, 1.0, t)
    assert recs[0]["valid"] is True and recs[0]["bridged_s"] == 90


def test_long_restart_is_not_bridged():
    tr = calc.SwingTracker()
    tr.update_soc(100, T0)
    _, t = simulate(tr, 100, 50, 2.5, T0)
    tr.s["power_w"] = -3000.0
    tr = _restart(tr, 900, t)  # 15 minutes down
    _, t = simulate(tr, 50, 11, 1.95, t + 960)
    recs, _ = simulate(tr, 11, 30, 1.0, t)
    assert recs[0]["valid"] is False and recs[0]["reason"] == "restart"


def test_no_value_within_ten_minutes_invalidates():
    tr = calc.SwingTracker()
    tr.update_soc(100, T0)
    _, t = simulate(tr, 100, 50, 2.5, T0)
    tr.s["power_w"] = -3000.0
    tr = _restart(tr, 30, t)
    tr.tick(t + 700)  # still no power value
    assert tr.s["bridge"] is None
    assert tr.s["swing"]["valid"] is False and tr.s["swing"]["reason"] == "restart"


def test_restart_without_saved_power_is_not_bridged():
    tr = calc.SwingTracker()
    tr.update_soc(100, T0)
    _, t = simulate(tr, 100, 50, 2.5, T0)
    tr.s["power_ts"] = None
    tr = _restart(tr, 30, t)
    assert tr.s["swing"]["valid"] is False


def test_soc_before_power_after_restart_keeps_gap_energy():
    """After a restart ESPHome may send the SOC before the power: the held-back
    SOC is replayed once the gap is filled, so the record includes the gap."""
    tr = calc.SwingTracker()
    tr.update_soc(100, T0)
    _, t = simulate(tr, 100, 12, 4.4, T0)
    tr.s["power_w"] = -1000.0
    tr = _restart(tr, 30, t)
    assert tr.update_soc(11, t + 200) is None  # last SOC step happened while down
    assert tr.s["swing"]["extreme"]["soc"] == 12  # held back
    assert tr.update_power(0.0, t + 240) is None
    assert tr.s["swing"]["extreme"]["soc"] == 11
    recs, _ = simulate(tr, 11, 30, 1.0, t + 300)
    r = recs[0]
    assert r["valid"] and r["bridged_s"] == 240
    # gap: (1000 + 0) / 2 W for 240 s = 0.0333 kWh, included in the record
    assert r["e_dc_kwh"] == pytest.approx(4.4 + 0.0333, abs=0.002)


def test_short_unavailable_power_is_bridged():
    """Issue #1: power unavailable for 2 minutes mid-discharge, then back."""
    tr = calc.SwingTracker()
    tr.update_soc(100, T0)
    _, t = simulate(tr, 100, 50, 2.5, T0)
    tr.update_power(-3000.0, t)
    tr.update_power(None, t + 30)  # unavailable
    tr.tick(t + 90)
    _, t2 = simulate(tr, 50, 11, 1.95, t + 150)  # back after 2 minutes
    recs, _ = simulate(tr, 11, 30, 1.0, t2)
    r = recs[0]
    assert r["valid"] and r["bridged_s"] == 120
    # 30 s before the outage + 120 s bridged at 3000 W = 0.125 kWh
    assert r["e_dc_kwh"] == pytest.approx(2.5 + 0.125 + 1.95, abs=0.01)


def test_long_unavailable_power_invalidates_swing():
    """Issue #1: power unavailable for 10 minutes: the energy is unknown, do not count."""
    tr = calc.SwingTracker()
    tr.update_soc(100, T0)
    _, t = simulate(tr, 100, 50, 2.5, T0)
    tr.update_power(-3000.0, t)
    tr.update_power(None, t + 30)
    for k in range(1, 11):
        tr.tick(t + 30 + 60 * k)
    _, t2 = simulate(tr, 50, 11, 1.95, t + 660)
    recs, _ = simulate(tr, 11, 30, 1.0, t2)
    assert recs[0]["valid"] is False and recs[0]["reason"] == "data_gap"


def _history(soc_from, soc_to, kwh, t0, idle_before_s=0, freeze_at=None):
    """Recorded events of a linear swing, as the recorder stores them (changes only)."""
    ev = [(t0, "s", float(soc_from)), (t0, "p", 0.0)]
    t0 += idle_before_s
    delta = soc_to - soc_from
    steps = int(abs(delta))
    power = (kwh * 3_600_000.0 / (steps * 60.0)) * (1 if delta > 0 else -1)
    for i in range(1, steps + 1):
        t = t0 + i * 60.0
        if freeze_at is not None and freeze_at[0] <= i < freeze_at[1]:
            continue  # nothing recorded (Home Assistant was off)
        ev.append((t - 59, "p", power + (i % 2)))  # measured power wobbles a little
        ev.append((t, "s", soc_from + delta * i / steps))
    ev.append((t + 1, "p", 0.0))
    return ev, t + 1


def test_history_replay_finds_full_discharge():
    ev, t = _history(100, 11, 4.42, T0, idle_before_s=4 * 3600)  # full and idle for 4 h first
    ev2, _ = _history(11, 30, 1.0, t)
    recs = calc.replay_history(calc.SwingTracker(), ev + ev2)
    full = [r for r in recs if calc.is_full_discharge(r)]
    assert len(full) == 1
    assert full[0]["source"] == "history"
    assert "cumulative_discharge_kwh" not in full[0]
    assert full[0]["e_dc_kwh"] == pytest.approx(4.42, abs=0.03)


def test_history_frozen_power_while_discharging_does_not_count():
    """Nothing recorded for 10 minutes while discharging: Home Assistant was off."""
    ev, t = _history(100, 11, 4.42, T0, freeze_at=(30, 41))
    ev2, _ = _history(11, 30, 1.0, t)
    recs = calc.replay_history(calc.SwingTracker(), ev + ev2)
    full = [r for r in recs if calc.is_full_discharge(r)]
    assert full == []


def test_history_idle_then_ha_off_does_not_count():
    """Idle at 100 %, then Home Assistant off for 3 hours while the battery
    discharged to 60 %: the quiet time must not count as 0 kWh."""
    ev = [(T0, "s", 100.0), (T0, "p", 0.0)]
    t = T0 + 3 * 3600  # nothing recorded for 3 hours
    ev2, t2 = _history(60, 11, 2.2, t)
    ev3, _ = _history(11, 30, 1.0, t2)
    recs = calc.replay_history(calc.SwingTracker(), ev + ev2 + ev3)
    assert [r for r in recs if calc.is_full_discharge(r) and r["valid"]] == []


def test_adopt_sign_from_history():
    hist = calc.SwingTracker()
    hist.update_soc(100, T0)
    recs, t = simulate(hist, 100, 11, 4.42, T0, invert=True)  # sensor shows charging as negative
    simulate(hist, 11, 40, 1.0, t, invert=True)
    assert hist.s["sign_confirmed"] and hist.s["sign"] == -1
    live = calc.SwingTracker()
    live.update_power(500.0, T0)  # raw value from the same sensor (discharging)
    assert live.adopt_sign(hist) is True
    assert live.s["sign"] == -1 and live.s["power_w"] == -500.0


def test_edge_ratio_normal_discharge_keeps_pace():
    """MT1 22-10-2026: evenveel energie per procent van boven tot onder."""
    tr = calc.SwingTracker()
    tr.update_soc(100, T0)
    _, t = simulate(tr, 100, 11, 4.37, T0)
    recs, _ = simulate(tr, 11, 30, 1.0, t)
    assert recs[0]["edge_ratio"] == pytest.approx(1.0, abs=0.05)


def test_edge_ratio_soc_stands_still_at_the_bottom():
    """MT2 22-10-2026: midden gelijk aan MT1, maar van 12 naar 11 % kwam er
    nog ~0,22 kWh uit (5 procent aan energie voor 1 punt) -> meting te hoog."""
    tr = calc.SwingTracker()
    tr.update_soc(99, T0)
    _, t = simulate(tr, 99, 12, 87 * 0.0491, T0)
    _, t = simulate(tr, 12, 11, 0.26, t)  # SOC hangt onderin
    recs, _ = simulate(tr, 11, 30, 1.0, t)
    r = recs[0]
    assert r["soc_start"] == 99 and r["soc_end"] == 11
    assert r["edge_ratio"] >= calc.EDGE_RATIO
    spec = calc.BatterySpec(reserve_kwh=0.61)
    assert calc.capacity_from_record(spec, r) / spec.usable_kwh > 1.0  # boven 100 %
    rel = calc.reliability(r, [], None)
    assert not rel["reliable"] and rel["why"] == "soc_edge"


def test_edge_ratio_unknown_for_old_swings():
    """Zwaaien uit een eerdere versie (zonder stappen): geen oordeel."""
    assert calc.edge_ratio(None, "discharge") is None
    assert calc.edge_ratio([[100, 0, 0], [99, 0, 0.05]], "discharge") is None


def test_about_half_asks_to_check_the_model():
    """A Venus C (2.56 kWh) set up as a Venus E (5.12 kWh) measures about 50 %:
    ask about the model instead of a red "report to Marstek"."""
    spec = calc.BatterySpec()  # Venus E: 5.12 kWh, 0.51 reserve
    now = datetime(2026, 10, 20)
    def rec(kwh):
        return {"ts": now.timestamp() - 86400, "direction": "discharge",
                "soc_start": 100, "soc_end": 10, "delta_soc": 90,
                "e_dc_kwh": kwh, "valid": True}
    # 2.30 kWh over 90 SOC points on a Venus E = 50 % of new
    assert calc.evaluate(spec, [rec(2.30)], 0, now)["status"] == "check_model"
    assert calc.evaluate(spec, [rec(1.50)], 0, now)["status"] == "critical"
    assert calc.evaluate(spec, [rec(3.30)], 0, now)["status"] == "critical"
    # The same measurement with the Venus C preset is a healthy battery
    venus_c = calc.BatterySpec(nominal_kwh=2.56, reserve_kwh=0.256)
    assert calc.evaluate(venus_c, [rec(2.30)], 0, now)["status"] == "good"
