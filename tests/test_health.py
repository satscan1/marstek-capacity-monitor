"""SOC drift and cell calibration (0.5): events, data filter and the ladder."""

from datetime import datetime, timedelta
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "health",
    Path(__file__).resolve().parent.parent
    / "custom_components"
    / "marstek_capacity_monitor"
    / "health.py",
)
health = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(health)

UNIT = 0.0512  # kWh per SOC point (5.12 kWh)
T0 = datetime(2026, 1, 5, 8, 0).timestamp()


class Battery:
    """Feeds a SocHealthTracker like the monitor does, with its own energy count."""

    def __init__(self):
        self.h = health.SocHealthTracker(unit_kwh=UNIT)
        self.ec = 0.0
        self.ed = 0.0
        self.t = T0
        self.events = []

    def power(self, w, dt=0, **kw):
        self.t += dt
        self.events += self.h.on_power(w, self.t, **kw)

    def soc(self, soc, charged_pts=0.0, discharged_pts=0.0, dt=60, **kw):
        self.t += dt
        self.ec += charged_pts * UNIT
        self.ed += discharged_pts * UNIT
        self.events += self.h.on_soc(soc, self.ec, self.ed, self.t, **kw)

    def tick(self, dt=60):
        self.t += dt
        self.events += self.h.tick(self.t)

    def types(self):
        return [e["type"] for e in self.events]


def test_calibration_point_after_ten_minutes_at_100_and_no_charging():
    b = Battery()
    b.power(1500)
    b.soc(99, 1)
    b.soc(100, 0.8)
    b.power(10)
    b.tick(300)
    assert "top" not in b.types()
    b.tick(301)
    assert b.types().count("top") == 1
    b.tick(3600)
    assert b.types().count("top") == 1  # once per stay at 100 %


def test_extra_charge_at_99_is_measured():
    b = Battery()
    b.power(2000)
    b.soc(99, 1)
    for _ in range(12):
        b.power(1900 + _, dt=240)  # power keeps coming in every few minutes
    b.soc(100, 19.6, dt=10)  # MT1, 7 Jan: about 20 points more while it said 99 %
    b99 = [e for e in b.events if e["type"] == "b99"]
    assert b99 and b99[0]["value"] == 19.6


def test_jump_not_explained_by_energy():
    b = Battery()
    b.power(2200)
    b.soc(57, 1)
    b.soc(91, 0.5, dt=60)  # 34 points in a minute, half a point of energy
    jumps = [e for e in b.events if e["type"] == "jump"]
    assert jumps and jumps[0]["value"] == 34


def test_normal_steps_are_not_jumps():
    b = Battery()
    b.power(2000)
    for s in range(20, 60, 5):
        b.soc(s, 5, dt=300)  # 5 points of energy per 5 points of SOC
    assert "jump" not in b.types()


def test_power_gap_hides_the_jump():
    b = Battery()
    b.power(2000)
    b.soc(50, 1)
    b.tick(600)  # 10 minutes without a power value while charging
    b.soc(96, 3, dt=60)
    assert "jump" not in b.types()


def test_zero_glitch_and_restart_are_ignored():
    b = Battery()
    b.power(-500)
    b.soc(65, discharged_pts=1)
    b.soc(0, dt=30)  # MT1, 5 May: briefly 0 %
    b.soc(65, dt=30)
    assert "jump" not in b.types()
    b.h.after_restart()
    b.power(-500)
    b.soc(40, discharged_pts=1)
    assert "jump" not in b.types()


def test_hanging_at_100_while_discharging():
    b = Battery()
    b.power(1000)
    b.soc(100, 1)
    b.power(-800)
    for _ in range(6):
        b.power(-800 - _, dt=290)
    b.soc(99, discharged_pts=4.2, dt=10)
    hang = [e for e in b.events if e["type"] == "hang"]
    assert hang and hang[0]["value"] == 4.2


def test_cycle_and_rest_at_full():
    b = Battery()
    b.power(-1000)
    b.soc(12, discharged_pts=1)
    b.power(2000)
    b.soc(99, 87, dt=3 * 3600)
    b.soc(100, 1)
    b.power(0)
    for _ in range(9 * 60):
        b.tick(60)  # 9 hours full, at rest (UPS mode)
    assert "cycle" in b.types()
    assert b.h.rest_hours_now(b.t) >= 8.9
    b.power(-1500)
    b.tick(400)  # rest ends after a 5 min break
    rest = [e for e in b.events if e["type"] == "rest"]
    assert rest and rest[0]["value"] >= 8.9


def _occ(day_offsets, size=8.0):
    """Occurrences as jump events on the given days after T0."""
    return [{"ts": T0 + d * 86400, "type": "jump", "value": size} for d in day_offsets]


def _alive(days):
    return [(datetime.fromtimestamp(T0) + timedelta(days=d)).strftime("%Y-%m-%d") for d in days]


def _some_full(days):
    """Full on every third day: fewer than 7 of 14, and never 14 days without."""
    return _alive([d for d in days if d % 3 == 0])


def test_ladder_one_two_three():
    alive = _alive(range(-20, 60))
    full = _some_full(range(-20, 60))
    now = T0 + 41 * 86400
    r1 = health.evaluate_soc(_occ([0]), full, alive, T0 + 86400)
    assert r1["level"] == "ok" and r1["count"] == 1
    r2 = health.evaluate_soc(_occ([0, 20]), full, alive, now)
    assert r2["level"] == "letop"
    r3 = health.evaluate_soc(_occ([0, 20, 40]), full, alive, now)
    assert r3["level"] == "advies" and r3["since"] == T0 + 40 * 86400


def test_ladder_30_vs_45_days_like_mt1():
    # MT1 winter: 31 Dec, 7 Jan, 5 Feb, 15 Feb -> letop on 7 Jan, advice on 5 Feb
    alive, full = _alive(range(-10, 60)), _some_full(range(-10, 60))
    r = health.evaluate_soc(_occ([0, 7, 36, 46]), full, alive, T0 + 47 * 86400)
    assert r["level"] == "advies" and r["since"] == T0 + 36 * 86400
    # with 30 days instead of 45 it would only have been "let op"
    old = health.LADDER_DAYS
    try:
        health.LADDER_DAYS = 30
        r30 = health.evaluate_soc(_occ([0, 7, 36, 46]), full, alive, T0 + 47 * 86400)
    finally:
        health.LADDER_DAYS = old
    assert r30["level"] == "letop"


def test_full_battery_behaviour_does_not_count():
    # MT2: full almost every day, still 6-8 points off now and then
    days = list(range(-20, 40))
    full = _alive(days)
    r = health.evaluate_soc(_occ([0, 10, 20, 30]), full, full, T0 + 31 * 86400)
    assert r["level"] == "ok"


def test_advice_carried_out_clears_and_45_days_quiet_clears():
    alive = _alive(range(-20, 120))
    full = _some_full(range(-20, 120))
    ev = _occ([0, 5, 10])
    cycle = lambda d: {"ts": T0 + d * 86400, "type": "cycle", "value": 11}  # noqa: E731
    assert health.evaluate_soc(ev + [cycle(12)], full, alive, T0 + 13 * 86400)["level"] == "advies"
    assert health.evaluate_soc(ev + [cycle(12), cycle(13)], full, alive, T0 + 14 * 86400)["level"] == "ok"
    assert health.evaluate_soc(ev, full, alive, T0 + 56 * 86400)["level"] == "ok"


def test_jumps_of_two_batteries_at_the_same_time_are_data():
    alive, full = _alive(range(-20, 60)), _some_full(range(-20, 60))
    ev = _occ([0, 10, 20])
    other = [e["ts"] + 60 for e in ev]
    assert health.evaluate_soc(ev, full, alive, T0 + 21 * 86400)["level"] == "advies"
    assert health.evaluate_soc(ev, full, alive, T0 + 21 * 86400, other)["level"] == "ok"


def test_no_full_for_14_days_is_an_occurrence_only_while_ha_ran():
    alive = _alive(range(0, 30))
    r = health.evaluate_soc([], [], alive, T0 + 30 * 86400)
    assert r["count"] == 1
    gappy = _alive(list(range(0, 8)) + list(range(10, 18)))  # HA off for 2 days
    assert health.evaluate_soc([], [], gappy, T0 + 18 * 86400)["count"] == 0


def test_monthly_table():
    full = _alive([0, 1, 2])
    ev = _occ([1], 11.0) + [{"ts": T0 + 2 * 86400, "type": "b99", "value": 0.6}]
    r = health.evaluate_soc(ev, full, full, T0 + 3 * 86400)
    row = r["trend"][0]
    assert row["full_days"] == 3 and row["dev"] == 11.0 and row["b99"] == 0.6


def _cells(values, start_day=0, step=7):
    return [
        {"ts": T0 + (start_day + i * step) * 86400, "spread_mv": v}
        for i, v in enumerate(values)
    ]


def test_cell_baseline_and_ladder():
    base = _cells([60, 62, 58, 61] * 4)  # first 3+ months: about 60 mV
    late = _cells([90, 130, 125], start_day=120, step=5)
    r = health.evaluate_cell_health(base + late, [], T0 + 131 * 86400)
    assert r["base_mv"] == 60 and r["limit_mv"] == 120
    assert r["level"] == "letop"  # two in a row above 2x
    r = health.evaluate_cell_health(base + late + _cells([70, 128], 131, 3), [], T0 + 135 * 86400)
    assert r["level"] == "advies"  # three within 45 days
    rest4 = [{"ts": T0 + 136 * 86400, "type": "rest", "value": 4.5}]
    assert health.evaluate_cell_health(base + late + _cells([70, 128], 131, 3), rest4, T0 + 137 * 86400)["level"] == "advies"
    rest8 = [{"ts": T0 + 136 * 86400, "type": "rest", "value": 8.2}]
    assert health.evaluate_cell_health(base + late + _cells([70, 128], 131, 3), rest8, T0 + 137 * 86400)["level"] == "ok"


def test_reliability_calibration_and_cold():
    since = T0
    rec = {"ts": T0 + 30 * 86400, "start_ts": T0 + 29.8 * 86400}
    assert health.reliability(rec, [T0 + 25 * 86400], since)["reliable"]
    old = health.reliability(rec, [T0 + 5 * 86400], since)
    assert not old["reliable"] and old["why"] == "no_calibration"
    assert health.reliability({**rec, "temp_c": 3.0}, [T0 + 29 * 86400], since)["why"] == "cold"
    # measurements from before SOC monitoring (older versions): unknown, shown as calibrated
    assert health.reliability({"ts": T0 - 86400}, [], since)["reliable"]


def test_sensitivity_soc():
    alive, full = _alive(range(-20, 60)), _some_full(range(-20, 60))
    ev = _occ([0, 10, 20], size=4.0)  # 4 % off: only counts when strict
    now = T0 + 21 * 86400
    assert health.evaluate_soc(ev, full, alive, now)["level"] == "ok"
    assert health.evaluate_soc(ev, full, alive, now, event_pct=3.0)["level"] == "advies"
    big = _occ([0, 10, 20], size=6.0)
    assert health.evaluate_soc(big, full, alive, now, event_pct=8.0)["level"] == "ok"
    off = health.evaluate_soc(big, full, alive, now, enabled=False)
    assert off["level"] == "ok" and off["trend"]  # table still there


def test_sensitivity_cells():
    base = _cells([60, 62, 58, 61] * 4)
    late = _cells([100, 105, 110], start_day=120, step=5)  # about 1.7x normal
    now = T0 + 131 * 86400
    assert health.evaluate_cell_health(base + late, [], now)["level"] == "ok"
    strict = health.evaluate_cell_health(base + late, [], now, factor=1.5)
    assert strict["level"] == "advies" and strict["limit_mv"] == 90
    assert health.evaluate_cell_health(base + late, [], now, factor=1.5, enabled=False)["level"] == "ok"
