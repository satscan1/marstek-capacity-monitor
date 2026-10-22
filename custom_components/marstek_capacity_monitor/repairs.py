"""Repairs: add sensors that were found on the battery's device."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_CYCLE_COUNTER, CONF_EXTRAS_DECLINED, CONF_INITIAL_CYCLES
from .extras import describe, find_extras

ADD_CELLS = "add_cells"
ADD_CYCLES = "add_cycles"


class ExtrasFlow(RepairsFlow):
    """Tick what to add; nothing ticked = do not offer it again."""

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        # The first step gets the issue data, not a form: go to the form
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        entry = self.hass.config_entries.async_get_entry(self._entry_id)
        if entry is None:
            return self.async_abort(reason="battery_gone")
        monitor = getattr(entry, "runtime_data", None)
        counted = monitor.tracker.cumulative_discharge_kwh if monitor else 0.0
        found = find_extras(
            self.hass, entry, counted, entry.options.get(CONF_EXTRAS_DECLINED, [])
        )
        if not found:
            return self.async_create_entry(data={})

        if user_input is not None:
            options = dict(entry.options)
            declined = list(options.get(CONF_EXTRAS_DECLINED, []))
            if found.get("cells"):
                if user_input.get(ADD_CELLS):
                    options.update(found["cells"])
                else:
                    declined.append("cells")
            if found.get("counter"):
                if user_input.get(ADD_CYCLES):
                    options[CONF_INITIAL_CYCLES] = found["cycles"]
                    options[CONF_CYCLE_COUNTER] = found["counter"]
                else:
                    declined.append("cycles")
            if declined:
                options[CONF_EXTRAS_DECLINED] = sorted(set(declined))
            # The update listener reloads the battery with the new settings
            self.hass.config_entries.async_update_entry(entry, options=options)
            return self.async_create_entry(data={})

        fields: dict[Any, Any] = {}
        if found.get("cells"):
            fields[vol.Required(ADD_CELLS, default=True)] = bool
        if found.get("counter"):
            fields[vol.Required(ADD_CYCLES, default=True)] = bool
        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema(fields),
            description_placeholders={
                "name": entry.title,
                "found": describe(self.hass.config.language, entry.title, found),
            },
        )


async def async_create_fix_flow(
    hass: HomeAssistant, issue_id: str, data: dict[str, Any] | None
) -> RepairsFlow:
    """Called by Home Assistant when the user opens a fixable message."""
    return ExtrasFlow((data or {}).get("entry_id", ""))

