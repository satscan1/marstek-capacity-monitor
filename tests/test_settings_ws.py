"""The settings window of the card (0.5.5-rc3): websocket commands."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from custom_components.marstek_capacity_monitor.const import DOMAIN

from .test_integration import POWER, SOC, _entry, _setup_with_one_record  # noqa: F401
from .test_integration import auto_enable_custom_integrations  # noqa: F401


async def _ws(hass, hass_ws_client, msg):
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(msg)
    return await client.receive_json()


async def test_window_gets_sensors_values_and_texts(hass: HomeAssistant, hass_ws_client) -> None:
    entry = await _setup_with_one_record(hass)
    hass.states.async_set("sensor.venus_veranda_marstek_battery_state_of_charge", 61, {"unit_of_measurement": "%", "device_class": "battery"})
    hass.states.async_set("sensor.venus_veranda_marstek_battery_power", 0, {"unit_of_measurement": "W", "device_class": "power"})
    r = await _ws(hass, hass_ws_client, {"type": f"{DOMAIN}/settings", "entry_id": entry.entry_id, "lang": "nl"})
    assert r["success"], r
    res = r["result"]
    assert res["sensors"]["soc"] == {"id": SOC, "name": SOC, "value": "60 %"}
    assert res["sensors"]["power"]["value"] == "0 W"
    assert res["found"][0]["power"]["id"] == "sensor.venus_veranda_marstek_battery_power"
    assert res["found"][0]["soc"]["value"] == "61 %"
    assert res["values"]["nominal_kwh"] == 5.12 and res["values"]["notify"] is True
    assert res["texts"]["label"]["red_pct"].startswith("Rode grens")
    assert res["texts"]["choices"]["sensitivity"]["strict"] == "Extra"
    assert res["texts"]["errors"]["reserve_too_large"]


async def test_window_saves_with_the_checks_of_the_form(hass: HomeAssistant, hass_ws_client) -> None:
    entry = await _setup_with_one_record(hass)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": f"{DOMAIN}/settings/save", "entry_id": entry.entry_id,
                                    "values": {"reserve_kwh": 6, "red_pct": 500, "cell_max_entity": "sensor.x"}})
    r = await client.receive_json()
    assert r["result"]["errors"] == {"red_pct": "out_of_range", "reserve_kwh": "reserve_too_large", "cell_min_entity": "cells_both"}
    assert "red_pct" not in entry.options
    await client.send_json_auto_id({"type": f"{DOMAIN}/settings/save", "entry_id": entry.entry_id,
                                    "values": {"red_pct": 70, "soc_sensitivity": "strict", "notify": False, "nominal_kwh": "5,02"}})
    r = await client.receive_json()
    assert r["result"]["errors"] == {}
    await hass.async_block_till_done()
    assert entry.options["red_pct"] == 70 and entry.options["soc_sensitivity"] == "strict"
    assert entry.options["notify"] is False and entry.options["nominal_kwh"] == 5.02
    assert entry.runtime_data is not None and len(entry.runtime_data.records) == 1


async def test_window_changes_sensors_warns_for_ac_and_can_start_over(hass: HomeAssistant, hass_ws_client) -> None:
    entry = await _setup_with_one_record(hass)
    hass.states.async_set("sensor.house_grid_ac_power", 300, {"unit_of_measurement": "W", "device_class": "power"})
    hass.states.async_set("sensor.new_power", 0, {"unit_of_measurement": "W", "device_class": "power"})
    client = await hass_ws_client(hass)
    base = {"type": f"{DOMAIN}/sensors/save", "entry_id": entry.entry_id, "soc": SOC}
    await client.send_json_auto_id({**base, "power": SOC})
    assert (await client.receive_json())["result"]["error"] == "same_entity"
    await client.send_json_auto_id({**base, "power": "sensor.house_grid_ac_power"})
    assert (await client.receive_json())["result"]["error"] == "looks_like_ac"
    assert entry.data["power_entity"] == POWER
    await client.send_json_auto_id({**base, "power": "sensor.new_power"})
    r = (await client.receive_json())["result"]
    assert r["error"] is None and r["changed"] is True
    await hass.async_block_till_done()
    assert entry.data["power_entity"] == "sensor.new_power"
    assert len(entry.runtime_data.records) == 1  # measurements stay
    await client.send_json_auto_id({**base, "power": "sensor.new_power", "restart": True})
    assert (await client.receive_json())["result"]["restarted"] is True
    await hass.async_block_till_done()
    assert entry.runtime_data.records == []


async def test_window_is_for_administrators(hass: HomeAssistant, hass_ws_client, hass_read_only_access_token) -> None:
    entry = await _setup_with_one_record(hass)
    client = await hass_ws_client(hass, hass_read_only_access_token)
    await client.send_json_auto_id({"type": f"{DOMAIN}/settings", "entry_id": entry.entry_id})
    r = await client.receive_json()
    assert not r["success"] and r["error"]["code"] == "unauthorized"


async def test_removing_a_battery_removes_its_repairs(hass: HomeAssistant) -> None:
    entry = await _setup_with_one_record(hass)
    ir.async_create_issue(hass, DOMAIN, f"check_power_{entry.entry_id}", is_fixable=False,
                          severity=ir.IssueSeverity.WARNING, translation_key="check_power")
    ir.async_create_issue(hass, DOMAIN, "check_power_other", is_fixable=False,
                          severity=ir.IssueSeverity.WARNING, translation_key="check_power")
    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    issues = ir.async_get(hass).issues
    assert (DOMAIN, f"check_power_{entry.entry_id}") not in issues
    assert (DOMAIN, "check_power_other") in issues


async def test_window_restores_a_backup(hass: HomeAssistant, hass_ws_client) -> None:
    """Restore from the window: an uploaded report file, merged."""
    from unittest.mock import patch
    from contextlib import contextmanager
    from pathlib import Path

    entry = await _setup_with_one_record(hass)
    monitor = entry.runtime_data
    report = monitor.report_html("full")
    monitor.records = []
    await monitor._store.async_save(monitor._data())

    import tempfile

    tmp = Path(tempfile.mkdtemp()) / "report.html"
    tmp.write_text(report, encoding="utf-8")

    @contextmanager
    def fake(_hass, _file_id):
        yield tmp

    with patch("homeassistant.components.file_upload.process_uploaded_file", fake):
        r = await _ws(hass, hass_ws_client, {"type": f"{DOMAIN}/restore", "entry_id": entry.entry_id, "file_id": "x", "mode": "merge"})
    assert r["success"], r
    assert r["result"]["error"] is None and r["result"]["records"] == 1
    assert len(entry.runtime_data.records) == 1

    tmp.write_text("not a report", encoding="utf-8")
    with patch("homeassistant.components.file_upload.process_uploaded_file", fake):
        r = await _ws(hass, hass_ws_client, {"type": f"{DOMAIN}/restore", "entry_id": entry.entry_id, "file_id": "x", "mode": "merge"})
    assert r["result"]["error"] == "restore_invalid"
