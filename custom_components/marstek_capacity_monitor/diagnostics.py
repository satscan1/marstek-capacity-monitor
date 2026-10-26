"""Diagnostics (0.5.5): Settings -> Devices & services -> the monitor -> ⋮ ->
Download diagnostics. The same export as the back-up, so a report on GitHub
shows what the monitor saw and decided: app version, settings, every swing
with the reason it did or did not count, the SOC events and the status."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import MonitorConfigEntry

# The battery's own name may be personal ("Garage Jansen"); the rest is not.
TO_REDACT = {"name", "title"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: MonitorConfigEntry
) -> dict[str, Any]:
    monitor = entry.runtime_data
    export = monitor.export("full")
    export["variant"] = "diagnostics"
    return {
        "entry": async_redact_data({"title": entry.title, "data": dict(entry.data), "options": dict(entry.options)}, TO_REDACT),
        "status": monitor.status,
        "export": async_redact_data(export, TO_REDACT),
    }
