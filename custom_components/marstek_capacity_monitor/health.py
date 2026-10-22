"""SOC drift and cell calibration: is the SOC meter still right, are the cells
still in balance? (0.5)

Like calc.py this module has NO Home Assistant dependency, so it can be tested
on its own.

Event   : a SOC change, a power change or a tick
Context : energy counted by the SwingTracker, power gaps, restarts, other
          batteries jumping at the same time (data errors, not the battery)
Result  : events (calibration point at 100 %, correction jump, extra charge at
          99 %, hanging at 100 %, hours full at rest, discharge-and-charge
          cycle) and a ladder per subject:
            1 occurrence              -> only recorded
            2 within 45 days          -> "let op"   (attention)
            3 within 45 days          -> "advies"   (advice)
          It clears when the monitor sees the advice carried out, or by itself
          after 45 days without a new occurrence.

Thresholds were checked against ten months of data from a Venus E v1 and a
Venus E v2 (Dec 2025 - Oct 2026).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from statistics import median
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Tuning
# ---------------------------------------------------------------------------

TOP_W = 50.0  # calibration point: SOC 100 % and |power| below this ...
TOP_S = 600.0  # ... for 10 minutes (the BMS stopped charging by itself)
BUSY_W = 100.0  # above this the battery is (dis)charging
POWER_STALE_S = 300.0  # no new power value for 5 min while busy = data gap
MAX_SOC_GAP_S = 2700.0  # more than 45 min between two SOC values = data gap
JUMP_PCT = 3.0  # a SOC step of >= 3 points that the energy does not explain
EVENT_PCT = 5.0  # a deviation of >= 5 points is an occurrence
HANG_PCT = 3.0  # discharged >= 3 points of energy while SOC stayed at 100 %
SAME_TIME_S = 180.0  # several batteries jumping within 3 min: data, not battery
CYCLE_LOW_PCT = 20.0  # a top after a low of <= 20 % = one "discharge and charge"
REST_FULL_PCT = 99.0  # full at rest: SOC >= 99 % ...
REST_W = 50.0  # ... and |power| <= 50 W
REST_BREAK_S = 300.0  # short interruptions of rest (UPS top-ups) are ignored
REST_MIN_S = 3600.0  # rest periods shorter than an hour are not recorded

LADDER_DAYS = 45
LOOKBACK_DAYS = 14  # an SOC occurrence only counts when the battery was ...
FULL_MIN_DAYS = 7  # ... full on fewer than 7 of the 14 days before it
NO_FULL_DAYS = 14  # 14 days without a full charge while HA ran = occurrence

REF_MAX_AGE_D = 14.0  # a measurement is calibrated when the last top was <= 14 days before
COLD_C = 5.0  # cells colder than this during a measurement = less reliable

CELL_BASE_DAYS = 90  # baseline = median of the first 3 months of samples
CELL_BASE_MIN = 3
CELL_FACTOR = 2.0  # a sample >= 2x the baseline is an occurrence
CELL_REST_ATTENTION_H = 4.0  # "let op": full for about 4 hours
CELL_REST_ADVICE_H = 8.0  # advice: 8 hours UPS mode (or charge mode)

MAX_EVENTS = 4000
MAX_DAYS = 4000
TREND_MONTHS = 120

LEVELS = ("ok", "letop", "advies")
_RANK = {name: i for i, name in enumerate(LEVELS)}


def day_of(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


def month_of(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m")


def _add_day(days: list[str], day: str, limit: int = MAX_DAYS) -> None:
    if not days or days[-1] != day:
        if day not in days[-3:]:
            days.append(day)
            del days[:-limit]


# ---------------------------------------------------------------------------
# Context: what happens to the SOC meter and at full charge
# ---------------------------------------------------------------------------


def new_health_state() -> dict[str, Any]:
    return {
        "soc": None,  # last SOC value
        "soc_ts": None,  # when that value came in
        "e_c": None,  # cumulative charged kWh at that moment (SwingTracker)
        "e_d": None,  # cumulative discharged kWh at that moment
        "gap": False,  # a data gap since the last SOC value
        "skip_next": False,  # first SOC step after a restart does not count
        "p": None,  # last power, positive = charging
        "p_ts": None,
        "top_since": None,
        "top_done": False,
        "last_top": None,
        "low_since_top": None,  # lowest SOC since the last top
        "rest_since": None,
        "rest_break": None,
        "since": None,  # first data seen (start of SOC monitoring)
    }


class SocHealthTracker:
    """Turns SOC, power and counted energy into health events.

    The state is a plain dict so Home Assistant can persist it. `unit_kwh` is
    one SOC point in kWh (rated capacity / 100)."""

    def __init__(self, state: dict[str, Any] | None = None, unit_kwh: float = 0.0512) -> None:
        self.s = {**new_health_state(), **(state or {})}
        self.unit = unit_kwh if unit_kwh > 0 else 0.0512

    # -- helpers ----------------------------------------------------------

    def after_restart(self) -> None:
        """Home Assistant was down: the next SOC step may hide a gap."""
        self.s["skip_next"] = True
        self.s["p"] = None
        self.s["p_ts"] = None
        self.s["top_since"] = None

    def _check_stale(self, ts: float) -> None:
        p, p_ts = self.s["p"], self.s["p_ts"]
        if p is not None and p_ts is not None and abs(p) > BUSY_W and ts - p_ts > POWER_STALE_S:
            self.s["gap"] = True

    # -- input --------------------------------------------------------------

    def on_power(self, power_w: float | None, ts: float, gap: bool = False) -> list[dict[str, Any]]:
        self._check_stale(ts)
        # the old power held until now: check with it first (a top or a rest
        # period can end exactly at this change)
        out = self._state_checks(ts)
        if gap or power_w is None:
            self.s["gap"] = True
        self.s["p"] = power_w
        self.s["p_ts"] = ts if power_w is not None else None
        return out + self._state_checks(ts)

    def tick(self, ts: float, gap: bool = False) -> list[dict[str, Any]]:
        self._check_stale(ts)
        if gap:
            self.s["gap"] = True
        return self._state_checks(ts)

    def on_soc(
        self, soc: float, e_charge: float, e_discharge: float, ts: float, gap: bool = False
    ) -> list[dict[str, Any]]:
        """New SOC value with the energy counted so far (kWh)."""
        self._check_stale(ts)
        if gap:
            self.s["gap"] = True
        if self.s["since"] is None:
            self.s["since"] = ts
        out: list[dict[str, Any]] = self._state_checks(ts)
        prev, prev_ts = self.s["soc"], self.s["soc_ts"]
        if prev is not None and soc == prev:
            return out
        if prev is not None and prev_ts is not None and self.s["e_c"] is not None:
            charged = (e_charge - self.s["e_c"]) / self.unit
            discharged = (e_discharge - self.s["e_d"]) / self.unit
            net = charged - discharged
            dt = ts - prev_ts
            clean = not self.s["gap"] and not self.s["skip_next"] and dt <= MAX_SOC_GAP_S
            d = soc - prev
            if (
                clean
                and abs(d) >= JUMP_PCT
                and abs(d - net) >= JUMP_PCT
                and soc > 0
                and prev > 0
            ):
                out.append(
                    {"ts": ts, "type": "jump", "value": round(abs(d), 1), "from": prev, "to": soc}
                )
            if prev == 99 and soc == 100 and not self.s["gap"] and not self.s["skip_next"]:
                # energy that still went in while the meter said 99 %
                if dt < 12 * 3600:
                    out.append({"ts": ts, "type": "b99", "value": round(max(charged, 0.0), 1)})
            if prev == 100 and not self.s["gap"] and not self.s["skip_next"]:
                hang = discharged - charged
                if hang >= HANG_PCT:
                    out.append({"ts": ts, "type": "hang", "value": round(hang, 1)})
        self.s["soc"] = soc
        self.s["soc_ts"] = ts
        self.s["e_c"] = e_charge
        self.s["e_d"] = e_discharge
        self.s["gap"] = False
        self.s["skip_next"] = False
        low = self.s.get("low_since_top")
        self.s["low_since_top"] = soc if low is None else min(low, soc)
        return out + self._state_checks(ts)

    # -- calibration point and rest at full --------------------------------

    def _state_checks(self, ts: float) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        soc, p = self.s["soc"], self.s["p"]
        if soc is None:
            return out
        # Calibration point: 100 % and the BMS stopped charging.
        if soc >= 100 and p is not None and abs(p) < TOP_W:
            if self.s["top_since"] is None:
                self.s["top_since"] = ts
            elif not self.s["top_done"] and ts - self.s["top_since"] >= TOP_S:
                self.s["top_done"] = True
                self.s["last_top"] = ts
                out.append({"ts": ts, "type": "top"})
                low = self.s.get("low_since_top")
                if low is not None and low <= CYCLE_LOW_PCT:
                    out.append({"ts": ts, "type": "cycle", "value": low})
                self.s["low_since_top"] = soc
        elif soc < 100:
            self.s["top_since"] = None
            self.s["top_done"] = False
        else:
            self.s["top_since"] = None
        # Full at rest (cell balancing happens here).
        at_rest = soc >= REST_FULL_PCT and p is not None and abs(p) <= REST_W
        if at_rest:
            self.s["rest_break"] = None
            if self.s["rest_since"] is None:
                self.s["rest_since"] = ts
        elif self.s["rest_since"] is not None:
            if soc < REST_FULL_PCT - 1:
                end = self.s["rest_break"] or ts
                out += self._end_rest(end)
            elif self.s["rest_break"] is None:
                self.s["rest_break"] = ts
            elif ts - self.s["rest_break"] > REST_BREAK_S:
                out += self._end_rest(self.s["rest_break"])
        return out

    def _end_rest(self, end: float) -> list[dict[str, Any]]:
        start = self.s["rest_since"]
        self.s["rest_since"] = None
        self.s["rest_break"] = None
        if start is None or end - start < REST_MIN_S:
            return []
        return [{"ts": end, "start": start, "type": "rest", "value": round((end - start) / 3600, 1)}]

    def rest_hours_now(self, ts: float) -> float:
        """Hours full at rest so far in the current stay (0 when not at rest)."""
        start = self.s.get("rest_since")
        if start is None:
            return 0.0
        end = self.s.get("rest_break") or ts
        return max(end - start, 0.0) / 3600


def add_events(events: list[dict[str, Any]], new: list[dict[str, Any]]) -> None:
    events.extend(new)
    del events[:-MAX_EVENTS]


def note_day(full_days: list[str], alive_days: list[str], soc: float | None, ts: float) -> None:
    """Remember which days HA saw data and on which days the battery was full."""
    if soc is None:
        return
    day = day_of(ts)
    _add_day(alive_days, day)
    if soc >= 100:
        _add_day(full_days, day)


# ---------------------------------------------------------------------------
# The ladder
# ---------------------------------------------------------------------------


def run_ladder(
    samples: list[tuple[float, bool, float]],
    actions: list[tuple[float, float]],
    done: Callable[[str, list[float]], bool],
    now_ts: float,
    consecutive: bool = False,
) -> dict[str, Any]:
    """samples: (ts, is_occurrence, size). actions: (ts, value) that may carry
    out an advice; done(level, values_since_level) says whether it did.

    1 occurrence = recorded, 2 within 45 days = letop (with `consecutive`:
    two in a row), 3 within 45 days = advies. The level only goes up within a
    series; it clears when the advice was carried out or after 45 days
    without a new occurrence."""
    window = LADDER_DAYS * 86400
    timeline = sorted(
        [(ts, 0, high, size) for ts, high, size in samples]
        + [(ts, 1, True, value) for ts, value in actions],
        key=lambda x: (x[0], x[1]),
    )
    level, since, series, acts = "ok", None, [], []
    prev_high = False
    last_size = None
    resolved = None
    for ts, kind, high, value in timeline:
        if series and ts - series[-1] > window:
            series, level, since, acts, prev_high = [], "ok", None, [], False
        if kind == 0:
            if not high:
                prev_high = False
                continue
            n = sum(1 for s in series if ts - s <= window) + 1
            consec = prev_high
            series.append(ts)
            prev_high = True
            last_size = value
            new = "advies" if n >= 3 else "letop" if n == 2 and (consec or not consecutive) else "ok"
            if _RANK[new] > _RANK[level]:
                level, since, acts = new, ts, []
        elif level != "ok" and since is not None and ts > since:
            acts.append(value)
            if done(level, acts):
                resolved = ts
                series, level, since, acts, prev_high = [], "ok", None, [], False
    if series and now_ts - series[-1] > window:
        series, level, since = [], "ok", None
    count = sum(1 for s in series if now_ts - s <= window)
    return {
        "level": level,
        "since": since,
        "count": count,
        "last_size": last_size if count else None,
        "last_ts": series[-1] if series else None,
        "resolved": resolved,
    }


def _soc_done(level: str, acts: list[float]) -> bool:
    # let op: once discharging and charging; advies: twice
    return len(acts) >= (1 if level == "letop" else 2)


def _cell_done(level: str, acts: list[float]) -> bool:
    need = CELL_REST_ATTENTION_H if level == "letop" else CELL_REST_ADVICE_H
    return any(h >= need for h in acts)


# ---------------------------------------------------------------------------
# Result: SOC
# ---------------------------------------------------------------------------


def clean_jumps(events: list[dict[str, Any]], other_jumps: list[float]) -> list[dict[str, Any]]:
    """Drop jumps that another battery made within 3 minutes (HA or the
    connection, not the battery)."""
    return [
        e
        for e in events
        if e["type"] != "jump" or not any(abs(e["ts"] - o) <= SAME_TIME_S for o in other_jumps)
    ]


def _deviation_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [e for e in events if e["type"] in ("jump", "b99", "hang")]


def _longest_without_full(full_days: list[str], alive_days: list[str]) -> dict[str, int]:
    """Longest run of days without a full charge, per month in which it ended."""
    out: dict[str, int] = {}
    full = set(full_days)
    run = 0
    for day in sorted(set(alive_days) | full):
        if day in full:
            if run:
                key = day[:7]
                out[key] = max(out.get(key, 0), run)
            run = 0
        else:
            run += 1
    return out


def _no_full_occurrences(full_days: list[str], alive_days: list[str]) -> list[float]:
    """First day of every stretch of 14 days without a full charge, counted
    only on days HA saw data."""
    full, alive = set(full_days), sorted(set(alive_days))
    out: list[float] = []
    run, fired = 0, False
    prev = None
    for day in alive:
        d = datetime.strptime(day, "%Y-%m-%d")
        if prev is not None and (d - prev).days > 1:
            run, fired = 0, False  # HA was off: do not guess
        prev = d
        if day in full:
            run, fired = 0, False
            continue
        run += 1
        if run >= NO_FULL_DAYS and not fired:
            fired = True
            out.append((d + timedelta(hours=12)).timestamp())
    return out


def _full_in_lookback(full: set[str], ts: float) -> int:
    d = datetime.fromtimestamp(ts).date()
    return sum(1 for k in range(1, LOOKBACK_DAYS + 1) if (d - timedelta(days=k)).isoformat() in full)


def evaluate_soc(
    events: list[dict[str, Any]],
    full_days: list[str],
    alive_days: list[str],
    now_ts: float,
    other_jumps: list[float] | None = None,
    event_pct: float = EVENT_PCT,
    enabled: bool = True,
) -> dict[str, Any]:
    """Level, monthly table and the head line of the SOC panel.

    event_pct: deviation that counts as an occurrence (sensitivity);
    enabled=False: the table is kept, but never "let op" or advice.
    """
    ev = clean_jumps(events, other_jumps or [])
    full = set(full_days)

    # Occurrences: one per day, the biggest deviation of that day.
    per_day: dict[str, tuple[float, float]] = {}
    for e in _deviation_events(ev):
        if e["value"] < event_pct:
            continue
        day = day_of(e["ts"])
        if day not in per_day or e["value"] > per_day[day][1]:
            per_day[day] = (e["ts"], e["value"])
    samples = [
        (ts, True, size)
        for ts, size in per_day.values()
        if _full_in_lookback(full, ts) < FULL_MIN_DAYS  # else: own behaviour of the battery
    ]
    samples += [(ts, True, 0.0) for ts in _no_full_occurrences(full_days, alive_days)]
    cycles = [(e["ts"], e.get("value", 0.0)) for e in ev if e["type"] == "cycle"]
    ladder = run_ladder(samples if enabled else [], cycles, _soc_done, now_ts)

    # Monthly table, newest month first
    months: dict[str, dict[str, Any]] = {}

    def m(key: str) -> dict[str, Any]:
        return months.setdefault(
            key, {"month": key, "full_days": 0, "dev": 0.0, "b99": None, "jump": None, "hang": None}
        )

    for day in full:
        m(day[:7])["full_days"] += 1
    for day in alive_days:
        m(day[:7])
    for e in _deviation_events(ev):
        row = m(month_of(e["ts"]))
        row[e["type"]] = max(row[e["type"]] or 0.0, e["value"])
        row["dev"] = max(row["dev"], e["value"])
    longest = _longest_without_full(full_days, alive_days)
    for key, run in longest.items():
        m(key)["no_full_days"] = run
    trend = [
        {**months[k], "dev": round(months[k]["dev"], 1)}
        for k in sorted(months, reverse=True)[:TREND_MONTHS]
    ]

    tops = [e["ts"] for e in ev if e["type"] == "top"]
    last_dev = next((e for e in reversed(_deviation_events(ev))), None)
    return {
        **ladder,
        "last_top": tops[-1] if tops else None,
        "last_deviation": last_dev["value"] if last_dev else None,
        "limit_pct": event_pct,
        "trend": trend,
    }


# ---------------------------------------------------------------------------
# Result: cells
# ---------------------------------------------------------------------------


def evaluate_cell_health(
    cell_records: list[dict[str, Any]],
    rest_events: list[dict[str, Any]],
    now_ts: float,
    rest_now_h: float = 0.0,
    factor: float = CELL_FACTOR,
    enabled: bool = True,
) -> dict[str, Any]:
    """Baseline (own normal value), level and per month the hours full at rest.

    factor: how many times the own normal value is an occurrence (sensitivity);
    enabled=False: never "let op" or advice.
    """
    recs = sorted(cell_records, key=lambda r: r["ts"])
    base = None
    if recs:
        first = recs[0]["ts"]
        early = [r["spread_mv"] for r in recs if r["ts"] - first <= CELL_BASE_DAYS * 86400]
        if len(early) >= CELL_BASE_MIN:
            base = round(median(early), 1)
    samples: list[tuple[float, bool, float]] = []
    if base and enabled:
        first = recs[0]["ts"]
        samples = [
            (r["ts"], r["spread_mv"] >= factor * base, r["spread_mv"])
            for r in recs
            if r["ts"] - first > CELL_BASE_DAYS * 86400
        ]
    rests = [(e["ts"], e["value"]) for e in rest_events if e["type"] == "rest"]
    if rest_now_h > 0:
        rests.append((now_ts, round(rest_now_h, 1)))
    ladder = run_ladder(samples, rests, _cell_done, now_ts, consecutive=True)
    rest_month: dict[str, float] = {}
    for ts, hours in rests:
        key = month_of(ts)
        rest_month[key] = max(rest_month.get(key, 0.0), hours)
    return {
        **ladder,
        "base_mv": base,
        "limit_mv": round(factor * base, 1) if base else None,
        "rest_trend": [
            {"month": k, "rest_h": rest_month[k]} for k in sorted(rest_month, reverse=True)[:TREND_MONTHS]
        ],
    }


# ---------------------------------------------------------------------------
# Is a capacity measurement calibrated?
# ---------------------------------------------------------------------------


def reliability(
    record: dict[str, Any], tops: list[float], soc_since: float | None
) -> dict[str, Any]:
    """Calibrated = the SOC meter had a calibration point at most 14 days
    before the discharge started, and the cells were not colder than 5 °C.

    Measurements from before SOC monitoring started (older versions) are
    unknown and shown as calibrated."""
    start = record.get("start_ts", record["ts"])
    out: dict[str, Any] = {"reliable": True}
    if soc_since is not None and start >= soc_since:
        before = [t for t in tops if t <= start + TOP_S]
        if before:
            age = (start - before[-1]) / 86400
            out["ref_age_d"] = round(max(age, 0.0), 1)
            if age > REF_MAX_AGE_D:
                out["reliable"] = False
                out["why"] = "no_calibration"
        elif start - soc_since > REF_MAX_AGE_D * 86400:
            # monitored for more than 14 days and never a calibration point
            out["reliable"] = False
            out["why"] = "no_calibration"
    temp = record.get("temp_c")
    if temp is not None and temp < COLD_C:
        out["reliable"] = False
        out["why"] = "cold" if "why" not in out else "both"
    return out
