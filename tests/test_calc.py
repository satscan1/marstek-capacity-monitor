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
