"""Constants for Marstek Capacity Monitor."""

DOMAIN = "marstek_capacity_monitor"
MAX_BATTERIES = 6

# Config entry data (chosen once)
CONF_BATTERY_ID = "battery_id"  # short slug used in entity ids, e.g. "mt1"
CONF_NAME = "name"
CONF_SOC_ENTITY = "soc_entity"
CONF_POWER_ENTITY = "power_entity"

# Options (editable later)
CONF_POWER_SIGN = "power_sign"
SIGN_AUTO = "auto"
SIGN_POSITIVE = "charge_positive"
SIGN_NEGATIVE = "charge_negative"
SIGN_MODES = [SIGN_AUTO, SIGN_POSITIVE, SIGN_NEGATIVE]
CONF_NOMINAL_KWH = "nominal_kwh"
CONF_RESERVE_KWH = "reserve_kwh"
CONF_PURCHASE_DATE = "purchase_date"
CONF_WARRANTY_YEARS = "warranty_years"
CONF_RED_PCT = "red_pct"
CONF_TOLERANCE_PCT = "tolerance_pct"
CONF_CYCLE_LIFE = "cycle_life"
CONF_CYCLE_EOL = "cycle_eol_pct"
CONF_INITIAL_CYCLES = "initial_cycles"

DEFAULTS = {
    CONF_POWER_SIGN: "auto",
    CONF_NOMINAL_KWH: 5.12,
    CONF_RESERVE_KWH: 0.51,  # DoD 90 % (datasheet)
    CONF_WARRANTY_YEARS: 10.0,
    CONF_RED_PCT: 75.0,
    CONF_TOLERANCE_PCT: 5.0,
    CONF_CYCLE_LIFE: 6000.0,
    CONF_CYCLE_EOL: 80.0,
    CONF_INITIAL_CYCLES: 0.0,
}

# Battery model: fills in the factory data, so users only add the install date
CONF_MODEL = "model"
CONF_PACKS = "packs"
MODEL_E_V12 = "venus_e_v12"
MODEL_E_V3 = "venus_e_v3"
MODEL_D = "venus_d"
MODEL_OTHER = "other"
MODELS = [MODEL_E_V12, MODEL_E_V3, MODEL_D, MODEL_OTHER]

# Sources: docs/05-supported-batteries.md (checked 20-10-2026).
# Where sources disagree the most cautious value is used.
_SPEC_LINE = {CONF_CYCLE_LIFE: 6000.0, CONF_CYCLE_EOL: 80.0, CONF_WARRANTY_YEARS: 10.0}
MODEL_PRESETS: dict[str, dict[str, float]] = {
    # Venus E datasheet: 5.12 kWh, 90 % DoD, > 6000 cycles
    MODEL_E_V12: {CONF_NOMINAL_KWH: 5.12, CONF_RESERVE_KWH: 0.51, **_SPEC_LINE},
    # Venus E 3.0 manual: 5.12 kWh, 90 % DoD, > 6000 cycles
    MODEL_E_V3: {CONF_NOMINAL_KWH: 5.12, CONF_RESERVE_KWH: 0.51, **_SPEC_LINE},
    # Venus D product page: 2.56 kWh per unit, calculated with 90 % DoD.
    # Values are per pack and multiplied by the number of packs.
    MODEL_D: {CONF_NOMINAL_KWH: 2.56, CONF_RESERVE_KWH: 0.256, **_SPEC_LINE},
}
MAX_PACKS = 6


def preset_for(model: str, packs: int = 1) -> dict[str, float]:
    """Factory data for a model; empty for 'other'."""
    preset = dict(MODEL_PRESETS.get(model, {}))
    if model == MODEL_D and preset:
        packs = max(1, min(int(packs or 1), MAX_PACKS))
        preset[CONF_NOMINAL_KWH] = round(preset[CONF_NOMINAL_KWH] * packs, 2)
        preset[CONF_RESERVE_KWH] = round(preset[CONF_RESERVE_KWH] * packs, 2)
    return preset


# Optional: highest / lowest cell voltage for the cell balance check
CONF_CELL_MAX_ENTITY = "cell_max_entity"
CONF_CELL_MIN_ENTITY = "cell_min_entity"
# Optional, experimental: highest / lowest cell temperature, stored as context
# with every measurement (a cold battery gives less)
CONF_TEMP_MAX_ENTITY = "temp_max_entity"
CONF_TEMP_MIN_ENTITY = "temp_min_entity"

# Status of the measurement itself (is the monitor working?)
STATUS_SENSOR_MISSING = "sensor_missing"
STATUS_NO_RECENT_DATA = "no_recent_data"
STATUS_COLLECTING = "collecting"
STATUS_MEASURING = "measuring"
MONITOR_STATUSES = [
    STATUS_MEASURING,
    STATUS_COLLECTING,
    STATUS_NO_RECENT_DATA,
    STATUS_SENSOR_MISSING,
]
STALE_SECONDS = 3600  # no new SOC or power value for an hour
# An idle battery (empty or full, standing still) sends the same SOC and power
# for hours; that is not a broken connection. Below this power it counts as idle.
IDLE_POWER_W = 50

STORAGE_VERSION = 1
TICK_SECONDS = 60
SAVE_DELAY_SECONDS = 600  # keep write load low; records are saved immediately
RECALC_SECONDS = 3600

SIGNAL_UPDATE = f"{DOMAIN}_update_{{}}"
SIGNAL_STATUS = f"{DOMAIN}_status_{{}}"
EVENT_SESSION = f"{DOMAIN}_session"
