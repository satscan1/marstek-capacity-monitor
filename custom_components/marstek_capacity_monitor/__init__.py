"""Marstek Capacity Monitor.

Tracks the usable capacity of up to six home batteries, measured on the DC
side, against factory data and warranty terms.
"""

from __future__ import annotations

from pathlib import Path

import voluptuous as vol

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .const import DOMAIN
from .monitor import BatteryMonitor

PLATFORMS = [Platform.SENSOR]

SERVICE_RESET = "reset_measurements"
ATTR_ENTRY_ID = "config_entry_id"

type MonitorConfigEntry = ConfigEntry[BatteryMonitor]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
CARD_URL = f"/{DOMAIN}_frontend"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the integration's own card and dashboard, on every frontend page.

    No button-card and no manual resource needed: after installing, the cards
    are in the card picker and the dashboard is offered under
    Settings -> Dashboards -> Add dashboard (HA 2026.5 and later).
    """
    integration = await async_get_integration(hass, DOMAIN)
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(Path(__file__).parent / "frontend"), True)]
    )
    # ?v= so a browser loads the new file after an update (31-day cache)
    add_extra_js_url(hass, f"{CARD_URL}/marstek-capacity-card.js?v={integration.version}")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: MonitorConfigEntry) -> bool:
    monitor = BatteryMonitor(hass, entry)
    await monitor.async_start()
    entry.runtime_data = monitor
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))

    if not hass.services.has_service(DOMAIN, SERVICE_RESET):

        async def _reset(call: ServiceCall) -> None:
            target = hass.config_entries.async_get_entry(call.data[ATTR_ENTRY_ID])
            if target is None or target.domain != DOMAIN or not hasattr(
                target, "runtime_data"
            ):
                raise ServiceValidationError("Unknown battery")
            await target.runtime_data.async_reset()

        hass.services.async_register(
            DOMAIN,
            SERVICE_RESET,
            _reset,
            schema=vol.Schema({vol.Required(ATTR_ENTRY_ID): cv.string}),
        )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MonitorConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_stop()
    return unloaded


# Measurements are deliberately NOT deleted when a battery is removed: they
# may be needed as evidence for a warranty claim. The file stays in
# .storage/marstek_capacity_monitor.<entry_id>.


async def _async_reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
