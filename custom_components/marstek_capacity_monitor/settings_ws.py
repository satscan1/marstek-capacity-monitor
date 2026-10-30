"""The settings window of the card (0.5.5-rc3).

The gear on a card opens an own window in the house style instead of the
general forms of Home Assistant. These websocket commands give that window
what it shows and store what it changes, with the same checks as the
options flow (that flow stays, as a fallback).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import (
    CONF_BATTERY_ID,
    CONF_CELL_MAX_ENTITY,
    CONF_CELL_MIN_ENTITY,
    CONF_CELL_SENSITIVITY,
    CONF_CYCLE_COUNTER,
    CONF_CYCLE_EOL,
    CONF_CYCLE_LIFE,
    CONF_INITIAL_CYCLES,
    CONF_NAME,
    CONF_NOMINAL_KWH,
    CONF_NOTIFY,
    CONF_POWER_ENTITY,
    CONF_POWER_SIGN,
    CONF_PURCHASE_DATE,
    CONF_RED_PCT,
    CONF_RESERVE_KWH,
    CONF_SIDEBAR,
    CONF_SOC_ENTITY,
    CONF_SOC_SENSITIVITY,
    CONF_TEMP_MAX_ENTITY,
    CONF_TEMP_MIN_ENTITY,
    CONF_TOLERANCE_PCT,
    CONF_WARRANTY_YEARS,
    DEFAULTS,
    DOMAIN,
    HIDDEN_OPTIONS,
    RESTORE_MODES,
    SENSITIVITIES,
    SIGN_MODES,
)
from .discovery import find_candidates, looks_like_ac

# Number fields: (min, max, step). The same limits as the options form.
NUMBERS: dict[str, tuple[float, float, float]] = {
    CONF_NOMINAL_KWH: (0.1, 100, 0.01),
    CONF_RESERVE_KWH: (0, 50, 0.01),
    CONF_WARRANTY_YEARS: (1, 30, 0.5),
    CONF_CYCLE_LIFE: (100, 20000, 100),
    CONF_CYCLE_EOL: (1, 100, 1),
    CONF_INITIAL_CYCLES: (0, 20000, 0.1),
    CONF_RED_PCT: (1, 100, 1),
    CONF_TOLERANCE_PCT: (0, 25, 0.5),
}
CELL_SENSORS = (CONF_CELL_MAX_ENTITY, CONF_CELL_MIN_ENTITY, CONF_TEMP_MAX_ENTITY, CONF_TEMP_MIN_ENTITY)
BOOLS = (CONF_NOTIFY, CONF_SIDEBAR)
CHOICES = {
    CONF_POWER_SIGN: SIGN_MODES,
    CONF_SOC_SENSITIVITY: SENSITIVITIES,
    CONF_CELL_SENSITIVITY: SENSITIVITIES,
}
SETTINGS = (*NUMBERS, CONF_PURCHASE_DATE, *CHOICES, *BOOLS, *CELL_SENSORS)

_TEXTS: dict[str, dict[str, Any]] = {}


def _load_texts() -> None:
    """Labels and help of the fields, from the translations of the options
    form: one place for the texts, in all three languages."""
    for lang in ("nl", "de", "en"):
        path = Path(__file__).parent / "translations" / f"{lang}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        step = data["options"]["step"]["settings"]
        _TEXTS[lang] = {
            "label": step.get("data", {}),
            "help": step.get("data_description", {}),
            "errors": data["options"].get("error", {}),
            "restored": data["options"].get("abort", {}).get("restored", ""),
            "restore": data["options"]["step"].get("restore", {}).get("description", ""),
            "modes": data["selector"].get("restore_mode", {}).get("options", {}),
            "choices": {
                CONF_POWER_SIGN: data["selector"]["power_sign"]["options"],
                "sensitivity": data["selector"]["sensitivity"]["options"],
            },
        }


def _texts(lang: str) -> dict[str, Any]:
    return _TEXTS.get(lang) or _TEXTS.get("en", {})


def _entry(hass: HomeAssistant, entry_id: str):
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN:
        return None
    return entry


def _sensor(hass: HomeAssistant, entity_id: str | None) -> dict[str, Any] | None:
    """A sensor as the window shows it: name, value of now and entity id."""
    if not entity_id:
        return None
    st = hass.states.get(entity_id)
    if st is None:
        return {"id": entity_id, "name": entity_id, "value": None, "missing": True}
    unit = st.attributes.get("unit_of_measurement") or ""
    value = None if st.state in ("unknown", "unavailable") else f"{st.state} {unit}".strip()
    return {"id": entity_id, "name": st.attributes.get("friendly_name") or entity_id, "value": value}


def _current(entry) -> dict[str, Any]:
    merged = {**entry.data, **entry.options}
    out: dict[str, Any] = {}
    for key in SETTINGS:
        value = merged.get(key, DEFAULTS.get(key))
        if key in NUMBERS and value is not None:
            value = float(value)
        if key in BOOLS:
            value = bool(value)
        out[key] = value if value is not None else ("" if key in CELL_SENSORS or key == CONF_PURCHASE_DATE else None)
    return out


def _admin(connection) -> bool:
    return bool(connection.user and connection.user.is_admin)


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/settings", vol.Required("entry_id"): str, vol.Optional("lang"): str}
)
@websocket_api.require_admin
@callback
def ws_get(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    entry = _entry(hass, msg["entry_id"])
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Unknown battery")
        return
    soc, power = entry.data[CONF_SOC_ENTITY], entry.data[CONF_POWER_ENTITY]
    others = {
        e.data.get(CONF_SOC_ENTITY)
        for e in hass.config_entries.async_entries(DOMAIN)
        if e.entry_id != entry.entry_id
    }
    found = [
        {"name": c.name, "soc": _sensor(hass, c.soc_entity), "power": _sensor(hass, c.power_entity)}
        for c in find_candidates(hass, exclude_soc=others)
        if (c.soc_entity, c.power_entity) != (soc, power)
    ]
    values = _current(entry)
    connection.send_result(
        msg["id"],
        {
            "battery": entry.data.get(CONF_BATTERY_ID),
            "name": entry.data.get(CONF_NAME) or entry.title,
            "running": getattr(entry, "runtime_data", None) is not None,
            "sensors": {"soc": _sensor(hass, soc), "power": _sensor(hass, power)},
            "found": found,
            "values": values,
            "cells": {key: _sensor(hass, values.get(key)) for key in CELL_SENSORS},
            "numbers": {k: list(v) for k, v in NUMBERS.items()},
            "choices": {k: list(v) for k, v in CHOICES.items()},
            "texts": _texts(msg.get("lang") or (hass.config.language or "en")[:2]),
        },
    )


def validate(current: dict[str, Any], changes: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    """The new settings and the errors per field, as the options form checks."""
    values = {**current}
    errors: dict[str, str] = {}
    for key, raw in changes.items():
        if key not in SETTINGS:
            errors[key] = "unknown"
            continue
        if key in NUMBERS:
            low, high, _step = NUMBERS[key]
            try:
                number = float(str(raw).replace(",", "."))
            except ValueError:
                errors[key] = "not_a_number"
                continue
            if not low <= number <= high:
                errors[key] = "out_of_range"
                continue
            values[key] = number
        elif key in BOOLS:
            values[key] = bool(raw)
        elif key in CHOICES:
            if raw not in CHOICES[key]:
                errors[key] = "unknown"
                continue
            values[key] = raw
        elif key == CONF_PURCHASE_DATE:
            from datetime import date

            try:
                date.fromisoformat(str(raw))
            except ValueError:
                errors[key] = "not_a_date"
                continue
            values[key] = str(raw)
        else:  # optional sensors
            values[key] = str(raw or "")
    if CONF_RESERVE_KWH not in errors and values[CONF_RESERVE_KWH] >= values[CONF_NOMINAL_KWH]:
        errors[CONF_RESERVE_KWH] = "reserve_too_large"
    has_max, has_min = bool(values[CONF_CELL_MAX_ENTITY]), bool(values[CONF_CELL_MIN_ENTITY])
    if has_max != has_min:
        errors[CONF_CELL_MAX_ENTITY if not has_max else CONF_CELL_MIN_ENTITY] = "cells_both"
    elif has_max and values[CONF_CELL_MAX_ENTITY] == values[CONF_CELL_MIN_ENTITY]:
        errors[CONF_CELL_MIN_ENTITY] = "same_entity"
    return values, errors


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/settings/save", vol.Required("entry_id"): str, vol.Required("values"): dict}
)
@websocket_api.require_admin
@callback
def ws_save(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    entry = _entry(hass, msg["entry_id"])
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Unknown battery")
        return
    current = _current(entry)
    values, errors = validate(current, msg["values"])
    if errors:
        connection.send_result(msg["id"], {"errors": errors})
        return
    # Keep what the window does not show (counter, declined extras)
    kept = {k: v for k, v in entry.options.items() if k in HIDDEN_OPTIONS}
    # A changed start value is the user's own, no longer the counter's
    if float(values[CONF_INITIAL_CYCLES]) != float(current.get(CONF_INITIAL_CYCLES) or 0):
        kept[CONF_CYCLE_COUNTER] = ""
    if values != current:
        # Saving reloads the battery (update listener), as the form does
        hass.config_entries.async_update_entry(entry, options={**kept, **values})
    connection.send_result(msg["id"], {"errors": {}})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/sensors/save",
        vol.Required("entry_id"): str,
        vol.Required("soc"): str,
        vol.Required("power"): str,
        vol.Optional("restart", default=False): bool,
        vol.Optional("accept_ac", default=False): bool,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_sensors(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    """Another SOC / power pair, or start the measuring over. The
    measurements stay with the battery unless the user starts over."""
    entry = _entry(hass, msg["entry_id"])
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Unknown battery")
        return
    soc, power, restart = msg["soc"], msg["power"], msg["restart"]
    if soc == power:
        connection.send_result(msg["id"], {"error": "same_entity"})
        return
    if hass.states.get(soc) is None or hass.states.get(power) is None:
        connection.send_result(msg["id"], {"error": "not_found"})
        return
    changed = (soc, power) != (entry.data[CONF_SOC_ENTITY], entry.data[CONF_POWER_ENTITY])
    if changed and power != entry.data[CONF_POWER_ENTITY] and not msg["accept_ac"] and looks_like_ac(hass, power):
        connection.send_result(msg["id"], {"error": "looks_like_ac"})
        return
    monitor = getattr(entry, "runtime_data", None)
    if monitor is not None and (changed or restart):
        await monitor.async_sensors_changed(restart=restart)
    if changed:
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_SOC_ENTITY: soc, CONF_POWER_ENTITY: power}
        )
    connection.send_result(msg["id"], {"error": None, "changed": changed, "restarted": restart})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/restore",
        vol.Required("entry_id"): str,
        vol.Required("file_id"): str,
        vol.Required("mode"): vol.In(RESTORE_MODES),
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_restore(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    """Restore a back-up from the window (0.5.5): the file is uploaded first
    (file_upload, as the form does), then read and merged or replaced.
    A full back-up of the current data is always written first."""
    from homeassistant.components.file_upload import process_uploaded_file

    from .export import ExportError

    entry = _entry(hass, msg["entry_id"])
    monitor = getattr(entry, "runtime_data", None) if entry else None
    if monitor is None:
        connection.send_error(msg["id"], "not_found", "Unknown battery")
        return

    def _read() -> str:
        with process_uploaded_file(hass, msg["file_id"]) as path:
            return path.read_text(encoding="utf-8")

    try:
        text = await hass.async_add_executor_job(_read)
        done = await monitor.async_restore(text, msg["mode"])
    except ExportError:
        connection.send_result(msg["id"], {"error": "restore_invalid"})
        return
    except (OSError, UnicodeDecodeError, ValueError):
        connection.send_result(msg["id"], {"error": "restore_unreadable"})
        return
    connection.send_result(msg["id"], {"error": None, "records": done["records"], "full": done["full"]})


async def async_register(hass: HomeAssistant) -> None:
    if not _TEXTS:
        await hass.async_add_executor_job(_load_texts)
    websocket_api.async_register_command(hass, ws_get)
    websocket_api.async_register_command(hass, ws_save)
    websocket_api.async_register_command(hass, ws_sensors)
    websocket_api.async_register_command(hass, ws_restore)
