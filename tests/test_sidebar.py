"""0.5.1: the integration's own dashboard in the sidebar."""

import pytest

from homeassistant.components.frontend import DATA_PANELS
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.marstek_capacity_monitor.const import DASHBOARD_URL

from .test_integration import POWER, SOC, _entry


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


async def _setup(hass: HomeAssistant, entry) -> None:
    hass.states.async_set(SOC, 50, {"unit_of_measurement": "%"})
    hass.states.async_set(POWER, 0, {"unit_of_measurement": "W"})
    assert await async_setup_component(hass, "lovelace", {})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_menu_item_appears_with_first_battery(hass: HomeAssistant, hass_ws_client) -> None:
    hass.config.language = "nl"
    await _setup(hass, _entry())
    panel = hass.data[DATA_PANELS][DASHBOARD_URL]
    assert panel.sidebar_title == "Batterijcapaciteit"
    assert panel.sidebar_icon == "mdi:home-battery"
    assert panel.component_name == "lovelace"
    assert not panel.require_admin

    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "lovelace/config", "url_path": DASHBOARD_URL})
    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"] == {"strategy": {"type": "custom:marstek-capacity"}}


async def test_option_off_removes_menu_item(hass: HomeAssistant) -> None:
    entry = _entry()
    await _setup(hass, entry)
    assert DASHBOARD_URL in hass.data[DATA_PANELS]

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert "sidebar" in result["data_schema"].schema
    data = {
        k.schema: k.default()
        for k in result["data_schema"].schema
        if hasattr(k, "default") and callable(k.default)
    }
    data["sidebar"] = False
    await hass.config_entries.options.async_configure(result["flow_id"], data)
    await hass.async_block_till_done()
    assert DASHBOARD_URL not in hass.data[DATA_PANELS]


async def test_last_battery_removed_removes_menu_item(hass: HomeAssistant) -> None:
    entry = _entry()
    await _setup(hass, entry)
    assert DASHBOARD_URL in hass.data[DATA_PANELS]
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert DASHBOARD_URL not in hass.data[DATA_PANELS]


async def test_own_dashboard_with_same_address_is_left_alone(hass: HomeAssistant) -> None:
    from homeassistant.components import frontend

    assert await async_setup_component(hass, "lovelace", {})
    frontend.async_register_built_in_panel(
        hass, "lovelace", sidebar_title="Mine", frontend_url_path=DASHBOARD_URL,
        config={"mode": "storage"},
    )
    await _setup(hass, _entry())
    assert hass.data[DATA_PANELS][DASHBOARD_URL].sidebar_title == "Mine"
