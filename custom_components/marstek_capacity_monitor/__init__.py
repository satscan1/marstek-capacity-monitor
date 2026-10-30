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
from homeassistant.core import CoreState, Event, HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from homeassistant.helpers.http import KEY_HASS

from .const import BACKUP_URL, DOMAIN, KIND_CELLS, KIND_SOC, NOTIFY_ACTION_PREFIX, REPORT_URL
from .export import VARIANTS
from .dashboard import async_update_sidebar
from .monitor import BatteryMonitor

PLATFORMS = [Platform.SENSOR]

SERVICE_RESET = "reset_measurements"
SERVICE_DISMISS = "dismiss_advice"
SERVICE_DEMO = "demo"
ATTR_SCENARIO = "scenario"
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
    # The version that is installed now: the card compares it with its own and
    # offers a refresh when a page (phone app) still runs an older card.
    hass.data[f"{DOMAIN}_version"] = integration.version
    # Loaded while Home Assistant was already running (first install, when the
    # first battery is being added): pages that are open now do not have the
    # card yet (0.5.5-rc4). The first battery then says: refresh once.
    hass.data[f"{DOMAIN}_late"] = hass.state is CoreState.running
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

    async def _demo(call: ServiceCall) -> None:
        """Demo battery with one made-up situation (0.5.5): the real card,
        Repairs and phone messages follow. Your own batteries are untouched."""
        from .demo import DEMO_ID

        monitor = _find_monitor(hass, None, DEMO_ID)
        if monitor is None:
            await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": "demo"}, data=_demo_entry_data()
            )
            await hass.async_block_till_done()
            monitor = _find_monitor(hass, None, DEMO_ID)
        if monitor is None:
            raise ServiceValidationError("Demo battery could not be added")
        await monitor.async_demo(call.data[ATTR_SCENARIO])

    from .demo import SCENARIOS

    hass.services.async_register(
        DOMAIN,
        SERVICE_DEMO,
        _demo,
        schema=vol.Schema({vol.Required(ATTR_SCENARIO): vol.In(SCENARIOS)}),
    )

    hass.bus.async_listen("mobile_app_notification_action", _phone_action)
    # The settings window of the card (0.5.5-rc3)
    from .settings_ws import async_register as _register_settings

    await _register_settings(hass)
    hass.http.register_view(ReportView())
    hass.http.register_view(BackupView())
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


REFRESH_NOTICE = {
    "nl": ("Batterijcapaciteit: vernieuw de pagina",
           "De monitor is net toegevoegd. Vernieuw de pagina één keer om **Batterijcapaciteit** te openen: "
           "in een browser met **Ctrl+F5**, in de Home Assistant-app door de app helemaal te sluiten en opnieuw te openen. "
           "Anders zie je de melding *Timeout waiting for strategy element*. Dit is alleen de eerste keer nodig."),
    "de": ("Batteriekapazität: Seite neu laden",
           "Der Monitor wurde gerade hinzugefügt. Lade die Seite einmal neu, um **Batteriekapazität** zu öffnen: "
           "im Browser mit **Strg+F5**, in der Home-Assistant-App, indem du die App ganz schließt und neu öffnest. "
           "Sonst erscheint die Meldung *Timeout waiting for strategy element*. Das ist nur beim ersten Mal nötig."),
    "en": ("Battery capacity: refresh the page",
           "The monitor was just added. Refresh the page once to open **Battery capacity**: "
           "in a browser with **Ctrl+F5**, in the Home Assistant app by closing the app completely and opening it again. "
           "Otherwise you see the message *Timeout waiting for strategy element*. This is only needed the first time."),
}


def _refresh_notice(hass: HomeAssistant) -> None:
    from homeassistant.components import persistent_notification

    lang = (hass.config.language or "en")[:2]
    title, message = REFRESH_NOTICE.get(lang, REFRESH_NOTICE["en"])
    persistent_notification.async_create(
        hass, message, title=title, notification_id=f"{DOMAIN}_refresh"
    )


class BackupView(HomeAssistantView):
    """Make a back-up (0.5.5): a full back-up of one battery, kept in
    /config/marstek_capacity_monitor/backup/ and downloaded to the device.
    Only for an administrator; opened by the settings window with a
    short-lived signed link."""

    url = BACKUP_URL + "/{entry_id}"
    name = f"api:{DOMAIN}:backup"
    requires_auth = True

    async def get(self, request: web.Request, entry_id: str) -> web.Response:
        hass: HomeAssistant = request.app[KEY_HASS]
        user = request.get("hass_user")
        if user is None or not user.is_admin:
            return web.Response(status=403, text="Only an administrator can make a back-up.")
        monitor = _find_monitor(hass, entry_id, None)
        if monitor is None:
            return web.Response(status=404)
        path = await monitor.async_write_backup(None, "backup")
        html = await hass.async_add_executor_job(path.read_text, "utf-8")
        return web.Response(
            text=html,
            content_type="text/html",
            charset="utf-8",
            headers={"Content-Disposition": f'attachment; filename="{path.name}"'},
        )


def _demo_entry_data() -> dict:
    from .const import MODEL_E_V12, preset_for
    from .demo import DEMO_CELL_MAX, DEMO_CELL_MIN, DEMO_ID, DEMO_POWER, DEMO_SOC, DEMO_TEMP_MAX

    return {
        "battery_id": DEMO_ID,
        "name": "Demo",
        "soc_entity": DEMO_SOC,
        "power_entity": DEMO_POWER,
        "power_sign": "charge_positive",
        "model": MODEL_E_V12,
        "purchase_date": "2024-02-01",
        "cell_max_entity": DEMO_CELL_MAX,
        "cell_min_entity": DEMO_CELL_MIN,
        "temp_max_entity": DEMO_TEMP_MAX,
        **preset_for(MODEL_E_V12),
        "initial_cycles": 300,
    }


def _demo_inputs(hass: HomeAssistant) -> None:
    """Made-up input values of the demo battery: idle, half full."""
    from .demo import DEMO_CELL_MAX, DEMO_CELL_MIN, DEMO_POWER, DEMO_SOC, DEMO_TEMP_MAX

    hass.states.async_set(DEMO_SOC, 60, {"unit_of_measurement": "%", "friendly_name": "Demo SOC"})
    hass.states.async_set(DEMO_POWER, 0, {"unit_of_measurement": "W", "friendly_name": "Demo DC power"})
    hass.states.async_set(DEMO_CELL_MAX, 3.33, {"unit_of_measurement": "V"})
    hass.states.async_set(DEMO_CELL_MIN, 3.32, {"unit_of_measurement": "V"})
    hass.states.async_set(DEMO_TEMP_MAX, 16, {"unit_of_measurement": "°C"})


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
    if entry.data.get("battery_id") == "demo":
        _demo_inputs(hass)
    monitor = BatteryMonitor(hass, entry)
    monitor.app_version = str((await async_get_integration(hass, DOMAIN)).version)
    await monitor.async_start()
    entry.runtime_data = monitor
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    async_update_sidebar(hass)
    if hass.data.pop(f"{DOMAIN}_late", False):
        _refresh_notice(hass)

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
    """Battery removed: its messages under Repairs go, the menu item goes
    with the last battery, and the made-up inputs of the demo battery go."""
    from homeassistant.helpers import issue_registry as ir

    registry = ir.async_get(hass)
    battery = entry.data.get("battery_id") or ""
    for domain, issue_id in list(registry.issues):
        if domain == DOMAIN and entry.entry_id in issue_id:
            ir.async_delete_issue(hass, DOMAIN, issue_id)
    if battery == "demo":
        for entity_id in list(hass.states.async_entity_ids("sensor")):
            if entity_id.startswith("sensor.marstek_demo_input_"):
                hass.states.async_remove(entity_id)
    async_update_sidebar(hass)


# Measurements are deliberately NOT deleted when a battery is removed: they
# may be needed as evidence for a warranty claim. The file stays in
# .storage/marstek_capacity_monitor.<entry_id>.


async def _async_reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
