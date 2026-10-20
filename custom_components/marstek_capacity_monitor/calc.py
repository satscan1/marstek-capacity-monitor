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
from datetime import date, datetime, timezone
from statistics import median
from typing import Any

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
MAX_RECORDS = 500
TREND_MONTHS = 12
HISTORY_ITEMS = 10


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
    }


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
        kwh = p * dt / 3_600_000.0  # left Riemann sum
        if kwh >= 0:
            self.s["e_charge_kwh"] += kwh
        else:
            self.s["e_discharge_kwh"] += -kwh
        self.s["power_ts"] = ts

    def update_power(self, power_w: float | None, ts: float) -> None:
        """New power value (W). The learned sign is applied, so after a
        correction positive always means charging. None = unknown."""
        self._integrate(ts)
        self.s["power_w"] = None if power_w is None else power_w * self.s["sign"]
        if power_w is None:
            self.s["power_ts"] = None

    def tick(self, ts: float) -> None:
        """Call periodically (<= every 60 s), like the max sub-interval of the
        HA Riemann helper, so a constant power is still integrated."""
        self._integrate(ts)

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
            return None

        rising = sw["direction"] == "charge"
        if (rising and soc > ext["soc"]) or (not rising and soc < ext["soc"]):
            sw["extreme"] = self._point(soc, ts)
            return None

        if abs(ext["soc"] - soc) < HYSTERESIS_PCT:
            return None

        # Turning point confirmed: the swing runs from start to extreme.
        flipped = self._check_sign(sw)
        record = self._make_record(sw)
        if record is not None and flipped:
            record["sign_corrected"] = True
        self.s["swing"] = {
            "direction": "discharge" if rising else "charge",
            "start": dict(ext),
            "extreme": self._point(soc, ts),
            "valid": True,
        }
        return record

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
            self.s["sign"] *= -1
            self.s["sign_confirmed"] = True
            self.s["sign_flipped"] = not self.s["sign_flipped"]
            self.s["e_charge_kwh"], self.s["e_discharge_kwh"] = (
                self.s["e_discharge_kwh"],
                self.s["e_charge_kwh"],
            )
            for pt in (st, ex):
                pt["e_charge"], pt["e_discharge"] = pt["e_discharge"], pt["e_charge"]
            if self.s["power_w"] is not None:
                self.s["power_w"] = -self.s["power_w"]
            return True
        return False

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
            "cumulative_discharge_kwh": round(self.s["e_discharge_kwh"], 3),
        }


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
) -> dict[str, Any]:
    """Every number the sensors and the cards show."""
    today = now.date()
    usable = spec.usable_kwh

    def cycles_at(cum_kwh: float) -> float:
        return spec.initial_cycles + (cum_kwh / usable if usable > 0 else 0.0)

    def pct(kwh: float) -> float:
        return kwh / usable * 100 if usable else 0.0

    cycles = cycles_at(cumulative_discharge_kwh)

    window_start = now.timestamp() - MEASURE_WINDOW_DAYS * 86400
    full = sorted((r for r in records if is_full_discharge(r)), key=lambda r: r["ts"])
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

    # Monthly trend, newest month first
    by_month: dict[str, list[dict[str, Any]]] = {}
    for r in full:
        by_month.setdefault(datetime.fromtimestamp(r["ts"]).strftime("%Y-%m"), []).append(r)
    trend = []
    for key in sorted(by_month, reverse=True)[:TREND_MONTHS]:
        recs = by_month[key]
        mc = [c for c in (capacity_from_record(spec, r) for r in recs) if c]
        if not mc:
            continue
        mid = recs[len(recs) // 2]
        m_exp = expected_pct(
            spec,
            datetime.fromtimestamp(mid["ts"]).date(),
            cycles_at(mid.get("cumulative_discharge_kwh", cumulative_discharge_kwh)),
        )
        m_pct = pct(median(mc))
        trend.append(
            {
                "month": key,
                "kwh": round(median(mc), 2),
                "pct": round(m_pct, 1),
                "expected_pct": round(m_exp, 1),
                "diff_pct": round(m_pct - m_exp, 1),
                "status": classify(spec, m_pct, m_exp),
                "n": len(mc),
            }
        )

    history = []
    for r in reversed(full[-HISTORY_ITEMS:]):
        cap = capacity_from_record(spec, r) or 0.0
        history.append(
            {
                "date": datetime.fromtimestamp(r["ts"]).strftime("%Y-%m-%d"),
                "kwh": round(cap, 3),
                "pct": round(pct(cap), 1),
                "soc": f"{r['soc_start']:.0f}->{r['soc_end']:.0f}",
                "e_dc_kwh": r["e_dc_kwh"],
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
        "last_full_discharge": _utc(full[-1]["ts"]) if full else None,
        "last_full_charge": _utc(charges[-1]["ts"]) if charges else None,
        "age_years": round(age_years(spec, today), 2) if spec.purchase_date else None,
        "cycles": round(cycles, 1),
        "expected_pct": round(exp, 1),
        "expected_kwh": round(exp_kwh, 3),
        "margin_kwh": round(measured_kwh - exp_kwh, 3) if measured_kwh is not None else None,
        "red_pct": spec.red_pct,
        "red_kwh": round(usable * spec.red_pct / 100, 3),
        "tolerance_pct": spec.tolerance_pct,
        "warranty_end": w_end,
        "in_warranty": w_end is None or today <= w_end,
        "status": status,
        "trend": trend,
        "history": history,
    }
