"""The integration's own dashboard in the sidebar (0.5.1).

After installing and adding the first battery, "Battery capacity" (NL
"Batterijcapaciteit") appears in the sidebar by itself. The dashboard is the
strategy `custom:marstek-capacity`, so it finds every battery of the monitor and
arranges 1 to 6 batteries without the user doing anything.

The dashboard is not stored anywhere: it is registered while Home Assistant
runs, read-only (like a YAML dashboard). Anyone who wants to change it can make
their own dashboard from the same strategy (Add dashboard -> community).

Off for one battery under Configure = no menu item.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components import frontend
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.json import json_bytes, json_fragment

from .const import (
    CONF_SIDEBAR,
    DASHBOARD_ICON,
    DASHBOARD_TITLE,
    DASHBOARD_URL,
    DEFAULTS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

try:  # Home Assistant internals; guarded so a change never breaks the monitor
    from homeassistant.components.lovelace.const import LOVELACE_DATA
    from homeassistant.components.lovelace.dashboard import LovelaceConfig
except ImportError:  # pragma: no cover - older or changed Home Assistant
    LOVELACE_DATA = None
    LovelaceConfig = object  # type: ignore[assignment,misc]

MODE = "yaml"  # read-only in the frontend: no edit pencil, no "take control"
STRATEGY = {"strategy": {"type": "custom:marstek-capacity"}}


def dashboard_title(language: str | None) -> str:
    lang = (language or "en")[:2].lower()
    return DASHBOARD_TITLE.get(lang, DASHBOARD_TITLE["en"])


def sidebar_wanted(hass: HomeAssistant) -> bool:
    """On when there is a battery and none of the batteries switched it off."""
    entries = [
        e for e in hass.config_entries.async_entries(DOMAIN) if not e.disabled_by
    ]
    if not entries:
        return False
    return all(
        bool({**e.data, **e.options}.get(CONF_SIDEBAR, DEFAULTS[CONF_SIDEBAR]))
        for e in entries
    )


class StrategyDashboard(LovelaceConfig):  # type: ignore[misc,valid-type]
    """A dashboard whose whole config is the integration's strategy."""

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(hass, DASHBOARD_URL, {"mode": MODE})
        self._json = json_fragment(json_bytes(STRATEGY))

    @property
    def mode(self) -> str:
        return MODE

    async def async_get_info(self) -> dict[str, Any]:
        return {"mode": MODE}

    async def async_load(self, force: bool) -> dict[str, Any]:
        return dict(STRATEGY)

    async def async_json(self, force: bool) -> Any:
        return self._json


@callback
def async_update_sidebar(hass: HomeAssistant) -> None:
    """Show or remove the menu item; never let it break the monitor itself."""
    try:
        _async_update_sidebar(hass)
    except Exception:  # noqa: BLE001 - Home Assistant internals may change
        _LOGGER.warning("Could not update the menu item in the sidebar", exc_info=True)


@callback
def _async_update_sidebar(hass: HomeAssistant) -> None:
    """Show or remove the menu item to match the batteries' settings."""
    if LOVELACE_DATA is None or LOVELACE_DATA not in hass.data:
        _LOGGER.debug("Lovelace not available; no menu item")
        return
    dashboards = hass.data[LOVELACE_DATA].dashboards
    panels = hass.data.get(frontend.DATA_PANELS, {})
    ours = isinstance(dashboards.get(DASHBOARD_URL), StrategyDashboard)

    if not sidebar_wanted(hass):
        if ours:
            dashboards.pop(DASHBOARD_URL, None)
            frontend.async_remove_panel(hass, DASHBOARD_URL, warn_if_unknown=False)
        return

    if ours:
        return
    if DASHBOARD_URL in dashboards or DASHBOARD_URL in panels:
        # Someone made a dashboard with this address themselves: leave it alone
        _LOGGER.info("A dashboard /%s already exists; no menu item added", DASHBOARD_URL)
        return
    dashboards[DASHBOARD_URL] = StrategyDashboard(hass)
    frontend.async_register_built_in_panel(
        hass,
        "lovelace",
        sidebar_title=dashboard_title(hass.config.language),
        sidebar_icon=DASHBOARD_ICON,
        frontend_url_path=DASHBOARD_URL,
        config={"mode": MODE},
        require_admin=False,
    )
