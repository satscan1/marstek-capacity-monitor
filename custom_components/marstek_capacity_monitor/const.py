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
# Battery counter "total discharged energy" the start value came from (AC side)
CONF_CYCLE_COUNTER = "cycle_counter"
# Found sensors the user chose not to add (Repairs): not offered again
CONF_EXTRAS_DECLINED = "extras_declined"
# Options the options form does not show but must keep
HIDDEN_OPTIONS = (CONF_CYCLE_COUNTER, CONF_EXTRAS_DECLINED)
EXTRAS_RECHECK_S = 600

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
MODEL_C = "venus_c"
MODEL_E_V3 = "venus_e_v3"
MODEL_E_V4 = "venus_e_v4"
MODEL_E_MAX = "venus_e_max"
MODEL_E_PRO = "venus_e_pro"
MODEL_D = "venus_d"
MODEL_OTHER = "other"
MODELS = [
    MODEL_E_V12,
    MODEL_C,
    MODEL_E_V3,
    MODEL_E_V4,
    MODEL_E_MAX,
    MODEL_E_PRO,
    MODEL_D,
    MODEL_OTHER,
]

# Sources: docs/05-supported-batteries.md (checked 20-10-2026).
# Where sources disagree the most cautious value is used.
_SPEC_LINE = {CONF_CYCLE_LIFE: 6000.0, CONF_CYCLE_EOL: 80.0, CONF_WARRANTY_YEARS: 10.0}
# New generation (2026, 314 Ah LFP cells): > 10,000 cycles at 25 °C. Marstek does
# not state the capacity after those cycles for these models; 80 % is assumed,
# as stated for the Venus E Mini (same cells). Change it under Configure.
_SPEC_LINE_10K = {CONF_CYCLE_LIFE: 10000.0, CONF_CYCLE_EOL: 80.0, CONF_WARRANTY_YEARS: 10.0}
MODEL_PRESETS: dict[str, dict[str, float]] = {
    # Venus E datasheet: 5.12 kWh, 90 % DoD, > 6000 cycles
    MODEL_E_V12: {CONF_NOMINAL_KWH: 5.12, CONF_RESERVE_KWH: 0.51, **_SPEC_LINE},
    # Venus C: half a Venus E. Marstek (Venus C/E page): 2.56 kWh, > 6000 cycles,
    # 10 years; 90 % DoD from a seller's datasheet (sun.store). Same Modbus
    # registers as the Venus E v1/v2 ("generation 2", evcc). 80 % after 6000
    # cycles assumed, as for the Venus E.
    MODEL_C: {CONF_NOMINAL_KWH: 2.56, CONF_RESERVE_KWH: 0.256, **_SPEC_LINE},
    # Venus E 3.0 manual: 5.12 kWh, 90 % DoD, > 6000 cycles
    MODEL_E_V3: {CONF_NOMINAL_KWH: 5.12, CONF_RESERVE_KWH: 0.51, **_SPEC_LINE},
    # Venus D product page: 2.56 kWh per unit, calculated with 90 % DoD.
    # Values are per pack and multiplied by the number of packs.
    MODEL_D: {CONF_NOMINAL_KWH: 2.56, CONF_RESERVE_KWH: 0.256, **_SPEC_LINE},
    # Venus E 4.0 brochure: 5024 Wh (314 Ah x 5S, 16 V), DoD 88 %
    MODEL_E_V4: {CONF_NOMINAL_KWH: 5.024, CONF_RESERVE_KWH: 0.603, **_SPEC_LINE_10K},
    # Venus E Max brochure: 10.048 kWh (314 Ah x 10S, 32 V), DoD 90 %
    MODEL_E_MAX: {CONF_NOMINAL_KWH: 10.048, CONF_RESERVE_KWH: 1.005, **_SPEC_LINE_10K},
    # Venus E Pro brochure (EU): 2.08 kWh per pack (41.6 V, 13S), DoD 90 %,
    # base unit + 0-5 extra packs. Per pack, multiplied by the number of packs.
    MODEL_E_PRO: {CONF_NOMINAL_KWH: 2.08, CONF_RESERVE_KWH: 0.208, **_SPEC_LINE_10K},
}
MAX_PACKS = 6
PACK_MODELS = (MODEL_D, MODEL_E_PRO)

# UPS mode (keeps the battery full while there is grid), used in the advice
# text for cell calibration. True: Marstek describes it; None: unknown or
# depends on the firmware (the text then also gives the alternative).
MODEL_UPS: dict[str, bool | None] = {
    MODEL_E_V3: True,
    MODEL_E_V12: None,  # a Homey app tested with a v2.0 has a card for it
}


def preset_for(model: str, packs: int = 1) -> dict[str, float]:
    """Factory data for a model; empty for 'other'."""
    preset = dict(MODEL_PRESETS.get(model, {}))
    if model in PACK_MODELS and preset:
        packs = max(1, min(int(packs or 1), MAX_PACKS))
        preset[CONF_NOMINAL_KWH] = round(preset[CONF_NOMINAL_KWH] * packs, 2)
        preset[CONF_RESERVE_KWH] = round(preset[CONF_RESERVE_KWH] * packs, 2)
    return preset


# Notifications (0.5): "let op" and advice for SOC drift and cell calibration,
# as a message on the phone and under Settings -> Repairs. On by default.
CONF_NOTIFY = "notify"
DEFAULTS[CONF_NOTIFY] = True
EVENT_ADVICE = "marstek_capacity_monitor_advice"
NOTIFY_ACTION_PREFIX = "MCM_DISMISS"
KIND_SOC = "soc"
KIND_CELLS = "cells"

# How sensitive the SOC drift and cell calibration checks are (0.5):
# off = only shown on the card, never "let op" or advice.
CONF_SOC_SENSITIVITY = "soc_sensitivity"
CONF_CELL_SENSITIVITY = "cell_sensitivity"
SENSITIVITIES = ["off", "relaxed", "normal", "strict"]
DEFAULTS[CONF_SOC_SENSITIVITY] = "normal"
DEFAULTS[CONF_CELL_SENSITIVITY] = "normal"
# SOC: an occurrence is a deviation of at least this many percent
SOC_EVENT_PCT = {"relaxed": 8.0, "normal": 5.0, "strict": 3.0, "off": 5.0}
# Cells: an occurrence is a spread of at least this times the own normal value
CELL_FACTORS = {"relaxed": 3.0, "normal": 2.0, "strict": 1.5, "off": 2.0}

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

# No home battery charges or discharges this fast. A value above it is a
# sensor with the wrong unit (W shown as kW) or a self-made sensor that
# multiplies mA or mV: ignored, and reported under Repairs.
MAX_PLAUSIBLE_POWER_W = 25000
# The Repairs message goes away after this long without such a value.
IMPLAUSIBLE_CLEAR_S = 24 * 3600

STORAGE_VERSION = 1
TICK_SECONDS = 60
SAVE_DELAY_SECONDS = 600  # keep write load low; records are saved immediately
RECALC_SECONDS = 3600

SIGNAL_UPDATE = f"{DOMAIN}_update_{{}}"
SIGNAL_STATUS = f"{DOMAIN}_status_{{}}"
EVENT_SESSION = f"{DOMAIN}_session"


# Sidebar (0.5.1): the integration puts its own dashboard in the sidebar, with
# all batteries in it. On by default; off for one battery = no menu item.
CONF_SIDEBAR = "sidebar"
DEFAULTS[CONF_SIDEBAR] = True
DASHBOARD_URL = "marstek-capacity"
DASHBOARD_ICON = "mdi:home-battery"
DASHBOARD_TITLE = {"nl": "Batterijcapaciteit", "de": "Batteriekapazität", "en": "Battery capacity"}
