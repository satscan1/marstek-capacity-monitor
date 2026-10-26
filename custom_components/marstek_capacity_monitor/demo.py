"""Demo battery (0.5.5): every situation of the monitor, on demand.

The service marstek_capacity_monitor.demo adds a battery "Demo" (once) and
fills it with made-up data for one situation. The real card, the real
messages under Settings -> Repairs and the real phone messages follow, so
each situation can be seen and lived through before a release. Your own
batteries are never touched; the demo battery can be removed like any other.

No Home Assistant dependency: only builds the data.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

DEMO_ID = "demo"
DEMO_SOC = "sensor.marstek_demo_input_soc"
DEMO_POWER = "sensor.marstek_demo_input_power"
DEMO_CELL_MAX = "sensor.marstek_demo_input_cell_max"
DEMO_CELL_MIN = "sensor.marstek_demo_input_cell_min"
DEMO_TEMP_MAX = "sensor.marstek_demo_input_temp_max"

# Capacity in % of new per full discharge, oldest first
_CAPACITY: dict[str, list[float]] = {
    "normal": [98.0, 97.6, 97.9, 97.2, 97.5, 97.0, 96.8, 97.1],
    "since_start": [99.0, 98.6, 98.8, 98.0, 97.6, 97.2, 96.8, 96.5],
    "high_provisional": [106.2, 105.4, 106.0],
    "high_confirmed": [106.2, 105.4, 106.0, 105.6, 105.1],
    "drop_unconfirmed": [97.4, 96.9, 97.2, 96.6, 84.8, 84.1],
    "drop_confirmed": [97.4, 96.9, 97.2, 96.6, 84.8, 84.1, 85.0, 84.6, 85.2],
    "drop_recovered": [97.4, 96.9, 97.2, 96.6, 84.8, 84.1, 96.5, 96.9],
    "below_spec": [97.0, 93.5, 91.0, 90.2, 89.8, 89.5],
    "critical": [76.0, 74.8, 74.2, 73.9, 73.5],
    "check_model": [50.4, 49.8, 50.1],
}
SCENARIOS = [
    "normal",
    "since_start",
    "high_provisional",
    "high_confirmed",
    "drop_unconfirmed",
    "drop_confirmed",
    "drop_recovered",
    "below_spec",
    "critical",
    "check_model",
    "soc_letop",
    "soc_advies",
    "cells_letop",
    "cells_advies",
    "collecting",
]


def _day(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


def build(scenario: str, now_ts: float, usable_kwh: float, nominal_kwh: float) -> dict[str, Any]:
    """Stored data for one situation (records, SOC events, cells, days)."""
    if scenario not in SCENARIOS:
        raise ValueError(scenario)
    band = usable_kwh / nominal_kwh * 100 if nominal_kwh else 90.0
    day = 86400.0
    caps = _CAPACITY.get(scenario, _CAPACITY["normal"]) if scenario != "collecting" else []
    soc_trouble = scenario in ("soc_letop", "soc_advies")

    records: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    # one full discharge every 4 days, the newest yesterday
    for i, pct in enumerate(caps):
        end = now_ts - (len(caps) - i) * 4 * day + 3 * day
        start = end - 6 * 3600
        delta = 89.0
        kwh = pct / 100 * usable_kwh * delta / band
        records.append({
            "ts": end, "start_ts": start, "direction": "discharge", "soc_start": 100.0, "soc_end": 11.0,
            "delta_soc": delta, "duration_min": 360.0, "e_dc_kwh": round(kwh, 4),
            "e_dc_counter_kwh": round(kwh, 4), "avg_power_dc_w": round(kwh / 6 * 1000),
            "valid": True, "reason": None, "bridged_s": None, "edge_ratio": 1.1,
            "cumulative_discharge_kwh": round(100 + i * 4.4, 3), "temp_c": 16.0, "source": "demo",
        })
        records.append({
            "ts": start - 2 * 3600, "start_ts": start - 8 * 3600, "direction": "charge", "soc_start": 11.0,
            "soc_end": 100.0, "delta_soc": 89.0, "duration_min": 360.0, "e_dc_kwh": round(kwh * 1.08, 4),
            "valid": True, "reason": None, "source": "demo",
        })
        if not soc_trouble:
            events.append({"ts": start - 3600, "type": "top"})

    full_days: list[str] = []
    alive_days = [_day(now_ts - k * day) for k in range(120, -1, -1)]
    if not soc_trouble:
        full_days = [_day(now_ts - k * day) for k in range(120, -1, -1) if k % 2 == 0]
    else:
        # rarely full, and the SOC meter was clearly off on 2 or 3 days
        n = 2 if scenario == "soc_letop" else 3
        for k in range(n):
            ts = now_ts - (20 - k * 6) * day
            events.append({"ts": ts, "type": "jump", "value": 8.0 + k, "from": 91.0, "to": 100.0})

    cell_records: list[dict[str, Any]] = []
    first = now_ts - 130 * day
    # own normal value from the first 3 months; for the cell situations the
    # regular samples stop 3 weeks ago, so the high ones come "in a row"
    last = 105 if scenario in ("cells_letop", "cells_advies") else 130
    for k in range(0, last, 3):
        ts = first + k * day
        cell_records.append({"ts": ts, "soc": 100.0, "max_mv": 3460.0, "min_mv": 3400.0, "spread_mv": 60.0})
    if scenario in ("cells_letop", "cells_advies"):
        n = 2 if scenario == "cells_letop" else 3
        for k in range(n):
            ts = now_ts - (10 - k * 3) * day + 3600
            cell_records.append({"ts": ts, "soc": 100.0, "max_mv": 3540.0, "min_mv": 3400.0, "spread_mv": 140.0})
    cell_records.sort(key=lambda r: r["ts"])

    return {
        "records": sorted(records, key=lambda r: r["ts"]),
        "soc_events": sorted(events, key=lambda e: e["ts"]),
        "cell_records": cell_records,
        "full_days": full_days,
        "alive_days": alive_days,
        "soc_since": now_ts - 120 * day,
        "dismissed": {},
        "notified": {},
        "history_until": None,
    }
