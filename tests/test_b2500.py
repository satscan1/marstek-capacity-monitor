"""B2500 (1.1.0, test): V2 measured via voltage x current, V1 not measurable yet."""

import pytest

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.marstek_capacity_monitor.const import DOMAIN

SOC = "sensor.b2500_battery_percentage"
VOLT = "sensor.b2500_host_battery_voltage"
AMP = "sensor.b2500_host_battery_current"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


async def _to_model(hass: HomeAssistant, power: str | None = None):
    hass.states.async_set(SOC, 60, {"unit_of_measurement": "%"})
    hass.states.async_set(VOLT, 51.2, {"unit_of_measurement": "V", "device_class": "voltage"})
    hass.states.async_set(AMP, -4.0, {"unit_of_measurement": "A", "device_class": "current"})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    data = {"battery_id": "b1", "name": "B2500", "soc_entity": SOC}
    if power:
        data["power_entity"] = power
    result = await hass.config_entries.flow.async_configure(result["flow_id"], data)
    assert result["step_id"] == "model"
    return result


async def test_b2500_v2_power_from_voltage_and_current(hass: HomeAssistant) -> None:
    result = await _to_model(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"model": "b2500_v2", "purchase_date": "2025-05-01"}
    )
    assert result["step_id"] == "b2500"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"b2500_voltage_entity": VOLT, "b2500_current_entity": AMP}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    data = result["data"]
    assert data["power_entity"] == "sensor.marstek_b1_b2500_battery_power"
    assert data["nominal_kwh"] == 2.24
    await hass.async_block_till_done()
    state = hass.states.get("sensor.marstek_b1_b2500_battery_power")
    assert state is not None and float(state.state) == pytest.approx(-204.8)
    hass.states.async_set(AMP, 2000, {"unit_of_measurement": "mA", "device_class": "current"})
    await hass.async_block_till_done()
    assert float(hass.states.get("sensor.marstek_b1_b2500_battery_power").state) == pytest.approx(102.4)
    hass.states.async_set(VOLT, "unavailable")
    await hass.async_block_till_done()
    assert hass.states.get("sensor.marstek_b1_b2500_battery_power").state == "unavailable"


async def test_b2500_v1_is_not_measurable(hass: HomeAssistant) -> None:
    result = await _to_model(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"model": "b2500_v1", "purchase_date": "2025-05-01"}
    )
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "b2500_v1"


async def test_power_needed_for_other_models(hass: HomeAssistant) -> None:
    result = await _to_model(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"model": "venus_e_v12", "purchase_date": "2025-05-01"}
    )
    assert result["step_id"] == "model" and result["errors"] == {"model": "power_required"}


# --- 1.1.0-dev2: plug-and-play checks --------------------------------------

from datetime import timedelta

from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)


async def _to_b2500_step(hass: HomeAssistant, volt=VOLT, amp=AMP):
    """Like _to_model, but only the sensors given exist."""
    hass.states.async_set(SOC, 60, {"unit_of_measurement": "%"})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"battery_id": "b1", "name": "B2500", "soc_entity": SOC}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"model": "b2500_v2", "purchase_date": "2025-05-01"}
    )
    assert result["step_id"] == "b2500"
    return result


async def test_missing_sensors_say_turn_on_extra_battery_data(hass: HomeAssistant) -> None:
    hass.config.language = "de"
    result = await _to_b2500_step(hass)
    check = result["description_placeholders"]["check"]
    assert "Enable Extra Battery Data" in check and "nicht gefunden" in check


async def test_no_value_blocks_and_names_the_sensor(hass: HomeAssistant) -> None:
    hass.states.async_set(VOLT, "unknown", {"unit_of_measurement": "V", "device_class": "voltage"})
    hass.states.async_set(AMP, "unknown", {"unit_of_measurement": "A", "device_class": "current"})
    result = await _to_b2500_step(hass)
    assert VOLT in result["description_placeholders"]["check"]
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"b2500_voltage_entity": VOLT, "b2500_current_entity": AMP}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {
        "b2500_voltage_entity": "b2500_no_value",
        "b2500_current_entity": "b2500_no_value",
    }
    # Values arrive: the same submit now works
    hass.states.async_set(VOLT, 51.2, {"unit_of_measurement": "V", "device_class": "voltage"})
    hass.states.async_set(AMP, 1.5, {"unit_of_measurement": "A", "device_class": "current"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"b2500_voltage_entity": VOLT, "b2500_current_entity": AMP}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_extra_pack_and_wrong_unit_are_refused(hass: HomeAssistant) -> None:
    extra = "sensor.b2500_battery_extra1_voltage"
    watt = "sensor.b2500_host_battery_current_w"
    hass.states.async_set(extra, 51.0, {"unit_of_measurement": "V", "device_class": "voltage"})
    hass.states.async_set(watt, 100, {"unit_of_measurement": "W", "device_class": "current"})
    result = await _to_b2500_step(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"b2500_voltage_entity": extra, "b2500_current_entity": watt}
    )
    assert result["errors"] == {
        "b2500_voltage_entity": "b2500_not_host",
        "b2500_current_entity": "b2500_wrong_unit",
    }


async def test_pv_in_device_name_is_still_the_host(hass: HomeAssistant) -> None:
    """ZakOyten (#16): device "Batterie PV Balkon"."""
    volt = "sensor.batterie_pv_balkon_host_battery_voltage"
    amp = "sensor.batterie_pv_balkon_host_battery_current"
    hass.states.async_set(volt, 51.2, {"unit_of_measurement": "V", "device_class": "voltage", "friendly_name": "Batterie PV Balkon Host Battery Voltage"})
    hass.states.async_set(amp, 1.0, {"unit_of_measurement": "A", "device_class": "current", "friendly_name": "Batterie PV Balkon Host Battery Current"})
    result = await _to_b2500_step(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"b2500_voltage_entity": volt, "b2500_current_entity": amp}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_disabled_sensors_are_named(hass: HomeAssistant) -> None:
    other = MockConfigEntry(domain="mqtt")
    other.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=other.entry_id, identifiers={("mqtt", "b2500")}, name="B2500"
    )
    reg = er.async_get(hass)
    reg.async_get_or_create("sensor", "mqtt", "soc", suggested_object_id="b2500_battery_percentage", device_id=device.id)
    v = reg.async_get_or_create(
        "sensor", "mqtt", "b2500_battery_voltage", suggested_object_id="b2500_host_battery_voltage",
        device_id=device.id, original_name="Host Battery Voltage", disabled_by=er.RegistryEntryDisabler.INTEGRATION,
    )
    reg.async_get_or_create(
        "sensor", "mqtt", "b2500_battery_current", suggested_object_id="b2500_host_battery_current",
        device_id=device.id, original_name="Host Battery Current", disabled_by=er.RegistryEntryDisabler.INTEGRATION,
    )
    result = await _to_b2500_step(hass)
    check = result["description_placeholders"]["check"]
    assert v.entity_id in check and "Disabled" in check


async def test_repairs_message_when_values_stop(hass: HomeAssistant, freezer) -> None:
    freezer.move_to("2026-11-04 10:00:00+00:00")
    hass.states.async_set(VOLT, 51.2, {"unit_of_measurement": "V", "device_class": "voltage"})
    hass.states.async_set(AMP, 1.0, {"unit_of_measurement": "A", "device_class": "current"})
    result = await _to_b2500_step(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"b2500_voltage_entity": VOLT, "b2500_current_entity": AMP}
    )
    entry_id = result["result"].entry_id
    await hass.async_block_till_done()
    issue_id = f"b2500_no_data_{entry_id}"

    hass.states.async_set(AMP, "unavailable")
    for _ in range(10):  # 10 minutes: not yet
        freezer.tick(timedelta(seconds=60))
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done()
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None
    for _ in range(6):  # past 15 minutes
        freezer.tick(timedelta(seconds=60))
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done()
    issue = ir.async_get(hass).async_get_issue(DOMAIN, issue_id)
    assert issue is not None and issue.translation_placeholders["sensors"] == AMP

    report = result["result"].runtime_data.export("full")["battery"]
    assert report["b2500_values"][AMP] == "unavailable"

    hass.states.async_set(AMP, 1.2, {"unit_of_measurement": "A", "device_class": "current"})
    freezer.tick(timedelta(seconds=60))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None
