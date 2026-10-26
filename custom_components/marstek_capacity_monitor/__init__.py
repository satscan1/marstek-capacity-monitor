"""Marstek Capacity Monitor.

Tracks the usable capacity of up to six home batteries, measured on the DC
side, against factory data and warranty terms.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import voluptuous as vol

from homeassistant.components.frontend import add_extra_js_url
from aiohttp import web

from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import Event, HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from homeassistant.helpers.http import KEY_HASS

from .const import DOMAIN, KIND_CELLS, KIND_SOC, NOTIFY_ACTION_PREFIX, REPORT_URL
from .export import VARIANTS
from .dashboard import async_update_sidebar
from .monitor import BatteryMonitor

PLATFORMS = [Platform.SENSOR]

SERVICE_RESET = "reset_measurements"
SERVICE_DISMISS = "dismiss_advice"
ATTR_ENTRY_ID = "config_entry_id"
ATTR_BATTERY = "battery"
ATTR_KIND = "kind"

type MonitorConfigEntry = ConfigEntry[BatteryMonitor]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
CARD_URL = f"/{DOMAIN}_frontend"


def _fingerprint(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()[:8]


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
    # ?v= so a browser loads the new file after an update (31-day cache).
    # Version plus a short fingerprint of the file: a test version (rc) with
    # the same version number also gets a new address.
    card = Path(__file__).parent / "frontend" / "marstek-capacity-card.js"
    tag = await hass.async_add_executor_job(_fingerprint, card)
    add_extra_js_url(hass, f"{CARD_URL}/marstek-capacity-card.js?v={integration.version}-{tag}")

    async def _dismiss(call: ServiceCall) -> None:
        """Dismiss a "let op" or advice once (the button on the card)."""
        monitor = _find_monitor(
            hass, call.data.get(ATTR_ENTRY_ID), call.data.get(ATTR_BATTERY)
        )
        if monitor is None:
            raise ServiceValidationError("Unknown battery")
        await monitor.async_dismiss(call.data[ATTR_KIND])

    hass.services.async_register(
        DOMAIN,
        SERVICE_DISMISS,
        _dismiss,
        schema=vol.Schema(
            {
                vol.Optional(ATTR_ENTRY_ID): cv.string,
                vol.Optional(ATTR_BATTERY): cv.string,
                vol.Required(ATTR_KIND): vol.In([KIND_SOC, KIND_CELLS]),
            }
        ),
    )

    async def _phone_action(event: Event) -> None:
        """"Dismiss" pressed in the message on the phone (Companion app)."""
        parts = str(event.data.get("action", "")).split("|")
        if len(parts) != 4 or parts[0] != NOTIFY_ACTION_PREFIX:
            return
        monitor = _find_monitor(hass, parts[1], None)
        if monitor is not None:
            await monitor.async_dismiss(parts[2], float(parts[3]))

    hass.bus.async_listen("mobile_app_notification_action", _phone_action)
    hass.http.register_view(ReportView())
    return True


class ReportView(HomeAssistantView):
    """The report of one battery (0.5.5): full back-up, anonymous to share,
    or for Marstek. Behind the login of Home Assistant (the card opens it
    with a short-lived signed link), never in the public www folder."""

    url = REPORT_URL + "/{entry_id}/{variant}"
    name = f"api:{DOMAIN}:report"
    requires_auth = True

    async def get(self, request: web.Request, entry_id: str, variant: str) -> web.Response:
        hass: HomeAssistant = request.app[KEY_HASS]
        if variant not in VARIANTS:
            return web.Response(status=404)
        user = request.get("hass_user")
        if variant == "full" and (user is None or not user.is_admin):
            return web.Response(status=403, text="Only an administrator can make a full back-up.")
        monitor = _find_monitor(hass, entry_id, None)
        if monitor is None:
            return web.Response(status=404)
        html = monitor.report_html(variant)
        return web.Response(text=html, content_type="text/html", charset="utf-8")


def _find_monitor(
    hass: HomeAssistant, entry_id: str | None, battery: str | None
) -> BatteryMonitor | None:
    for entry in hass.config_entries.async_entries(DOMAIN):
        monitor = getattr(entry, "runtime_data", None)
        if not isinstance(monitor, BatteryMonitor):
            continue
        if entry.entry_id == entry_id or (battery and entry.data.get("battery_id") == battery):
            return monitor
    return None


async def async_setup_entry(hass: HomeAssistant, entry: MonitorConfigEntry) -> bool:
    monitor = BatteryMonitor(hass, entry)
    monitor.app_version = str((await async_get_integration(hass, DOMAIN)).version)
    await monitor.async_start()
    entry.runtime_data = monitor
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    async_update_sidebar(hass)

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
        async_update_sidebar(hass)
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Last battery removed: the menu item goes too."""
    async_update_sidebar(hass)


# Measurements are deliberately NOT deleted when a battery is removed: they
# may be needed as evidence for a warranty claim. The file stays in
# .storage/marstek_capacity_monitor.<entry_id>.


async def _async_reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
