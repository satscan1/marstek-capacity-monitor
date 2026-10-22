"""Sensors found on the battery's device that the monitor does not use yet.

Two kinds:
- cell voltage (and temperature) sensors, for the cell balance check;
- the battery's own counter of all energy it ever discharged, to estimate the
  cycles done before the monitor existed.

That counter is the battery's own, measured on the AC side (after conversion
losses). It is an estimate, less exact than the cycles the monitor counts
itself from the DC power. The texts say so.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_CELL_MAX_ENTITY,
    CONF_CELL_MIN_ENTITY,
    CONF_INITIAL_CYCLES,
    CONF_NOMINAL_KWH,
    CONF_RESERVE_KWH,
    CONF_SOC_ENTITY,
    CONF_TEMP_MAX_ENTITY,
    CONF_TEMP_MIN_ENTITY,
    DEFAULTS,
)
from .discovery import counter_kwh, find_cell_sensors, find_discharge_counter


def lang_of(language: str | None) -> str:
    code = (language or "en")[:2]
    return code if code in ("nl", "de") else "en"


def _num(value: float, lang: str, digits: int = 1) -> str:
    text = f"{value:,.{digits}f}"
    if lang in ("nl", "de"):
        text = text.replace(",", "_").replace(".", ",").replace("_", ".")
    return text


def start_cycles(kwh: float, usable_kwh: float, counted_kwh: float = 0.0) -> float:
    """Cycles before the monitor: (counter - what the monitor already
    counted itself) / usable capacity."""
    if usable_kwh <= 0:
        return 0.0
    return round(max(0.0, (kwh - counted_kwh) / usable_kwh), 1)


# Shown in the add-battery flow and in the Repairs message.
COUNTER_NOTE = {
    "nl": "Cycli vóór de monitoring: ongeveer {cycles}, uitgerekend met de teller "
    "totaal ontladen van de batterij ({entity}, {kwh} kWh) gedeeld door de bruikbare "
    "capaciteit. Die teller meet aan de AC-kant: dit is een schatting, minder precies dan "
    "de cycli die deze monitor zelf aan de DC-kant telt. Aanpassen kan later via Configureren.",
    "en": "Cycles before monitoring: about {cycles}, worked out from the battery's "
    "total discharged counter ({entity}, {kwh} kWh) divided by the usable capacity. That "
    "counter measures on the AC side: this is an estimate, less exact than the cycles this "
    "monitor counts itself on the DC side. You can change it later under Configure.",
    "de": "Zyklen vor der Überwachung: etwa {cycles}, berechnet aus dem Zähler "
    "Gesamtentladung der Batterie ({entity}, {kwh} kWh) geteilt durch die nutzbare "
    "Kapazität. Dieser Zähler misst auf der AC-Seite: eine Schätzung, ungenauer als die "
    "Zyklen, die dieser Monitor selbst auf der DC-Seite zählt. Ändern kannst du das später "
    "unter Konfigurieren.",
}

# Shown when adding a battery (model step); the number follows from the model.
FLOW_NOTE = {
    "nl": "Cycli vóór de monitoring worden geschat met de teller totaal ontladen van de "
    "batterij ({entity}, {kwh} kWh) gedeeld door de bruikbare capaciteit. Die teller meet "
    "aan de AC-kant: een schatting, minder precies dan de cycli die deze monitor zelf aan de "
    "DC-kant telt. Aanpassen kan later via Configureren.",
    "en": "Cycles before monitoring are estimated from the battery's total discharged "
    "counter ({entity}, {kwh} kWh) divided by the usable capacity. That counter measures on "
    "the AC side: an estimate, less exact than the cycles this monitor counts itself on the "
    "DC side. You can change it later under Configure.",
    "de": "Die Zyklen vor der Überwachung werden aus dem Zähler Gesamtentladung der Batterie "
    "({entity}, {kwh} kWh) geteilt durch die nutzbare Kapazität geschätzt. Dieser Zähler misst "
    "auf der AC-Seite: eine Schätzung, ungenauer als die Zyklen, die dieser Monitor selbst auf "
    "der DC-Seite zählt. Ändern kannst du das später unter Konfigurieren.",
}

CELLS_NOTE = {
    "nl": "Celspanning hoogste en laagste: {max} en {min}. Daarmee volgt de monitor de "
    "celbalans (knopje Cellen op de kaart).",
    "en": "Highest and lowest cell voltage: {max} and {min}. With these the monitor follows "
    "the cell balance (Cells button on the card).",
    "de": "Höchste und niedrigste Zellspannung: {max} und {min}. Damit verfolgt der Monitor "
    "die Zellbalance (Taste Zellen auf der Karte).",
}

INTRO = {
    "nl": "Op het apparaat van {name} staan sensoren die de monitor nog niet gebruikt. "
    "Vink aan wat je wilt toevoegen en kies Verzenden.",
    "en": "The device of {name} has sensors the monitor does not use yet. Tick what you "
    "want to add and press Submit.",
    "de": "Das Gerät von {name} hat Sensoren, die der Monitor noch nicht nutzt. Hake an, "
    "was du hinzufügen willst, und wähle Absenden.",
}


def counter_note(
    language: str | None, entity: str, kwh: float, cycles: float
) -> str:
    lang = lang_of(language)
    return COUNTER_NOTE[lang].format(
        cycles=_num(cycles, lang, 0), entity=entity, kwh=_num(kwh, lang)
    )


def setting(entry: ConfigEntry, key: str) -> Any:
    if key in entry.options:
        return entry.options[key]
    if key in entry.data:
        return entry.data[key]
    return DEFAULTS.get(key)


def find_extras(
    hass: HomeAssistant,
    entry: ConfigEntry,
    counted_kwh: float = 0.0,
    declined: list[str] | None = None,
) -> dict[str, Any]:
    """What can be added to this battery. Keys: cells (dict of option values),
    counter (entity), kwh, cycles."""
    soc = entry.data[CONF_SOC_ENTITY]
    declined = declined or []
    found: dict[str, Any] = {}
    if "cells" not in declined and not setting(entry, CONF_CELL_MAX_ENTITY) and not setting(entry, CONF_CELL_MIN_ENTITY):
        cells = find_cell_sensors(hass, soc)
        if "max" in cells and "min" in cells:
            values = {CONF_CELL_MAX_ENTITY: cells["max"], CONF_CELL_MIN_ENTITY: cells["min"]}
            if "temp_max" in cells and not setting(entry, CONF_TEMP_MAX_ENTITY):
                values[CONF_TEMP_MAX_ENTITY] = cells["temp_max"]
            if "temp_min" in cells and not setting(entry, CONF_TEMP_MIN_ENTITY):
                values[CONF_TEMP_MIN_ENTITY] = cells["temp_min"]
            found["cells"] = values
    # Only when no start value was entered: never overwrite the user's own.
    if "cycles" not in declined and not float(setting(entry, CONF_INITIAL_CYCLES) or 0):
        counter = find_discharge_counter(hass, soc)
        kwh = counter_kwh(hass, counter)
        usable = float(setting(entry, CONF_NOMINAL_KWH)) - float(
            setting(entry, CONF_RESERVE_KWH)
        )
        if counter and kwh:
            cycles = start_cycles(kwh, usable, counted_kwh)
            if cycles >= 1:
                found.update(counter=counter, kwh=kwh, cycles=cycles)
    return found


def describe(language: str | None, name: str, found: dict[str, Any]) -> str:
    """The text of the Repairs message."""
    lang = lang_of(language)
    parts = [INTRO[lang].format(name=name)]
    if cells := found.get("cells"):
        parts.append(
            "- " + CELLS_NOTE[lang].format(
                max=cells[CONF_CELL_MAX_ENTITY], min=cells[CONF_CELL_MIN_ENTITY]
            )
        )
    if found.get("counter"):
        parts.append(
            "- " + counter_note(language, found["counter"], found["kwh"], found["cycles"])
        )
    return "\n\n".join(parts)
