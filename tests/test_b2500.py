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
