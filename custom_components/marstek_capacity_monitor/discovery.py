"""Find batteries that are already in Home Assistant.

Every common Marstek route (ESPHome over RS485, Modbus TCP via a bridge or the
built-in LAN port of the E v3 / A / D, community integrations) exposes the
same two values: the state of charge and the DC battery power. Only the names
differ. This module looks for those two sensors per device and proposes them,
so users do not have to create new sensors.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from homeassistant.const import PERCENTAGE, UnitOfPower
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import DOMAIN

SOC_RE = re.compile(r"state_of_charge|(^|_)soc($|_)|battery_level|battery_percent")
POWER_RE = re.compile(r"battery_power|batt_power|bat_power|battery_dc_power|dc_power")
# Names that point to settings or limits rather than measurements
EXCLUDE_RE = re.compile(
    r"cutoff|cut_off|limit|min_|_min|max_|_max|target|reserve|setpoint|set_|"
    r"threshold|backup|rated|forcible|force_|minimum|maximum"
)
# Names that point to the AC / grid side instead of the battery (DC) side
AC_RE = re.compile(r"(^|_)ac($|_)|grid|(^|_)net($|_)|inverter|p1|meter|socket|plug")

POWER_UNITS = {UnitOfPower.WATT, UnitOfPower.KILO_WATT}


@dataclass
class Candidate:
    """One proposed battery."""

    name: str
    soc_entity: str
    power_entity: str


def _text(state: State, entry: er.RegistryEntry | None) -> str:
    parts = [state.entity_id.split(".", 1)[1]]
    if entry is not None:
        parts += [entry.original_name or "", entry.name or ""]
    parts.append(str(state.attributes.get("friendly_name", "")))
    return re.sub(r"[^a-z0-9]+", "_", " ".join(parts).lower())


def is_soc(state: State, entry: er.RegistryEntry | None = None) -> bool:
    if state.attributes.get("unit_of_measurement") != PERCENTAGE:
        return False
    text = _text(state, entry)
    if EXCLUDE_RE.search(text):
        return False
    return state.attributes.get("device_class") == "battery" or bool(SOC_RE.search(text))


def is_battery_power(state: State, entry: er.RegistryEntry | None = None) -> bool:
    if state.attributes.get("unit_of_measurement") not in POWER_UNITS:
        return False
    text = _text(state, entry)
    if EXCLUDE_RE.search(text) or AC_RE.search(text):
        return False
    return bool(POWER_RE.search(text))


def looks_like_ac(hass: HomeAssistant, entity_id: str) -> bool:
    """True when a chosen power sensor looks like the AC / grid side."""
    state = hass.states.get(entity_id)
    if state is None:
        return False
    entry = er.async_get(hass).async_get(entity_id)
    text = _text(state, entry)
    return bool(AC_RE.search(text)) and not POWER_RE.search(text)


def _prefix(entity_id: str, pattern: re.Pattern[str]) -> str:
    """Object id up to the matched keyword, e.g.
    venus_veranda_marstek_battery_power -> venus_veranda_marstek_."""
    obj = entity_id.split(".", 1)[1]
    m = pattern.search(obj)
    head = obj[: m.start()] if m else obj
    return re.sub(r"(battery_?|batt_?|bat_?)$", "", head)


def _score_soc(entity_id: str) -> int:
    return 2 if "state_of_charge" in entity_id else 1 if "soc" in entity_id else 0


def find_candidates(
    hass: HomeAssistant, exclude_soc: set[str] | None = None
) -> list[Candidate]:
    """Pairs of (SOC, DC battery power) that belong to the same battery."""
    exclude_soc = exclude_soc or set()
    ent_reg = er.async_get(hass)
    dev_reg = dr.async_get(hass)

    socs: list[tuple[State, er.RegistryEntry | None]] = []
    powers: list[tuple[State, er.RegistryEntry | None]] = []
    for state in hass.states.async_all("sensor"):
        entry = ent_reg.async_get(state.entity_id)
        if entry is not None and entry.platform == DOMAIN:
            continue
        if is_soc(state, entry) and state.entity_id not in exclude_soc:
            socs.append((state, entry))
        elif is_battery_power(state, entry):
            powers.append((state, entry))

    found: list[Candidate] = []
    used_power: set[str] = set()

    # 1. Same device in the device registry
    for soc, soc_entry in sorted(socs, key=lambda x: -_score_soc(x[0].entity_id)):
        dev_id = soc_entry.device_id if soc_entry else None
        match = None
        if dev_id:
            match = next(
                (
                    p
                    for p, pe in powers
                    if pe is not None
                    and pe.device_id == dev_id
                    and p.entity_id not in used_power
                ),
                None,
            )
        # 2. Fallback: same name prefix (template / YAML sensors, split devices)
        if match is None:
            pre = _prefix(soc.entity_id, SOC_RE)
            match = next(
                (
                    p
                    for p, _ in powers
                    if p.entity_id not in used_power
                    and pre
                    and _prefix(p.entity_id, POWER_RE) == pre
                ),
                None,
            )
        if match is None:
            continue
        used_power.add(match.entity_id)
        name = None
        if dev_id and (device := dev_reg.async_get(dev_id)):
            name = device.name_by_user or device.name
        if not name:
            name = _prefix(soc.entity_id, SOC_RE).strip("_").replace("_", " ") or (
                soc.entity_id
            )
        found.append(Candidate(name, soc.entity_id, match.entity_id))

    # One proposal per SOC sensor is enough; keep a stable order.
    unique: dict[str, Candidate] = {}
    for cand in found:
        unique.setdefault(cand.power_entity, cand)
    return sorted(unique.values(), key=lambda c: c.name.lower())
