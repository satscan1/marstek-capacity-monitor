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


async def test_config_flow_other_model(hass: HomeAssistant) -> None:
    """Other model: factory data entered by hand after the model step."""
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
    assert result["step_id"] == "model"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"model": "other", "purchase_date": "2024-02-01"}
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
    mon = hass.states.get("sensor.marstek_mt1_monitor_status")
    assert mon.state == "collecting" and mon.attributes["phase"] == "ready"

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

    await run(100, 50, 2.48, unit="kW")  # kW sensor is converted
    mon = hass.states.get("sensor.marstek_mt1_monitor_status")
    assert mon.attributes["phase"] == "full_discharge_running"
    assert mon.attributes["from_soc"] == 100
    await run(50, 11, 1.94, unit="kW")
    await run(11, 40, 1.5)

    assert hass.states.get("sensor.marstek_mt1_monitor_status").state == "measuring"
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
    assert result["step_id"] == "model"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"model": "venus_e_v12", "purchase_date": "2024-02-01"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["nominal_kwh"] == 5.12 and result["data"]["reserve_kwh"] == 0.51

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
    assert result["step_id"] == "model"


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
    assert first["step_id"] == "model"  # left open
    second = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    second = await hass.config_entries.flow.async_configure(second["flow_id"], data)
    assert second["step_id"] == "model"


async def test_scan_uses_friendly_name(hass: HomeAssistant) -> None:
    hass.states.async_set("sensor.marstek_venus_e_v3_battery_soc", 80,
        {"unit_of_measurement": "%", "device_class": "battery", "friendly_name": "Venus E v3 Battery SOC"})
    hass.states.async_set("sensor.marstek_venus_e_v3_battery_power", 0,
        {"unit_of_measurement": "W", "device_class": "power"})
    from custom_components.marstek_capacity_monitor.discovery import find_candidates
    cands = find_candidates(hass)
    assert [c.name for c in cands] == ["Venus E v3"]


async def test_scan_skips_cars_and_totals(hass: HomeAssistant) -> None:
    """Seen in a real installation: an EV and a 'house total' sum were proposed."""
    W = {"unit_of_measurement": "W", "device_class": "power"}
    P = {"unit_of_measurement": "%", "device_class": "battery"}
    hass.states.async_set("sensor.venus_5_12kwh_veranda_marstek_battery_state_of_charge", 80, P)
    hass.states.async_set("sensor.venus_5_12kwh_veranda_marstek_battery_power", 0, W)
    hass.states.async_set("sensor.byd_atto_3_batterijniveau", 70, P)
    hass.states.async_set("sensor.byd_atto_3_battery_power", 0, W)
    hass.states.async_set("sensor.house_total_battery_soc", 60, P)
    hass.states.async_set("sensor.house_total_battery_power", 0, W)
    from custom_components.marstek_capacity_monitor.discovery import find_candidates
    names = [c.soc_entity for c in find_candidates(hass)]
    assert names == ["sensor.venus_5_12kwh_veranda_marstek_battery_state_of_charge"]


async def test_model_preset_only_needs_install_date(hass: HomeAssistant) -> None:
    """Known model: factory data are filled in; the model is guessed from the name."""
    hass.states.async_set("sensor.venus_e_v3_battery_soc", 50,
        {"unit_of_measurement": "%", "device_class": "battery"})
    hass.states.async_set("sensor.venus_e_v3_battery_power", 0,
        {"unit_of_measurement": "W", "device_class": "power"})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"candidate": "0"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"battery_id": "v3", "name": "Venus v3",
         "soc_entity": "sensor.venus_e_v3_battery_soc",
         "power_entity": "sensor.venus_e_v3_battery_power"},
    )
    assert result["step_id"] == "model"
    model_key = next(k for k in result["data_schema"].schema if str(k) == "model")
    assert model_key.default() == "venus_e_v3"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"model": "venus_e_v3", "purchase_date": "2025-06-01"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    data = result["data"]
    assert data["nominal_kwh"] == 5.12 and data["reserve_kwh"] == 0.51
    assert data["cycle_life"] == 6000 and data["cycle_eol_pct"] == 80
    assert data["purchase_date"] == "2025-06-01" and data["model"] == "venus_e_v3"
    await hass.async_block_till_done()
    assert hass.states.get("sensor.marstek_v3_usable_capacity").state == "4.61"


async def test_venus_d_packs(hass: HomeAssistant) -> None:
    hass.states.async_set(SOC, 50, {"unit_of_measurement": "%"})
    hass.states.async_set(POWER, 0, {"unit_of_measurement": "W", "device_class": "power"})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"battery_id": "vd", "name": "Venus D", "soc_entity": SOC, "power_entity": POWER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"model": "venus_d", "purchase_date": "2025-06-01"}
    )
    assert result["step_id"] == "packs"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"packs": 3})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["nominal_kwh"] == 7.68
    assert result["data"]["reserve_kwh"] == 0.77
    assert result["data"]["packs"] == 3


async def test_status_sensor_missing(hass: HomeAssistant) -> None:
    hass.states.async_set(SOC, "unavailable")
    hass.states.async_set(POWER, 0, {"unit_of_measurement": "W"})
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    mon = hass.states.get("sensor.marstek_mt1_monitor_status")
    assert mon.state == "sensor_missing"
    assert mon.attributes["missing"] == [SOC]
    hass.states.async_set(SOC, 40, {"unit_of_measurement": "%"})
    await hass.async_block_till_done()
    mon = hass.states.get("sensor.marstek_mt1_monitor_status")
    assert mon.state == "collecting" and mon.attributes["phase"] == "waiting_full_charge"
    assert mon.attributes["soc"] == 40


async def test_scan_suggests_cell_sensors(hass: HomeAssistant) -> None:
    W = {"unit_of_measurement": "W", "device_class": "power"}
    P = {"unit_of_measurement": "%", "device_class": "battery"}
    V = {"unit_of_measurement": "mV", "device_class": "voltage"}
    hass.states.async_set("sensor.venus_veranda_battery_state_of_charge", 80, P)
    hass.states.async_set("sensor.venus_veranda_battery_power", 0, W)
    hass.states.async_set("sensor.venus_veranda_max_cell_voltage", 3330, V)
    hass.states.async_set("sensor.venus_veranda_min_cell_voltage", 3310, V)
    hass.states.async_set("sensor.venus_veranda_diff_cell_voltage", 20, V)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"candidate": "0"})
    sugg = {
        str(k): k.description.get("suggested_value")
        for k in result["data_schema"].schema
        if k.description
    }
    assert sugg["cell_max_entity"] == "sensor.venus_veranda_max_cell_voltage"
    assert sugg["cell_min_entity"] == "sensor.venus_veranda_min_cell_voltage"
    # only one of the two -> error
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"battery_id": "mt1", "name": "MT1",
         "soc_entity": "sensor.venus_veranda_battery_state_of_charge",
         "power_entity": "sensor.venus_veranda_battery_power",
         "cell_max_entity": "sensor.venus_veranda_max_cell_voltage"},
    )
    assert result["errors"] == {"cell_min_entity": "cells_both"}


async def test_cell_spread_after_full_charge(hass: HomeAssistant, freezer) -> None:
    """Sample once per full charge, after 5 minutes at rest; V is converted to mV."""
    freezer.move_to("2026-10-18 06:00:00+00:00")
    MAXC, MINC = "sensor.test_cell_max", "sensor.test_cell_min"
    V = {"unit_of_measurement": "V", "device_class": "voltage"}
    hass.states.async_set(SOC, 80, {"unit_of_measurement": "%"})
    hass.states.async_set(POWER, 1500, {"unit_of_measurement": "W"})
    hass.states.async_set(MAXC, 3.40, V)
    hass.states.async_set(MINC, 3.37, V)
    entry = _entry(cell_max_entity=MAXC, cell_min_entity=MINC)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    spread = hass.states.get("sensor.marstek_mt1_cell_spread")
    assert spread is not None and spread.state == "unknown"

    async def minutes(n):
        for _ in range(n):
            freezer.tick(timedelta(seconds=60))
            async_fire_time_changed(hass, dt_util.utcnow())
            await hass.async_block_till_done()

    hass.states.async_set(SOC, 97, {"unit_of_measurement": "%"})
    await minutes(10)  # still charging: no sample
    assert hass.states.get("sensor.marstek_mt1_cell_spread").state == "unknown"
    hass.states.async_set(POWER, 0, {"unit_of_measurement": "W"})
    hass.states.async_set(MAXC, 3.452, V)
    hass.states.async_set(MINC, 3.431, V)
    await minutes(3)
    assert hass.states.get("sensor.marstek_mt1_cell_spread").state == "unknown"
    await minutes(4)
    st = hass.states.get("sensor.marstek_mt1_cell_spread")
    assert float(st.state) == pytest.approx(21, abs=0.1)
    assert st.attributes["trend"][0]["month"] == "2026-10"
    # still full: no second sample until the SOC dropped below 90 %
    hass.states.async_set(MINC, 3.400, V)
    await minutes(10)
    assert hass.states.get("sensor.marstek_mt1_cell_spread").attributes["sample_count"] == 1


async def test_no_cell_sensor_without_cells(hass: HomeAssistant) -> None:
    hass.states.async_set(SOC, 50, {"unit_of_measurement": "%"})
    hass.states.async_set(POWER, 0, {"unit_of_measurement": "W"})
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.marstek_mt1_cell_spread") is None


async def test_temperature_stored_with_measurement(hass: HomeAssistant, freezer) -> None:
    """Cell temperature during a full discharge ends up in history and trend."""
    freezer.move_to("2026-10-18 06:00:00+00:00")
    TMAX, TMIN = "sensor.test_max_cell_temperature", "sensor.test_min_cell_temperature"
    T = {"unit_of_measurement": "°C", "device_class": "temperature"}
    hass.states.async_set(SOC, 100, {"unit_of_measurement": "%"})
    hass.states.async_set(POWER, 0, {"unit_of_measurement": "W"})
    hass.states.async_set(TMAX, 12.0, T)
    hass.states.async_set(TMIN, 10.0, T)
    entry = _entry(reserve_kwh=0.61, temp_max_entity=TMAX, temp_min_entity=TMIN)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    async def run(soc_from, soc_to, kwh):
        steps = abs(soc_to - soc_from)
        p = kwh * 3_600_000 / (steps * 60) * (1 if soc_to > soc_from else -1)
        hass.states.async_set(POWER, round(p, 3), {"unit_of_measurement": "W"})
        await hass.async_block_till_done()
        for i in range(1, steps + 1):
            freezer.tick(timedelta(seconds=60))
            async_fire_time_changed(hass, dt_util.utcnow())
            await hass.async_block_till_done()
            hass.states.async_set(SOC, soc_from + (soc_to - soc_from) * i / steps)
            await hass.async_block_till_done()

    await run(100, 11, 4.42)
    await run(11, 40, 1.5)
    m = hass.states.get("sensor.marstek_mt1_measured_capacity")
    assert m.attributes["history"][0]["temp_c"] == pytest.approx(11.0)
    assert m.attributes["trend"][0]["temp_c"] == pytest.approx(11.0)
    assert hass.states.get("sensor.marstek_mt1_monitor_status").attributes["temperature_check"]


async def test_scan_suggests_cell_temperature_not_mos(hass: HomeAssistant) -> None:
    P = {"unit_of_measurement": "%", "device_class": "battery"}
    W = {"unit_of_measurement": "W", "device_class": "power"}
    T = {"unit_of_measurement": "°C", "device_class": "temperature"}
    hass.states.async_set("sensor.venus_v3_battery_soc", 80, P)
    hass.states.async_set("sensor.venus_v3_battery_power", 0, W)
    hass.states.async_set("sensor.venus_v3_internal_mos1_temperature", 30, T)
    hass.states.async_set("sensor.venus_v3_max_mos_cell_temperature", 31, T)
    hass.states.async_set("sensor.venus_v3_max_cell_temperature", 15, T)
    hass.states.async_set("sensor.venus_v3_min_cell_temperature", 13, T)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"candidate": "0"})
    sugg = {
        str(k): k.description.get("suggested_value")
        for k in result["data_schema"].schema
        if k.description
    }
    assert sugg["temp_max_entity"] == "sensor.venus_v3_max_cell_temperature"
    assert sugg["temp_min_entity"] == "sensor.venus_v3_min_cell_temperature"



async def _status_after_quiet(hass, freezer, power, unit="W", minutes=90):
    hass.states.async_set(SOC, 11, {"unit_of_measurement": "%"})
    hass.states.async_set(POWER, power, {"unit_of_measurement": unit})
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    freezer.tick(timedelta(minutes=minutes))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    return hass.states.get("sensor.marstek_mt1_monitor_status")


async def test_idle_battery_is_not_stale(hass: HomeAssistant, freezer) -> None:
    """Empty battery standing still at -10 W: values do not change, connection is fine."""
    mon = await _status_after_quiet(hass, freezer, -10)
    assert mon.state == "collecting"


async def test_idle_in_kw_is_not_stale(hass: HomeAssistant, freezer) -> None:
    mon = await _status_after_quiet(hass, freezer, 0.01, "kW")
    assert mon.state == "collecting"


async def test_frozen_values_while_discharging_are_stale(hass: HomeAssistant, freezer) -> None:
    mon = await _status_after_quiet(hass, freezer, 0.8, "kW")
    assert mon.state == "no_recent_data"
    assert mon.attributes["last_data_minutes"] >= 60


async def test_stale_minutes_refresh_hourly(hass: HomeAssistant, freezer) -> None:
    mon = await _status_after_quiet(hass, freezer, 800, minutes=61)
    assert mon.state == "no_recent_data"
    first = mon.attributes["last_data_minutes"]
    freezer.tick(timedelta(minutes=70))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    mon = hass.states.get("sensor.marstek_mt1_monitor_status")
    assert mon.attributes["last_data_minutes"] >= first + 60


async def test_reset_measurements(hass: HomeAssistant) -> None:
    hass.states.async_set(SOC, 50, {"unit_of_measurement": "%"})
    hass.states.async_set(POWER, 0, {"unit_of_measurement": "W"})
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await hass.services.async_call(
        DOMAIN, "reset_measurements", {"config_entry_id": entry.entry_id}, blocking=True
    )
    await hass.async_block_till_done()
    assert entry.runtime_data.records == []


async def test_restart_during_discharge_is_bridged(hass: HomeAssistant, hass_storage, freezer) -> None:
    """Saved state from before a restart 2 minutes ago: the discharge keeps counting."""
    now = dt_util.utcnow().timestamp()
    entry = _entry()
    point = {"soc": 97.0, "ts": now - 3600, "e_charge": 0.0, "e_discharge": 0.0}
    hass_storage[f"{DOMAIN}.{entry.entry_id}"] = {
        "version": 1,
        "key": f"{DOMAIN}.{entry.entry_id}",
        "data": {
            "tracker": {
                "e_charge_kwh": 0.0, "e_discharge_kwh": 1.5,
                "power_w": -1500.0, "power_ts": now - 120, "soc": 60.0,
                "swing": {"direction": "discharge", "start": point,
                          "extreme": {**point, "soc": 60.0, "e_discharge": 1.5}, "valid": True},
                "sign": 1, "sign_confirmed": True, "sign_flipped": False,
            },
            "records": [],
        },
    }
    hass.states.async_set(SOC, 60, {"unit_of_measurement": "%"})
    hass.states.async_set(POWER, -1500, {"unit_of_measurement": "W"})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    mon = hass.states.get("sensor.marstek_mt1_monitor_status")
    assert mon.attributes["phase"] == "full_discharge_running"
    assert mon.attributes["interrupted"] is None
    sw = entry.runtime_data.tracker.s["swing"]
    assert sw["valid"] is True and sw["bridged_s"] == 120


async def test_stop_saves_exact_power_time(hass: HomeAssistant, freezer) -> None:
    """When HA stops, power is integrated up to that moment (for the restart bridge)."""
    from homeassistant.const import EVENT_HOMEASSISTANT_STOP

    hass.states.async_set(SOC, 60, {"unit_of_measurement": "%"})
    hass.states.async_set(POWER, -800, {"unit_of_measurement": "W"})
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    freezer.tick(timedelta(seconds=45))
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STOP)
    await hass.async_block_till_done()
    s = entry.runtime_data.tracker.s
    assert s["power_ts"] == pytest.approx(dt_util.utcnow().timestamp(), abs=1)
    assert s["e_discharge_kwh"] == pytest.approx(800 * 45 / 3_600_000, rel=0.01)



# ---------------------------------------------------------------------------
# 0.5: new models, SOC drift and cell calibration
# ---------------------------------------------------------------------------


async def _flow_to_model(hass: HomeAssistant, model: str, battery_id: str = "ep"):
    hass.states.async_set(SOC, 50, {"unit_of_measurement": "%"})
    hass.states.async_set(POWER, 0, {"unit_of_measurement": "W", "device_class": "power"})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"battery_id": battery_id, "name": "Test", "soc_entity": SOC, "power_entity": POWER},
    )
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {"model": model, "purchase_date": "2026-09-01"}
    )


async def test_venus_e_pro_packs(hass: HomeAssistant) -> None:
    result = await _flow_to_model(hass, "venus_e_pro")
    assert result["step_id"] == "packs"
    assert result["description_placeholders"]["model"] == "Venus E Pro"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"packs": 4})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["nominal_kwh"] == 8.32
    assert result["data"]["reserve_kwh"] == 0.83
    assert result["data"]["cycle_life"] == 10000
    assert result["data"]["notify"] is True


@pytest.mark.parametrize(
    ("model", "nominal", "reserve"),
    [("venus_e_v4", 5.024, 0.603), ("venus_e_max", 10.048, 1.005)],
)
async def test_new_models(hass: HomeAssistant, model, nominal, reserve) -> None:
    result = await _flow_to_model(hass, model, battery_id=model[-3:].strip("_"))
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["nominal_kwh"] == nominal
    assert result["data"]["reserve_kwh"] == reserve
    assert result["data"]["cycle_life"] == 10000


async def _setup_with_phone(hass: HomeAssistant, **extra):
    calls = []

    async def _notify(call):
        calls.append(dict(call.data))

    hass.services.async_register("notify", "mobile_app_phone", _notify)
    hass.states.async_set(SOC, 60, {"unit_of_measurement": "%"})
    hass.states.async_set(POWER, 0, {"unit_of_measurement": "W"})
    entry = _entry(**extra)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry, calls


def _drift(monitor, days_ago=(40, 20, 2), size=8.0):
    """Three clear SOC corrections, on days the battery was hardly ever full."""
    now = dt_util.utcnow().timestamp()
    monitor.soc_events = [
        {"ts": now - d * 86400, "type": "jump", "value": size} for d in days_ago
    ]
    monitor.alive_days = [
        dt_util.as_local(dt_util.utcnow() - timedelta(days=d)).strftime("%Y-%m-%d")
        for d in range(60, -1, -1)
    ]
    monitor.full_days = monitor.alive_days[::3]
    monitor._recalculate()  # noqa: SLF001


async def test_soc_drift_advice_and_dismiss(hass: HomeAssistant, freezer) -> None:
    from homeassistant.helpers import issue_registry as ir

    freezer.move_to("2026-10-22 12:00:00+00:00")
    entry, calls = await _setup_with_phone(hass)
    state = hass.states.get("sensor.marstek_mt1_soc_health")
    assert state.state == "ok" and state.attributes["notify"] is True
    events = []
    hass.bus.async_listen(f"{DOMAIN}_advice", lambda e: events.append(e.data))

    monitor = entry.runtime_data
    _drift(monitor)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.marstek_mt1_soc_health")
    assert state.state == "advies" and state.attributes["count"] == 3
    assert events and events[-1]["level"] == "advies" and events[-1]["kind"] == "soc"
    issues = [i for (d, i) in ir.async_get(hass).issues if d == DOMAIN]
    assert len(issues) == 1 and issues[0].startswith("soc_")
    sent = [c for c in calls if c.get("message") != "clear_notification"]
    assert "twee keer" in sent[-1]["message"] or "twice" in sent[-1]["message"]
    action = sent[-1]["data"]["actions"][0]["action"]

    # Phone button "Dismiss"
    hass.bus.async_fire("mobile_app_notification_action", {"action": action})
    await hass.async_block_till_done()
    state = hass.states.get("sensor.marstek_mt1_soc_health")
    assert state.state == "advies" and state.attributes["dismissed"] is True
    assert not [i for (d, i) in ir.async_get(hass).issues if d == DOMAIN]
    assert calls[-1]["message"] == "clear_notification"

    # Stays dismissed after a recalculation; a new series comes back
    n = len(calls)
    monitor._recalculate()  # noqa: SLF001
    await hass.async_block_till_done()
    assert len(calls) == n
    _drift(monitor, days_ago=(70, 50, 30, 14, 7, 1))
    await hass.async_block_till_done()


async def test_dismiss_service_and_repairs_ignore(hass: HomeAssistant, freezer) -> None:
    from homeassistant.helpers import issue_registry as ir

    freezer.move_to("2026-10-22 12:00:00+00:00")
    entry, _calls = await _setup_with_phone(hass)
    _drift(entry.runtime_data)
    await hass.async_block_till_done()
    await hass.services.async_call(
        DOMAIN, "dismiss_advice", {"battery": "mt1", "kind": "soc"}, blocking=True
    )
    assert hass.states.get("sensor.marstek_mt1_soc_health").attributes["dismissed"] is True

    # Ignoring under Settings -> Repairs does the same
    await hass.services.async_call(
        DOMAIN, "reset_measurements", {"config_entry_id": entry.entry_id}, blocking=True
    )
    _drift(entry.runtime_data)
    await hass.async_block_till_done()
    issue_id = next(i for (d, i) in ir.async_get(hass).issues if d == DOMAIN)
    ir.async_ignore_issue(hass, DOMAIN, issue_id, True)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.marstek_mt1_soc_health").attributes["dismissed"] is True


async def test_notifications_off(hass: HomeAssistant, freezer) -> None:
    from homeassistant.helpers import issue_registry as ir

    freezer.move_to("2026-10-22 12:00:00+00:00")
    entry, calls = await _setup_with_phone(hass, notify=False)
    _drift(entry.runtime_data)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.marstek_mt1_soc_health").state == "advies"  # card shows it
    assert not calls
    assert not [i for (d, i) in ir.async_get(hass).issues if d == DOMAIN]


async def test_options_have_notify_switch(hass: HomeAssistant) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    hass.states.async_set(SOC, 60)
    hass.states.async_set(POWER, 0, {"unit_of_measurement": "W"})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert "notify" in result["data_schema"].schema


async def test_live_jump_and_calibration_point(hass: HomeAssistant, freezer) -> None:
    freezer.move_to("2026-01-07 07:00:00+00:00")
    hass.states.async_set(SOC, 57, {"unit_of_measurement": "%"})
    hass.states.async_set(POWER, 2200, {"unit_of_measurement": "W"})
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    async def step(seconds, soc=None, power=None):
        freezer.tick(timedelta(seconds=seconds))
        if power is not None:
            hass.states.async_set(POWER, power, {"unit_of_measurement": "W"})
        if soc is not None:
            hass.states.async_set(SOC, soc, {"unit_of_measurement": "%"})
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done()

    await step(30, soc=91, power=2210)  # MT1, 7 Jan: 57 -> 91 % within a minute
    for i in range(10):
        await step(60, soc=92 + min(i, 7), power=2200 + i)
    await step(60, soc=100, power=5)
    for _ in range(12):
        await step(60, power=5)
    types = [e["type"] for e in entry.runtime_data.soc_events]
    assert "jump" in types and "top" in types
    state = hass.states.get("sensor.marstek_mt1_soc_health")
    assert state.attributes["last_calibration"] is not None
    assert state.attributes["trend"][0]["dev"] >= 34


async def test_sensitivity_options(hass: HomeAssistant, freezer) -> None:
    freezer.move_to("2026-10-22 12:00:00+00:00")
    entry, calls = await _setup_with_phone(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert "soc_sensitivity" in result["data_schema"].schema
    hass.config_entries.async_update_entry(entry, options={**entry.options, "soc_sensitivity": "off"})
    await hass.async_block_till_done()
    monitor = entry.runtime_data
    _drift(monitor)
    await hass.async_block_till_done()
    state = hass.states.get("sensor.marstek_mt1_soc_health")
    assert state.state == "ok" and state.attributes["sensitivity"] == "off"
    assert state.attributes["trend"]
    assert not [c for c in calls if c.get("message") != "clear_notification"]


KWH = {"unit_of_measurement": "kWh", "device_class": "energy", "state_class": "total_increasing"}
MV = {"unit_of_measurement": "mV", "device_class": "voltage"}


async def test_new_battery_takes_start_cycles_from_counter(hass: HomeAssistant) -> None:
    """The battery's own discharge counter fills in the cycles before monitoring
    (AC side, an estimate); daily counters are not used."""
    W = {"unit_of_measurement": "W", "device_class": "power"}
    P = {"unit_of_measurement": "%", "device_class": "battery"}
    pre = "sensor.venus_veranda_marstek_"
    hass.states.async_set(pre + "battery_state_of_charge", 80, P)
    hass.states.async_set(pre + "battery_power", 0, W)
    hass.states.async_set(pre + "daily_discharging_energy", 3.2, KWH)
    hass.states.async_set(pre + "total_discharging_energy", 1589.5, KWH)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"candidate": "0"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"battery_id": "mt1", "name": "MT1", "soc_entity": pre + "battery_state_of_charge",
         "power_entity": pre + "battery_power"},
    )
    assert result["step_id"] == "model"
    note = result["description_placeholders"]["counter"]
    assert pre + "total_discharging_energy" in note and "AC" in note
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"model": "venus_e_v12", "purchase_date": "2024-02-01"}
    )
    data = result["data"]
    assert data["initial_cycles"] == round(1589.5 / 4.61, 1)
    assert data["cycle_counter"] == pre + "total_discharging_energy"
    await hass.async_block_till_done()
    attrs = hass.states.get("sensor.marstek_mt1_expected_capacity").attributes
    assert attrs["initial_cycles"] == data["initial_cycles"]
    assert attrs["cycle_counter"] == pre + "total_discharging_energy"


async def _repairs_flow(hass, issue_id):
    from homeassistant.components.repairs import repairs_flow_manager

    manager = repairs_flow_manager(hass)
    return manager, await manager.async_init(DOMAIN, data={"issue_id": issue_id})


async def test_found_sensors_offered_under_repairs(hass: HomeAssistant) -> None:
    """After an update: cell sensors and the discharge counter found on the
    device are offered under Repairs; ticking adds them."""
    from homeassistant.helpers import issue_registry as ir

    hass.states.async_set(SOC, 60, {"unit_of_measurement": "%"})
    hass.states.async_set(POWER, 0, {"unit_of_measurement": "W"})
    hass.states.async_set("sensor.test_max_cell_voltage", 3330, MV)
    hass.states.async_set("sensor.test_min_cell_voltage", 3310, MV)
    hass.states.async_set("sensor.test_total_discharging_energy", 461.0, KWH)
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    issue_id = f"extras_{entry.entry_id}"
    issue = ir.async_get(hass).async_get_issue(DOMAIN, issue_id)
    assert issue is not None and issue.is_fixable

    manager, result = await _repairs_flow(hass, issue_id)
    assert result["step_id"] == "confirm"
    found = result["description_placeholders"]["found"]
    assert "sensor.test_max_cell_voltage" in found and "AC" in found
    result = await manager.async_configure(
        result["flow_id"], {"add_cells": True, "add_cycles": True}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options["cell_max_entity"] == "sensor.test_max_cell_voltage"
    assert entry.options["initial_cycles"] == 100.0  # 461 kWh / 4.61 kWh
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None
    assert hass.states.get("sensor.marstek_mt1_cell_health") is not None

    # The options form keeps the counter; a hand-changed value drops it
    result = await hass.config_entries.options.async_init(entry.entry_id)
    form = {
        str(k): (k.default() if callable(getattr(k, "default", None)) else None)
        for k in result["data_schema"].schema
    }
    form = {k: v for k, v in form.items() if v is not None}
    result = await hass.config_entries.options.async_configure(result["flow_id"], form)
    assert entry.options["cycle_counter"] == "sensor.test_total_discharging_energy"


async def test_declined_sensors_are_not_offered_again(hass: HomeAssistant) -> None:
    from homeassistant.helpers import issue_registry as ir

    hass.states.async_set(SOC, 60, {"unit_of_measurement": "%"})
    hass.states.async_set(POWER, 0, {"unit_of_measurement": "W"})
    hass.states.async_set("sensor.test_total_discharging_energy", 461.0, KWH)
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    issue_id = f"extras_{entry.entry_id}"
    manager, result = await _repairs_flow(hass, issue_id)
    assert "add_cells" not in {str(k) for k in result["data_schema"].schema}
    await manager.async_configure(result["flow_id"], {"add_cycles": False})
    await hass.async_block_till_done()
    assert entry.options["extras_declined"] == ["cycles"]
    assert entry.options.get("initial_cycles") is None
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None


async def test_no_offer_when_start_value_entered(hass: HomeAssistant) -> None:
    """A start value the user entered is never overwritten or questioned."""
    from homeassistant.helpers import issue_registry as ir

    hass.states.async_set(SOC, 60, {"unit_of_measurement": "%"})
    hass.states.async_set(POWER, 0, {"unit_of_measurement": "W"})
    hass.states.async_set("sensor.test_total_discharging_energy", 461.0, KWH)
    entry = _entry(initial_cycles=352)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert ir.async_get(hass).async_get_issue(DOMAIN, f"extras_{entry.entry_id}") is None


async def test_venus_c_preset_and_guess(hass: HomeAssistant) -> None:
    """Venus C: 2.56 kWh, picked from the name; the step text mentions it."""
    hass.states.async_set("sensor.venus_c_battery_soc", 50,
        {"unit_of_measurement": "%", "device_class": "battery"})
    hass.states.async_set("sensor.venus_c_battery_power", 0,
        {"unit_of_measurement": "W", "device_class": "power"})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"candidate": "0"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"battery_id": "vc", "name": "Venus C",
         "soc_entity": "sensor.venus_c_battery_soc",
         "power_entity": "sensor.venus_c_battery_power"},
    )
    assert result["step_id"] == "model"
    model_key = next(k for k in result["data_schema"].schema if str(k) == "model")
    assert model_key.default() == "venus_c"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"model": "venus_c", "purchase_date": "2025-06-01"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["nominal_kwh"] == 2.56
    assert result["data"]["reserve_kwh"] == 0.256
    await hass.async_block_till_done()
    assert hass.states.get("sensor.marstek_vc_usable_capacity").state == "2.304"


async def test_scan_finds_german_names_and_skips_phones(hass: HomeAssistant) -> None:
    """Seen on simon42: a German HA names the sensors 'SoC Batterie' and
    'Batterieleistung'; the Home Assistant app on a phone must not show up."""
    from homeassistant.helpers import entity_registry as er

    from custom_components.marstek_capacity_monitor.discovery import find_candidates

    W = {"unit_of_measurement": "W", "device_class": "power"}
    P = {"unit_of_measurement": "%", "device_class": "battery"}
    hass.states.async_set("sensor.marstek_soc_batterie", 11, P)
    hass.states.async_set("sensor.marstek_batterieleistung", -17, W)
    hass.states.async_set("sensor.marstek_ac_leistung", 0, W)
    reg = er.async_get(hass)
    for uid, obj, value, attrs in (
        ("phone_level", "sm_a525f_battery_level", 80, P),
        ("phone_power", "sm_a525f_battery_power", 3, W),
    ):
        reg.async_get_or_create("sensor", "mobile_app", uid, suggested_object_id=obj)
        hass.states.async_set(f"sensor.{obj}", value, attrs)
    cands = find_candidates(hass)
    assert [(c.soc_entity, c.power_entity) for c in cands] == [
        ("sensor.marstek_soc_batterie", "sensor.marstek_batterieleistung")
    ]


async def test_scan_finds_dutch_names(hass: HomeAssistant) -> None:
    from custom_components.marstek_capacity_monitor.discovery import find_candidates

    hass.states.async_set("sensor.venus_laadtoestand", 50, {"unit_of_measurement": "%"})
    hass.states.async_set("sensor.venus_batterijvermogen", 0, {"unit_of_measurement": "W"})
    cands = find_candidates(hass)
    assert [c.power_entity for c in cands] == ["sensor.venus_batterijvermogen"]


async def test_impossible_power_is_ignored_and_reported(hass: HomeAssistant, freezer) -> None:
    """Seen on simon42: a self-made sensor 1000x too high made the full cycles
    jump by 400 in a day. Such values are ignored and reported under Repairs."""
    from homeassistant.helpers import issue_registry as ir

    freezer.move_to("2026-10-24 12:00:00+00:00")
    hass.states.async_set(SOC, 40, {"unit_of_measurement": "%"})
    hass.states.async_set(POWER, 0, {"unit_of_measurement": "W"})
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    issue_id = f"implausible_power_{entry.entry_id}"

    # 800 W reported as 800 kW, for an hour
    for i in range(60):
        hass.states.async_set(POWER, -800 - i % 2, {"unit_of_measurement": "kW"})
        await hass.async_block_till_done()
        freezer.tick(timedelta(seconds=60))
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done()
    assert float(hass.states.get("sensor.marstek_mt1_dc_discharged").state) < 0.01
    t = entry.runtime_data.tracker.s
    assert t["e_discharge_kwh"] + t["e_charge_kwh"] < 0.01
    issue = ir.async_get(hass).async_get_issue(DOMAIN, issue_id)
    assert issue is not None
    assert issue.translation_placeholders["value"] == "-800 kW"
    assert issue.translation_placeholders["watts"] == "800,000"

    # Sensor fixed: real values count again, the message goes after 24 h
    hass.states.async_set(POWER, -800, {"unit_of_measurement": "W"})
    await hass.async_block_till_done()
    for _ in range(30):
        freezer.tick(timedelta(seconds=60))
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done()
    t = entry.runtime_data.tracker.s  # sign not known yet: either bucket
    assert t["e_discharge_kwh"] + t["e_charge_kwh"] == pytest.approx(0.4, abs=0.05)
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None
    hass.states.async_set(POWER, 0, {"unit_of_measurement": "W"})
    freezer.tick(timedelta(hours=25))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None
