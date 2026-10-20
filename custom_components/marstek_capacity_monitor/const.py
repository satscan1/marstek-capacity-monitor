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

STORAGE_VERSION = 1
TICK_SECONDS = 60
SAVE_DELAY_SECONDS = 600  # keep write load low; records are saved immediately
RECALC_SECONDS = 3600

SIGNAL_UPDATE = f"{DOMAIN}_update_{{}}"
EVENT_SESSION = f"{DOMAIN}_session"
