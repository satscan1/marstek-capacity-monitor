"""Calculation core of Marstek Capacity Monitor.

This module deliberately has NO Home Assistant dependency so the maths can be
tested on its own.

Three capacities are kept strictly apart:

* nominal capacity   - what is in the cells in total (e.g. 5.12 kWh)
* usable capacity    - nominal minus the internal reserve
                       (e.g. 5.12 kWh at 90 % DoD = 4.61 kWh) = "100 % of new"
* measured capacity  - what actually came out of the cells on the DC side
                       during a full discharge, scaled to the usable SOC band

Architecture: Event (SOC or power change) -> Context (swing detection, DC
energy integration) -> Result (one session record per completed swing).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from statistics import median
from typing import Any

try:
    from . import health as _health
except ImportError:  # loaded on its own, without Home Assistant (tests)
    import importlib.util as _ilu
    from pathlib import Path as _Path

    _hs = _ilu.spec_from_file_location("mcm_health", _Path(__file__).with_name("health.py"))
    _health = _ilu.module_from_spec(_hs)
    _hs.loader.exec_module(_health)
reliability = _health.reliability

# ---------------------------------------------------------------------------
# Tuning (defaults match the Marstek Venus E 5.12 kWh)
# ---------------------------------------------------------------------------

HYSTERESIS_PCT = 3.0  # a swing closes once SOC moves back 3 points from its extreme
MIN_SWING_PCT = 20.0  # only record swings of >= 20 SOC points
FULL_HIGH_PCT = 95.0  # a full discharge starts at or above 95 %
FULL_LOW_PCT = 15.0  # ... and ends at or below 15 %
MEDIAN_OF_LAST = 3  # measured capacity = median of the last 3 full discharges
MEASURE_WINDOW_DAYS = 365
MAX_GAP_S = 300.0  # no power value for longer than this -> swing unreliable
# A Home Assistant restart of up to 10 minutes is bridged: the energy in the gap
# is estimated from the power just before and just after (average). Longer -> invalid.
MAX_BRIDGE_S = 600.0
MAX_RECORDS = 500  # other swings kept (recent context only)
MAX_FULL_RECORDS = 3000  # full discharges are kept for the whole warranty period
TREND_MONTHS = 120  # monthly trend over 10 years (warranty period)
FIRST_PERIOD_DAYS = 183  # first half year: chart per 2 weeks
HISTORY_ITEMS = 10
# SOC meter at the edges (0.5.1): energy per SOC point in the first or last
# 3 points of a swing compared with the middle (30-80 %). A battery whose SOC
# stands still at the top or bottom while energy keeps flowing makes the
# capacity look too high (or low); such a measurement gets an open dot.
EDGE_PTS = 3
EDGE_RATIO = 2.0
EDGE_MID = (30.0, 80.0)
EDGE_MIN_MID_STEPS = 5


@dataclass
class BatterySpec:
    """Factory data and warranty terms of one battery."""

    nominal_kwh: float = 5.12
    reserve_kwh: float = 0.51  # datasheet: DoD 90 % of 5.12 kWh
    purchase_date: date | None = None
    warranty_years: float = 10.0
    cycle_life: float = 6000.0
    cycle_eol_pct: float = 80.0
    red_pct: float = 75.0  # at or below: report to Marstek (via the app)
    tolerance_pct: float = 5.0  # green while within this many points of expected
    initial_cycles: float = 0.0

    @property
    def usable_kwh(self) -> float:
        return max(self.nominal_kwh - self.reserve_kwh, 0.0)

    @property
    def usable_band_pct(self) -> float:
        """SOC points covered by the usable capacity (5.12 / 0.51 -> 90)."""
        if self.nominal_kwh <= 0:
            return 100.0
        return self.usable_kwh / self.nominal_kwh * 100.0

    @property
    def warranty_end(self) -> date | None:
        if self.purchase_date is None:
            return None
        months = int(round(self.warranty_years * 12))
        idx = self.purchase_date.month - 1 + months
        return date(
            self.purchase_date.year + idx // 12,
            idx % 12 + 1,
            min(self.purchase_date.day, 28),
        )


# ---------------------------------------------------------------------------
# Expectation line (ageing by use: the factory cycle rating)
# ---------------------------------------------------------------------------


def age_years(spec: BatterySpec, on: date) -> float | None:
    if spec.purchase_date is None:
        return None
    return max((on - spec.purchase_date).days, 0) / 365.25


def cycle_expected_pct(spec: BatterySpec, cycles: float) -> float:
    """Cycle line: straight line from 100 % to the factory rating
    (e.g. 80 % after 6,000 full cycles)."""
    if spec.cycle_life <= 0:
        return 100.0
    drop = (100.0 - spec.cycle_eol_pct) * cycles / spec.cycle_life
    return max(100.0 - drop, 0.0)


def expected_pct(spec: BatterySpec, on: date, cycles: float) -> float:
    """Expected capacity. Only the factory cycle line counts: Marstek gives
    no capacity guarantee in years. `on` is kept for future use."""
    return cycle_expected_pct(spec, cycles)


# About half of the usable capacity: more likely a wrong model than a battery
# that lost half its capacity (a Venus C, 2.56 kWh, set up as a Venus E,
# 5.12 kWh, measures about 50 %). Shown as "check the model", not red.
CHECK_MODEL_PCT = (40.0, 60.0)

# Above this a measurement cannot be the battery: more energy was counted than
# fits in it. The SOC meter alone explains at most about 120 % (it stands
# still at the top or bottom for a while). Far above that the power sensor is
# wrong: stuck on its last value instead of falling back to 0 W, the wrong
# sensor, or a wrong factor. Such a measurement does not count, and the
# battery shows "check the power sensor" (a user saw 1300 %, Oct 2026).
IMPOSSIBLE_PCT = 130.0


def classify(spec: BatterySpec, pct: float | None, expected: float) -> str:
    """good   : at or at most `tolerance` points below expected
    attention : further below expected, but above the red threshold
    critical  : at or below the red threshold (default 75 %)"""
    if pct is None:
        return "no_measurement"
    if pct <= spec.red_pct:
        return "critical"
    if pct >= expected - spec.tolerance_pct:
        return "good"
    return "attention"


# ---------------------------------------------------------------------------
# How sure is the latest value? (0.5.5)
# ---------------------------------------------------------------------------
# Above 100 %: shown as "provisional" until the last 5 measurements all stay
# above 100 % within 3 points of each other; then it is a real "more than the
# rating plate" and the normal colours apply.
# Sudden drop: more than 5 points below the 3 measurements before it, in one
# go. Real wear is slow; a jump like that is nearly always the battery's SOC
# meter shifting for a while (MT1, April 2026). Shown as "not confirmed yet"
# (grey) until it holds for 5 measurements in a row; if it recovers, it goes.
# Change since start: the latest value against the middle of the first 3
# measurements of this monitor (not against "new").

CONFIRM_N = 5
STABLE_PTS = 3.0
DROP_PTS = 5.0
BASELINE_N = 3


def confidence(pcts: list[float], measured_pct: float | None) -> dict[str, Any]:
    """pcts: every full-discharge measurement in % of new, oldest first."""
    out: dict[str, Any] = {
        "display_state": "normal",
        "baseline_pct": None,
        "since_start_pct": None,
        "confirm_needed": CONFIRM_N,
        "confirm_count": None,
        "drop_ref_pct": None,
        "spread_pts": None,
    }
    if len(pcts) >= BASELINE_N:
        base = median(pcts[:BASELINE_N])
        out["baseline_pct"] = round(base, 1)
        if measured_pct is not None:
            out["since_start_pct"] = round(measured_pct - base, 1)
    # Sudden drop: the longest run of latest measurements that are all more
    # than DROP_PTS below the middle of the 3 measurements before that run,
    # and the value shown (median of the last 3) is itself that much lower.
    # One odd measurement that the median already hides is not a drop.
    run, ref = 0, None
    for k in range(1, len(pcts)):
        before = pcts[:-k]
        if len(before) < BASELINE_N:
            break
        r = median(before[-BASELINE_N:])
        if all(p < r - DROP_PTS for p in pcts[-k:]):
            run, ref = k, r
    if 0 < run < CONFIRM_N and measured_pct is not None and measured_pct < ref - DROP_PTS:
        out.update(display_state="drop_unconfirmed", confirm_count=run, drop_ref_pct=round(ref, 1))
        return out
    if measured_pct is not None and measured_pct > 100:
        last = pcts[-CONFIRM_N:]
        # Count the latest measurements that are above 100 % AND within
        # STABLE_PTS of each other: that is what "x/5" on the card means.
        close = 0
        for k in range(1, min(len(pcts), CONFIRM_N) + 1):
            run = pcts[-k:]
            if all(p > 100 for p in run) and max(run) - min(run) <= STABLE_PTS:
                close = k
            else:
                break
        stable = (
            len(last) == CONFIRM_N
            and all(p > 100 for p in last)
            and max(last) - min(last) <= STABLE_PTS
        )
        out.update(
            display_state="high_confirmed" if stable else "high_provisional",
            confirm_count=close,
            spread_pts=round(max(last) - min(last), 1) if len(last) == CONFIRM_N else None,
        )
    return out


def capacity_from_record(spec: BatterySpec, rec: dict[str, Any]) -> float | None:
    """Measured usable capacity (kWh) from one session record."""
    delta = rec.get("delta_soc") or 0
    if delta <= 0:
        return None
    return rec["e_dc_kwh"] / delta * spec.usable_band_pct


def is_full_discharge(rec: dict[str, Any]) -> bool:
    return (
        rec.get("direction") == "discharge"
        and rec.get("valid", True)
        and rec.get("soc_start", 0) >= FULL_HIGH_PCT
        and rec.get("soc_end", 100) <= FULL_LOW_PCT
    )


def prune_records(
    records: list[dict[str, Any]],
    max_other: int = MAX_RECORDS,
    max_full: int = MAX_FULL_RECORDS,
) -> list[dict[str, Any]]:
    """Drop the oldest records, but keep full discharges for years.

    Full discharges are the measurements; other swings are only recent context.
    The order of the remaining records is unchanged.
    """
    full = [i for i, r in enumerate(records) if is_full_discharge(r)]
    other = [i for i, r in enumerate(records) if not is_full_discharge(r)]
    drop = set(full[:-max_full] if len(full) > max_full else [])
    drop |= set(other[:-max_other] if len(other) > max_other else [])
    if not drop:
        return records
    return [r for i, r in enumerate(records) if i not in drop]


def is_full_charge(rec: dict[str, Any]) -> bool:
    return (
        rec.get("direction") == "charge"
        and rec.get("valid", True)
        and rec.get("soc_start", 100) <= FULL_LOW_PCT
        and rec.get("soc_end", 0) >= FULL_HIGH_PCT
    )


# ---------------------------------------------------------------------------
# Context: DC energy integration + swing detection
# ---------------------------------------------------------------------------


def new_tracker_state() -> dict[str, Any]:
    return {
        "e_charge_kwh": 0.0,  # cumulative DC charged (own integrator)
        "e_discharge_kwh": 0.0,  # cumulative DC discharged (own integrator)
        "power_w": None,  # last power value, positive = charging
        "power_ts": None,
        "soc": None,
        "swing": None,
        "sign": 1,  # multiplier applied to incoming power (auto-detected)
        "sign_confirmed": False,
        "sign_flipped": False,
        "bridge": None,  # {"ts", "p"}: last power before a restart, to bridge the gap
    }


def edge_ratio(steps: list[list[float]] | None, direction: str) -> float | None:
    """How much more energy per SOC point went in or out in the first or last
    EDGE_PTS points of a swing than in the middle (30-80 %).

    1.0 = the SOC meter kept pace all the way; 2.0 or more = at the top or the
    bottom the SOC stood (nearly) still while energy kept flowing, so the
    capacity of this swing is off. None = not enough steps to tell."""
    if not steps or len(steps) < EDGE_MIN_MID_STEPS + 2:
        return None
    k = 1 if direction == "charge" else 2
    rates = []
    for a, b in zip(steps, steps[1:]):
        d = abs(b[0] - a[0])
        if d > 0 and EDGE_MID[0] <= min(a[0], b[0]) and max(a[0], b[0]) <= EDGE_MID[1]:
            rates.append((b[k] - a[k]) / d)
    if len(rates) < EDGE_MIN_MID_STEPS:
        return None
    mid = median(rates)
    if mid <= 0:
        return None

    def rate(first: list[float], others: list[list[float]]) -> float | None:
        for st in others:
            d = abs(st[0] - first[0])
            if d >= EDGE_PTS:
                return abs(st[k] - first[k]) / d
        return None

    top = rate(steps[0], steps[1:])
    bottom = rate(steps[-1], list(reversed(steps[:-1])))
    edges = [r for r in (top, bottom) if r is not None]
    return round(max(edges) / mid, 2) if edges else None


class SwingTracker:
    """Integrates DC power into energy and detects charge/discharge swings.

    The state is a plain dict so Home Assistant can persist it.
    """

    def __init__(
        self, state: dict[str, Any] | None = None, auto_sign: bool = True
    ) -> None:
        self.s = {**new_tracker_state(), **(state or {})}
        self.auto_sign = auto_sign

    # -- energy -------------------------------------------------------------

    def _integrate(self, ts: float) -> None:
        last_ts = self.s["power_ts"]
        p = self.s["power_w"]
        if last_ts is None or p is None:
            self.s["power_ts"] = ts
            return
        dt = ts - last_ts
        if dt <= 0:
            return
        if dt > MAX_GAP_S:
            # Too long without data (restart, sensor gone): do not guess.
            self._invalidate_swing("data_gap")
            self.s["power_ts"] = ts
            return
        self._add_energy(p * dt / 3_600_000.0)  # left Riemann sum
        self.s["power_ts"] = ts

    def _add_energy(self, kwh: float) -> None:
        if kwh >= 0:
            self.s["e_charge_kwh"] += kwh
        else:
            self.s["e_discharge_kwh"] += -kwh

    def start_after_restart(self, ts: float) -> None:
        """Home Assistant was down. Keep the last power value so a short gap
        (<= MAX_BRIDGE_S) can be bridged when the first new value arrives."""
        last_ts, p = self.s.get("power_ts"), self.s.get("power_w")
        self.s["power_w"] = None
        self.s["power_ts"] = None
        if last_ts is None or p is None or ts - last_ts > MAX_BRIDGE_S:
            self.s["bridge"] = None
            self._invalidate_swing("restart")
        else:
            self.s["bridge"] = {"ts": last_ts, "p": p}

    def _close_bridge(self, p_new: float | None, ts: float) -> dict[str, Any] | None:
        """Fill the restart gap with the average of the power before and after.
        Too late (> MAX_BRIDGE_S) -> the swing does not count.

        SOC values that came in while the bridge was open are held back and
        replayed here, after the gap energy is added, so swing points always
        include it. Returns a session record if that replay completes a swing."""
        br = self.s.get("bridge")
        if not br:
            return None
        gap = ts - br["ts"]
        if gap > br.get("limit", MAX_BRIDGE_S):
            self.s["bridge"] = None
            self._invalidate_swing(br.get("reason", "restart"))
        elif p_new is None:
            return None  # still waiting for the first value after the restart
        else:
            if gap > 0:
                self._add_energy((br["p"] + p_new) / 2 * gap / 3_600_000.0)
                sw = self.s.get("swing")
                if sw is not None:
                    sw["bridged_s"] = round(sw.get("bridged_s", 0) + gap)
            self.s["bridge"] = None
        pending = br.get("soc")
        if pending is None:
            return None
        return self.update_soc(pending, ts)

    def update_power(self, power_w: float | None, ts: float) -> dict[str, Any] | None:
        """New power value (W). The learned sign is applied, so after a
        correction positive always means charging. None = unknown.
        Returns a session record only when a restart bridge closes and the
        held-back SOC completes a swing (rare); otherwise None."""
        if self.s.get("bridge"):
            new = None if power_w is None else power_w * self.s["sign"]
            self.s["power_w"] = new
            self.s["power_ts"] = ts if new is not None else None
            return self._close_bridge(new, ts)
        self._integrate(ts)
        if power_w is None and self.s["power_w"] is not None and self.s["power_ts"] is not None:
            # Power sensor unavailable (e.g. a Modbus hiccup): bridge it like a
            # restart, but only up to MAX_GAP_S; longer -> the swing does not count.
            self.s["bridge"] = {
                "ts": self.s["power_ts"],
                "p": self.s["power_w"],
                "limit": MAX_GAP_S,
                "reason": "data_gap",
            }
        self.s["power_w"] = None if power_w is None else power_w * self.s["sign"]
        if power_w is None:
            self.s["power_ts"] = None
        return None

    def tick(self, ts: float) -> dict[str, Any] | None:
        """Call periodically (<= every 60 s), like the max sub-interval of the
        HA Riemann helper, so a constant power is still integrated."""
        if self.s.get("bridge"):
            return self._close_bridge(None, ts)  # gives up once the gap is too long
        self._integrate(ts)
        return None

    @property
    def cumulative_discharge_kwh(self) -> float:
        return self.s["e_discharge_kwh"]

    # -- swings -------------------------------------------------------------

    def _invalidate_swing(self, reason: str) -> None:
        sw = self.s.get("swing")
        if sw is not None:
            sw["valid"] = False
            sw["reason"] = reason

    def _point(self, soc: float, ts: float) -> dict[str, float]:
        return {
            "soc": soc,
            "ts": ts,
            "e_charge": self.s["e_charge_kwh"],
            "e_discharge": self.s["e_discharge_kwh"],
        }

    def update_soc(self, soc: float, ts: float) -> dict[str, Any] | None:
        """New SOC value. Returns a session record when a swing of >= 20
        points has completed, otherwise None."""
        if self.s.get("bridge"):
            # Restart gap not filled yet: hold the SOC back (see _close_bridge).
            self.s["soc"] = soc
            self.s["bridge"]["soc"] = soc
            return None
        self._integrate(ts)
        self.s["soc"] = soc
        sw = self.s.get("swing")
        if sw is None:
            self.s["swing"] = {
                "direction": None,
                "start": self._point(soc, ts),
                "extreme": self._point(soc, ts),
                "valid": True,
            }
            return None

        ext = sw["extreme"]
        if sw["direction"] is None:
            if abs(soc - sw["start"]["soc"]) >= 1:
                sw["direction"] = "charge" if soc > sw["start"]["soc"] else "discharge"
                sw["extreme"] = self._point(soc, ts)
                sw["steps"] = [self._step(sw["start"]), self._step(sw["extreme"])]
            return None

        rising = sw["direction"] == "charge"
        if (rising and soc > ext["soc"]) or (not rising and soc < ext["soc"]):
            sw["extreme"] = self._point(soc, ts)
            steps = sw.get("steps")
            if steps is not None and len(steps) < 200:
                steps.append(self._step(sw["extreme"]))
            return None

        if abs(ext["soc"] - soc) < HYSTERESIS_PCT:
            return None

        # Turning point confirmed: the swing runs from start to extreme.
        flipped = self._check_sign(sw)
        record = self._make_record(sw)
        if record is not None and flipped:
            record["sign_corrected"] = True
        new_ext = self._point(soc, ts)
        self.s["swing"] = {
            "direction": "discharge" if rising else "charge",
            "start": dict(ext),
            "extreme": new_ext,
            "valid": True,
            "steps": [self._step(ext), self._step(new_ext)],
        }
        return record

    @staticmethod
    def _step(pt: dict[str, float]) -> list[float]:
        """[soc, energy charged, energy discharged] at a new SOC extreme."""
        return [pt["soc"], round(pt["e_charge"], 4), round(pt["e_discharge"], 4)]

    def _check_sign(self, sw: dict[str, Any]) -> bool:
        """Auto-detect whether the power sensor reports charging as negative.

        On the first clear swing (>= 20 points, >= 0.2 kWh) we compare where
        the energy went with the direction the SOC moved. If almost all
        energy ended up in the opposite bucket, the sign is reversed: we flip
        it, move the counted energy to the right buckets and remember it.
        Returns True when a flip happened."""
        if not self.auto_sign or self.s["sign_confirmed"] or not sw.get("valid", True):
            return False
        st, ex = sw["start"], sw["extreme"]
        if abs(ex["soc"] - st["soc"]) < MIN_SWING_PCT:
            return False
        d_charge = ex["e_charge"] - st["e_charge"]
        d_discharge = ex["e_discharge"] - st["e_discharge"]
        along, against = (
            (d_charge, d_discharge)
            if sw["direction"] == "charge"
            else (d_discharge, d_charge)
        )
        if along >= 0.2 and along > 2 * against:
            self.s["sign_confirmed"] = True
            return False
        if against >= 0.2 and against > 2 * along:
            self._flip_sign()
            self.s["sign_confirmed"] = True
            return True
        return False

    def _flip_sign(self) -> None:
        """Reverse the sign: move the counted energy to the right buckets."""
        self.s["sign"] *= -1
        self.s["sign_flipped"] = not self.s["sign_flipped"]
        self.s["e_charge_kwh"], self.s["e_discharge_kwh"] = (
            self.s["e_discharge_kwh"],
            self.s["e_charge_kwh"],
        )
        sw = self.s.get("swing") or {}
        for pt in (sw.get("start"), sw.get("extreme")):
            if pt:
                pt["e_charge"], pt["e_discharge"] = pt["e_discharge"], pt["e_charge"]
        for st in sw.get("steps") or []:
            st[1], st[2] = st[2], st[1]
        if self.s["power_w"] is not None:
            self.s["power_w"] = -self.s["power_w"]
        if self.s.get("bridge"):
            self.s["bridge"]["p"] = -self.s["bridge"]["p"]

    def adopt_sign(self, other: "SwingTracker") -> bool:
        """Take over a sign that another tracker (the history replay) already
        learned, if this one has not learned it yet. Returns True if flipped."""
        if self.s["sign_confirmed"] or not other.s["sign_confirmed"]:
            return False
        flipped = other.s["sign"] != self.s["sign"]
        if flipped:
            self._flip_sign()
        self.s["sign_confirmed"] = True
        return flipped

    def _make_record(self, sw: dict[str, Any]) -> dict[str, Any] | None:
        st, ex = sw["start"], sw["extreme"]
        delta = abs(ex["soc"] - st["soc"])
        if delta < MIN_SWING_PCT:
            return None
        if sw["direction"] == "discharge":
            e = ex["e_discharge"] - st["e_discharge"]
            e_counter = ex["e_charge"] - st["e_charge"]
        else:
            e = ex["e_charge"] - st["e_charge"]
            e_counter = ex["e_discharge"] - st["e_discharge"]
        dur_h = max(ex["ts"] - st["ts"], 1) / 3600.0
        return {
            "ts": ex["ts"],
            "start_ts": st["ts"],
            "direction": sw["direction"],
            "soc_start": st["soc"],
            "soc_end": ex["soc"],
            "delta_soc": round(delta, 1),
            "duration_min": round(dur_h * 60, 1),
            "e_dc_kwh": round(e, 4),
            "e_dc_counter_kwh": round(e_counter, 4),
            "kwh_per_100pct_dc": round(e / delta * 100, 4),
            "avg_power_dc_w": round(e / dur_h * 1000, 0),
            "valid": bool(sw.get("valid", True)) and e > 0,
            "reason": sw.get("reason"),
            "bridged_s": sw.get("bridged_s"),
            "edge_ratio": edge_ratio(sw.get("steps"), sw["direction"]),
            "cumulative_discharge_kwh": round(self.s["e_discharge_kwh"], 3),
        }


# ---------------------------------------------------------------------------
# History: replay the recorder history once, when a battery is added
# ---------------------------------------------------------------------------

HISTORY_DAYS = 30  # ask the recorder for this much (it usually keeps 10 days)
IDLE_W = 50.0  # below this the battery stands still; quiet sensors are normal then
TICK_S = 60.0
SOC_JUMP_PCT = 2.0  # SOC step after a quiet time that cannot be "standing still"


def replay_history(
    tracker: SwingTracker,
    events: list[tuple[float, str, float | None]],
    health: Any = None,
    health_out: dict[str, list] | None = None,
) -> list[dict[str, Any]]:
    """Feed recorded SOC ("s") and power ("p") values through a tracker.

    The recorder only stores changes. A battery that stands still (|power| <=
    IDLE_W) may report nothing for hours; that time is filled in with ticks.
    A (dis)charging battery whose power did not change for more than MAX_GAP_S
    is treated as a data gap (e.g. Home Assistant was off): that swing does not
    count. Returns the completed swing records, marked as coming from history.

    With `health` (a SocHealthTracker) and `health_out` ({"events", "full_days",
    "alive_days"}) the SOC drift events are collected as well (0.5).
    """
    add_events, note_day = _health.add_events, _health.note_day
    out: list[dict[str, Any]] = []
    soc_before_gap: float | None = None
    for ts, kind, value in sorted(events, key=lambda e: e[0]):
        p, last = tracker.s["power_w"], tracker.s["power_ts"]
        if p is not None and last is not None and abs(p) <= IDLE_W and ts - last > MAX_GAP_S:
            # Quiet time: the battery stood still, or Home Assistant was off.
            # Fill it in, but check the SOC afterwards (see below).
            if soc_before_gap is None:
                soc_before_gap = tracker.s.get("soc")
            t = last + TICK_S
            while t < ts:
                tracker.tick(t)
                t += TICK_S
        gap_in_quiet = False
        if kind == "p":
            rec = tracker.update_power(value, ts)
            if health is not None:
                add_events(
                    health_out["events"],
                    health.on_power(tracker.s["power_w"], ts, gap=bool(tracker.s.get("bridge"))),
                )
        elif value is not None:
            if soc_before_gap is not None and abs(value - soc_before_gap) >= SOC_JUMP_PCT:
                # The SOC moved during the quiet time: the battery was not
                # idle, Home Assistant was off. The energy is unknown.
                tracker._invalidate_swing("data_gap")  # noqa: SLF001
                gap_in_quiet = True
            soc_before_gap = None
            rec = tracker.update_soc(value, ts)
            if health is not None:
                add_events(
                    health_out["events"],
                    health.on_soc(
                        value,
                        tracker.s["e_charge_kwh"],
                        tracker.s["e_discharge_kwh"],
                        ts,
                        gap=gap_in_quiet or bool(tracker.s.get("bridge")),
                    ),
                )
                note_day(health_out["full_days"], health_out["alive_days"], value, ts)
        else:
            rec = None
        if rec:
            rec["source"] = "history"
            # The energy counter of the replay starts at 0; the age of the
            # battery is taken from the live counter instead.
            rec.pop("cumulative_discharge_kwh", None)
            out.append(rec)
    return out


# ---------------------------------------------------------------------------
# Result: evaluation for sensors and card
# ---------------------------------------------------------------------------


def _utc(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def evaluate(
    spec: BatterySpec,
    records: list[dict[str, Any]],
    cumulative_discharge_kwh: float,
    now: datetime,
    tops: list[float] | None = None,
    soc_since: float | None = None,
) -> dict[str, Any]:
    """Every number the sensors and the cards show.

    tops / soc_since (0.5): calibration points of the SOC meter, to mark each
    month as calibrated (filled dot) or less reliable (open dot)."""
    today = now.date()
    usable = spec.usable_kwh

    def cycles_at(cum_kwh: float) -> float:
        return spec.initial_cycles + (cum_kwh / usable if usable > 0 else 0.0)

    def pct(kwh: float) -> float:
        return kwh / usable * 100 if usable else 0.0

    cycles = cycles_at(cumulative_discharge_kwh)

    window_start = now.timestamp() - MEASURE_WINDOW_DAYS * 86400
    every_full = sorted((r for r in records if is_full_discharge(r)), key=lambda r: r["ts"])

    def impossible(r: dict[str, Any]) -> bool:
        c = capacity_from_record(spec, r)
        return c is not None and pct(c) > IMPOSSIBLE_PCT

    # Impossible measurements are kept (history, report) but never counted.
    full = [r for r in every_full if not impossible(r)]
    bad = [r for r in every_full if impossible(r)]
    last_bad = bool(every_full) and impossible(every_full[-1])
    charges = sorted((r for r in records if is_full_charge(r)), key=lambda r: r["ts"])
    recent = [r for r in full if r["ts"] >= window_start]
    caps = [
        c for c in (capacity_from_record(spec, r) for r in recent[-MEDIAN_OF_LAST:]) if c
    ]

    measured_kwh = round(median(caps), 3) if caps else None
    measured_pct = round(pct(measured_kwh), 1) if measured_kwh else None

    exp = expected_pct(spec, today, cycles)
    exp_kwh = usable * exp / 100

    w_end = spec.warranty_end

    status = classify(spec, measured_pct, exp)
    if measured_pct is not None and CHECK_MODEL_PCT[0] <= measured_pct <= CHECK_MODEL_PCT[1]:
        status = "check_model"
    sure = confidence(
        [pct(c) for c in (capacity_from_record(spec, r) for r in full) if c], measured_pct
    )
    if sure["display_state"] == "drop_unconfirmed":
        status = "unconfirmed"
    if last_bad:
        # The newest full discharge cannot be right: the power sensor first.
        status = "check_power"
    # Red is reported (Repairs + phone) only once the last CONFIRM_N
    # measurements are all at or below the red line: one odd measurement
    # never sends anyone to Marstek.
    red_count = 0
    for c in reversed([pct(c) for c in (capacity_from_record(spec, r) for r in full) if c]):
        if c > spec.red_pct:
            break
        red_count += 1
    red_since = full[-red_count]["ts"] if red_count else None
    red_confirmed = status == "critical" and red_count >= CONFIRM_N

    def summary(recs: list[dict[str, Any]]) -> dict[str, Any] | None:
        """One chart point: the middle of the measurements in a period."""
        mc = [c for c in (capacity_from_record(spec, r) for r in recs) if c]
        if not mc:
            return None
        mid = recs[len(recs) // 2]
        m_exp = expected_pct(
            spec,
            datetime.fromtimestamp(mid["ts"]).date(),
            cycles_at(mid.get("cumulative_discharge_kwh", cumulative_discharge_kwh)),
        )
        m_pct = pct(median(mc))
        temps = [r["temp_c"] for r in recs if r.get("temp_c") is not None]
        rel = [reliability(r, tops or [], soc_since) for r in recs]
        good = sum(1 for x in rel if x["reliable"])
        whys = [x["why"] for x in rel if not x["reliable"]]
        ages = [x["ref_age_d"] for x in rel if x.get("ref_age_d") is not None]
        return {
                "kwh": round(median(mc), 2),
                "pct": round(m_pct, 1),
                "expected_pct": round(m_exp, 1),
                "diff_pct": round(m_pct - m_exp, 1),
                "status": classify(spec, m_pct, m_exp),
                "n": len(mc),
                "temp_c": round(median(temps), 1) if temps else None,
                "reliable": good * 2 >= len(rel),
                "why": max(set(whys), key=whys.count) if whys and good * 2 < len(rel) else None,
                "ref_age_d": round(median(ages), 1) if ages else None,
            }

    # Monthly trend, newest month first
    by_month: dict[str, list[dict[str, Any]]] = {}
    for r in full:
        by_month.setdefault(datetime.fromtimestamp(r["ts"]).strftime("%Y-%m"), []).append(r)
    trend = []
    for key in sorted(by_month, reverse=True)[:TREND_MONTHS]:
        point = summary(by_month[key])
        if point:
            trend.append({"month": key, **point})

    # The first half year: a point per 2 weeks, so the chart fills sooner.
    # Fewer than 3 measurements in a point = less reliable (open dot).
    trend_2w = []
    if full:
        first = datetime.fromtimestamp(full[0]["ts"]).replace(hour=0, minute=0, second=0, microsecond=0)
        if (datetime.fromtimestamp(now.timestamp()) - first).days < FIRST_PERIOD_DAYS:
            by_2w: dict[int, list[dict[str, Any]]] = {}
            for r in full:
                by_2w.setdefault((datetime.fromtimestamp(r["ts"]) - first).days // 14, []).append(r)
            for k in sorted(by_2w, reverse=True):
                point = summary(by_2w[k])
                if point:
                    if point["n"] < 3 and point["reliable"]:
                        point.update(reliable=False, why="few")
                    trend_2w.append({"start": (first + timedelta(days=14 * k)).strftime("%Y-%m-%d"), **point})

    history = []
    for r in reversed(every_full[-HISTORY_ITEMS:]):
        cap = capacity_from_record(spec, r) or 0.0
        history.append(
            {
                "impossible": impossible(r),
                "date": datetime.fromtimestamp(r["ts"]).strftime("%Y-%m-%d"),
                "kwh": round(cap, 3),
                "pct": round(pct(cap), 1),
                "soc": f"{r['soc_start']:.0f}->{r['soc_end']:.0f}",
                "e_dc_kwh": r["e_dc_kwh"],
                "temp_c": r.get("temp_c"),
            }
        )

    return {
        "nominal_kwh": round(spec.nominal_kwh, 3),
        "reserve_kwh": round(spec.reserve_kwh, 3),
        "usable_kwh": round(usable, 3),
        "usable_band_pct": round(spec.usable_band_pct, 1),
        "measured_kwh": measured_kwh,
        "measured_pct": measured_pct,
        "loss_kwh": round(usable - measured_kwh, 3) if measured_kwh is not None else None,
        "measurement_count": len(caps),
        "last_measurement": datetime.fromtimestamp(recent[-1]["ts"]) if recent else None,
        "last_full_discharge": _utc(every_full[-1]["ts"]) if every_full else None,
        "last_full_charge": _utc(charges[-1]["ts"]) if charges else None,
        "age_years": round(age_years(spec, today), 2) if spec.purchase_date else None,
        "cycles": round(cycles, 1),
        "expected_pct": round(exp, 1),
        "expected_kwh": round(exp_kwh, 3),
        "margin_kwh": round(measured_kwh - exp_kwh, 3) if measured_kwh is not None else None,
        "red_pct": spec.red_pct,
        "red_count": red_count,
        "red_confirmed": red_confirmed,
        "red_since": red_since,
        "red_kwh": round(usable * spec.red_pct / 100, 3),
        "tolerance_pct": spec.tolerance_pct,
        "warranty_end": w_end,
        "in_warranty": w_end is None or today <= w_end,
        "status": status,
        "impossible_count": len(bad),
        "impossible_last_pct": (
            round(pct(capacity_from_record(spec, bad[-1]) or 0.0), 1) if bad else None
        ),
        "impossible_last_kwh": (
            round(capacity_from_record(spec, bad[-1]) or 0.0, 2) if bad else None
        ),
        "impossible_limit_pct": IMPOSSIBLE_PCT,
        **sure,
        "trend": trend,
        "trend_2w": trend_2w,
        "first_measurement": (
            datetime.fromtimestamp(full[0]["ts"]).strftime("%Y-%m-%d") if full else None
        ),
        "history": history,
    }


# ---------------------------------------------------------------------------
# Progress towards a measurement (for the "collecting data" message)
# ---------------------------------------------------------------------------


def measurement_phase(tracker_state: dict[str, Any]) -> dict[str, Any]:
    """Where the battery is on the way to the next full-discharge measurement.

    waiting_full_charge     - charge to >= 95 % first
    ready                   - full; a discharge to <= 15 % gives a measurement
    full_discharge_running  - discharging from >= 95 %; ends at <= 15 %
    """
    soc = tracker_state.get("soc")
    sw = tracker_state.get("swing") or {}
    out: dict[str, Any] = {"soc": soc}
    start = (sw.get("start") or {}).get("soc")
    if (
        sw.get("direction") == "discharge"
        and start is not None
        and start >= FULL_HIGH_PCT
        and sw.get("valid", True)
    ):
        out["phase"] = "full_discharge_running"
        out["from_soc"] = start
    elif soc is not None and soc >= FULL_HIGH_PCT:
        out["phase"] = "ready"
    else:
        out["phase"] = "waiting_full_charge"
    # Only worth mentioning when a full discharge was actually under way
    if (
        sw
        and not sw.get("valid", True)
        and sw.get("direction") == "discharge"
        and start is not None
        and start >= FULL_HIGH_PCT
    ):
        out["interrupted"] = sw.get("reason")
    return out


# ---------------------------------------------------------------------------
# Cell balance: spread between highest and lowest cell after a full charge
# ---------------------------------------------------------------------------
#
# Event   : end of a full charge (SOC >= 95 %)
# Context : battery at rest (|power| <= 50 W) for 5 minutes, so the spread is
#           not distorted by load. LFP voltage is flat mid-band; differences
#           only show near full.
# Result  : spread = highest - lowest cell in mV, one sample per full charge.
#
# No colours / limits yet: Marstek publishes no normal spread.

CELL_FULL_PCT = FULL_HIGH_PCT
CELL_REARM_PCT = 90.0  # a new sample needs the SOC to drop below this first
CELL_REST_W = 50.0
CELL_REST_S = 300.0
MAX_CELL_RECORDS = 4000  # about one per day at most: covers the warranty period


def new_cell_state() -> dict[str, Any]:
    return {"armed": True, "rest_since": None}


def to_mv(value: float, unit: str | None) -> float:
    """Cell voltage in mV, whatever the sensor reports (V or mV)."""
    if unit == "mV":
        return value
    if unit in ("V",):
        return value * 1000.0
    return value * 1000.0 if value < 10 else value


class CellBalanceTracker:
    """Takes one spread sample per full charge, at rest."""

    def __init__(self, state: dict[str, Any] | None = None) -> None:
        self.s = {**new_cell_state(), **(state or {})}

    def update(
        self,
        soc: float | None,
        power_w: float | None,
        max_mv: float | None,
        min_mv: float | None,
        ts: float,
    ) -> dict[str, Any] | None:
        if soc is None:
            return None
        if soc < CELL_REARM_PCT:
            self.s["armed"] = True
            self.s["rest_since"] = None
            return None
        if not self.s["armed"] or soc < CELL_FULL_PCT:
            self.s["rest_since"] = None
            return None
        if power_w is None or abs(power_w) > CELL_REST_W:
            self.s["rest_since"] = None
            return None
        if self.s["rest_since"] is None:
            self.s["rest_since"] = ts
            return None
        if ts - self.s["rest_since"] < CELL_REST_S:
            return None
        if max_mv is None or min_mv is None or max_mv < min_mv:
            return None
        self.s["armed"] = False
        self.s["rest_since"] = None
        return {
            "ts": ts,
            "soc": round(soc, 1),
            "max_mv": round(max_mv, 1),
            "min_mv": round(min_mv, 1),
            "spread_mv": round(max_mv - min_mv, 1),
        }


def evaluate_cells(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Last spread, monthly median (newest first) and recent samples."""
    recs = sorted(records, key=lambda r: r["ts"])
    by_month: dict[str, list[float]] = {}
    for r in recs:
        by_month.setdefault(datetime.fromtimestamp(r["ts"]).strftime("%Y-%m"), []).append(
            r["spread_mv"]
        )
    trend = [
        {"month": k, "spread_mv": round(median(by_month[k]), 1), "n": len(by_month[k])}
        for k in sorted(by_month, reverse=True)[:TREND_MONTHS]
    ]
    history = [
        {
            "date": datetime.fromtimestamp(r["ts"]).strftime("%Y-%m-%d"),
            "spread_mv": r["spread_mv"],
            "max_mv": r["max_mv"],
            "min_mv": r["min_mv"],
        }
        for r in reversed(recs[-HISTORY_ITEMS:])
    ]
    return {
        "spread_mv": recs[-1]["spread_mv"] if recs else None,
        "last_sample": _utc(recs[-1]["ts"]) if recs else None,
        "sample_count": len(recs),
        "trend": trend,
        "history": history,
    }
