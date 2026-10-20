"""End-to-end tests inside a real Home Assistant instance."""

from datetime import timedelta

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.util import dt as dt_util

from custom_components.marstek_capacity_monitor.const import DOMAIN

SOC = "sensor.test_soc"
POWER = "sensor.test_power"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


def _entry(battery_id="mt1", **extra):
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=battery_id,
        title=battery_id.upper(),
        data={
            "battery_id": battery_id,
            "name": battery_id.upper(),
            "soc_entity": SOC,
            "power_entity": POWER,
            "power_sign": "auto",
            "nominal_kwh": 5.12,
            "reserve_kwh": 0.51,
            "purchase_date": "2024-02-01",
            "warranty_years": 10,
            "red_pct": 75,
            "tolerance_pct": 5,
            "cycle_life": 6000,
            "cycle_eol_pct": 80,
            "initial_cycles": 0,
            **extra,
        },
    )


async def test_config_flow_two_steps(hass: HomeAssistant) -> None:
    hass.states.async_set(SOC, 50, {"unit_of_measurement": "%"})
    hass.states.async_set(POWER, 0, {"unit_of_measurement": "W", "device_class": "power"})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    # nothing recognisable -> straight to choosing the sensors yourself
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "details"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "battery_id": "MT1",
            "name": "MT1 veranda",
            "soc_entity": SOC,
            "power_entity": POWER,
        },
    )
    assert result["step_id"] == "specs"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "nominal_kwh": 5.12,
            "reserve_kwh": 0.51,
            "purchase_date": "2024-02-01",
            "warranty_years": 10,
            "red_pct": 75,
            "tolerance_pct": 5,
            "cycle_life": 6000,
            "cycle_eol_pct": 80,
            "initial_cycles": 0,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["battery_id"] == "mt1"
    await hass.async_block_till_done()
    assert hass.states.get("sensor.marstek_mt1_usable_capacity").state == "4.61"


async def test_max_six_batteries(hass: HomeAssistant) -> None:
    for i in range(1, 7):
        _entry(f"mt{i}").add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "max_batteries"


async def test_full_discharge_end_to_end(hass: HomeAssistant, freezer) -> None:
    """100 -> 11 % with 4.42 kWh DC, then recharge: 4.37 kWh = 97 % (88 % band)."""
    freezer.move_to("2026-10-18 06:00:00+00:00")
    hass.states.async_set(SOC, 100, {"unit_of_measurement": "%"})
    hass.states.async_set(POWER, 0, {"unit_of_measurement": "W"})
    entry = _entry(reserve_kwh=0.61)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    status = hass.states.get("sensor.marstek_mt1_warranty_status")
    assert status.state == "no_measurement"

    sessions = []
    hass.bus.async_listen(f"{DOMAIN}_session", lambda e: sessions.append(e.data))

    async def run(soc_from, soc_to, kwh, unit="W"):
        steps = abs(soc_to - soc_from)
        power_w = kwh * 3_600_000 / (steps * 60) * (1 if soc_to > soc_from else -1)
        value = power_w / 1000 if unit == "kW" else power_w
        hass.states.async_set(POWER, round(value, 4), {"unit_of_measurement": unit})
        await hass.async_block_till_done()
        for i in range(1, steps + 1):
            freezer.tick(timedelta(seconds=60))
            async_fire_time_changed(hass, dt_util.utcnow())
            await hass.async_block_till_done()
            soc = soc_from + (soc_to - soc_from) * i / steps
            hass.states.async_set(SOC, soc, {"unit_of_measurement": "%"})
            await hass.async_block_till_done()

    await run(100, 11, 4.42, unit="kW")  # kW sensor is converted
    await run(11, 40, 1.5)

    assert len(sessions) == 1
    assert sessions[0]["direction"] == "discharge"
    assert sessions[0]["e_dc_kwh"] == pytest.approx(4.42, abs=0.02)

    measured = hass.states.get("sensor.marstek_mt1_measured_capacity")
    assert float(measured.state) == pytest.approx(4.37, abs=0.02)
    assert measured.attributes["measurement_count"] == 1
    assert measured.attributes["trend"][0]["month"] == "2026-10"
    pct = hass.states.get("sensor.marstek_mt1_capacity_pct")
    assert float(pct.state) == pytest.approx(96.9, abs=0.5)
    assert hass.states.get("sensor.marstek_mt1_warranty_status").state == "good"
    assert float(hass.states.get("sensor.marstek_mt1_margin").state) == pytest.approx(-0.14, abs=0.02)
    assert hass.states.get("sensor.marstek_mt1_warranty_end").state == "2034-02-01"

    # Survives a reload (stored in .storage)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    measured = hass.states.get("sensor.marstek_mt1_measured_capacity")
    assert float(measured.state) == pytest.approx(4.37, abs=0.02)


async def test_negative_is_charge_option(hass: HomeAssistant, freezer) -> None:
    """Sensor that reports discharging as positive."""
    freezer.move_to("2026-10-18 06:00:00+00:00")
    hass.states.async_set(SOC, 100)
    hass.states.async_set(POWER, 0, {"unit_of_measurement": "W"})
    entry = _entry(power_sign="charge_negative")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    hass.states.async_set(POWER, 2000, {"unit_of_measurement": "W"})  # discharging
    for i in range(1, 31):
        freezer.tick(timedelta(seconds=60))
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done()
    assert entry.runtime_data.tracker.cumulative_discharge_kwh == pytest.approx(1.0, abs=0.05)


SPECS = {
    "nominal_kwh": 5.12,
    "reserve_kwh": 0.51,
    "purchase_date": "2025-05-01",
    "warranty_years": 10,
    "cycle_life": 6000,
    "cycle_eol_pct": 80,
    "initial_cycles": 0,
    "red_pct": 75,
    "tolerance_pct": 5,
}


async def test_scan_proposes_existing_sensors(hass: HomeAssistant) -> None:
    """ESPHome-style names are found; settings, AC power and phones are not."""
    W = {"unit_of_measurement": "W", "device_class": "power"}
    P = {"unit_of_measurement": "%", "device_class": "battery"}
    hass.states.async_set("sensor.venus_5_12kwh_berging_marstek_battery_state_of_charge", 80, P)
    hass.states.async_set("sensor.venus_5_12kwh_berging_marstek_battery_power", -500, W)
    hass.states.async_set("sensor.venus_5_12kwh_berging_marstek_ac_power", -480, W)
    hass.states.async_set("sensor.venus_5_12kwh_berging_marstek_charging_cutoff_capacity", 100, {"unit_of_measurement": "%"})
    hass.states.async_set("sensor.pixel_battery_level", 55, P)
    hass.states.async_set("sensor.p1_meter_vermogen", 300, W)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["step_id"] == "user"
    assert result["description_placeholders"]["count"] == "1"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"candidate": "0"}
    )
    assert result["step_id"] == "details"
    schema_defaults = {
        str(k): k.description.get("suggested_value")
        for k in result["data_schema"].schema
        if k.description
    }
    assert schema_defaults["soc_entity"].endswith("battery_state_of_charge")
    assert schema_defaults["power_entity"].endswith("battery_power")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "battery_id": "mt2",
            "name": "MT2 berging",
            "soc_entity": schema_defaults["soc_entity"],
            "power_entity": schema_defaults["power_entity"],
        },
    )
    assert result["step_id"] == "specs"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], SPECS)
    assert result["type"] is FlowResultType.CREATE_ENTRY

    # Already configured -> not proposed again
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["step_id"] == "details"


async def test_ac_sensor_warning(hass: HomeAssistant) -> None:
    hass.states.async_set(SOC, 50, {"unit_of_measurement": "%"})
    hass.states.async_set("sensor.marstek_ac_power", 0, {"unit_of_measurement": "W", "device_class": "power"})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    data = {"battery_id": "mt1", "name": "MT1", "soc_entity": SOC, "power_entity": "sensor.marstek_ac_power"}
    result = await hass.config_entries.flow.async_configure(result["flow_id"], data)
    assert result["errors"] == {"power_entity": "looks_like_ac"}
    # second time with the same sensor: accepted
    result = await hass.config_entries.flow.async_configure(result["flow_id"], data)
    assert result["step_id"] == "specs"


async def test_auto_sign_notification(hass: HomeAssistant, freezer, monkeypatch) -> None:
    """Inverted sensor: corrected automatically and the user is told."""
    freezer.move_to("2026-10-18 06:00:00+00:00")
    hass.states.async_set(SOC, 100)
    hass.states.async_set(POWER, 0, {"unit_of_measurement": "W"})
    entry = _entry(reserve_kwh=0.61)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    created = []
    from custom_components.marstek_capacity_monitor import monitor as mon
    monkeypatch.setattr(
        mon.persistent_notification, "async_create",
        lambda hass_, msg, title=None, notification_id=None: created.append((msg, notification_id)),
    )

    async def run(soc_from, soc_to, kwh):
        steps = abs(soc_to - soc_from)
        p = kwh * 3_600_000 / (steps * 60) * (1 if soc_to > soc_from else -1)
        hass.states.async_set(POWER, round(-p, 3), {"unit_of_measurement": "W"})  # inverted
        await hass.async_block_till_done()
        for i in range(1, steps + 1):
            freezer.tick(timedelta(seconds=60))
            async_fire_time_changed(hass, dt_util.utcnow())
            await hass.async_block_till_done()
            hass.states.async_set(SOC, soc_from + (soc_to - soc_from) * i / steps)
            await hass.async_block_till_done()

    await run(100, 11, 4.42)
    await run(11, 40, 1.5)
    measured = hass.states.get("sensor.marstek_mt1_measured_capacity")
    assert float(measured.state) == pytest.approx(4.37, abs=0.02)
    diag = hass.states.get("sensor.marstek_mt1_dc_discharged")
    assert diag.attributes["power_sign"] == "auto_reversed"
    assert len(created) == 1
    assert created[0][1] == f"{DOMAIN}_sign_{entry.entry_id}"
    assert "omgedraaid" in created[0][0] and POWER in created[0][0]


async def test_abandoned_flow_does_not_block(hass: HomeAssistant) -> None:
    """A flow left open at the factory-data step must not block a new one."""
    hass.states.async_set(SOC, 50, {"unit_of_measurement": "%"})
    hass.states.async_set(POWER, 0, {"unit_of_measurement": "W", "device_class": "power"})
    data = {"battery_id": "mt1", "name": "MT1", "soc_entity": SOC, "power_entity": POWER}
    first = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    first = await hass.config_entries.flow.async_configure(first["flow_id"], data)
    assert first["step_id"] == "specs"  # left open
    second = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    second = await hass.config_entries.flow.async_configure(second["flow_id"], data)
    assert second["step_id"] == "specs"


async def test_scan_uses_friendly_name(hass: HomeAssistant) -> None:
    hass.states.async_set("sensor.marstek_venus_e_v3_battery_soc", 80,
        {"unit_of_measurement": "%", "device_class": "battery", "friendly_name": "Venus E v3 Battery SOC"})
    hass.states.async_set("sensor.marstek_venus_e_v3_battery_power", 0,
        {"unit_of_measurement": "W", "device_class": "power"})
    from custom_components.marstek_capacity_monitor.discovery import find_candidates
    cands = find_candidates(hass)
    assert [c.name for c in cands] == ["Venus E v3"]
