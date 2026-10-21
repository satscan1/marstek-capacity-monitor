"""History replay with a real recorder (separate file: the recorder must start before hass)."""

from datetime import timedelta

import pytest

from homeassistant.core import HomeAssistant

from tests.test_integration import POWER, SOC, _entry


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(recorder_mock, enable_custom_integrations):
    yield


async def test_new_battery_gets_first_measurement_from_history(
    hass: HomeAssistant, freezer
) -> None:
    """A full discharge that is already in the recorder counts right away."""
    from pytest_homeassistant_custom_component.components.recorder.common import (
        async_wait_recording_done,
    )

    attrs_p, attrs_s = {"unit_of_measurement": "W"}, {"unit_of_measurement": "%"}
    hass.states.async_set(SOC, 100, attrs_s)
    hass.states.async_set(POWER, 0, attrs_p)
    freezer.tick(timedelta(hours=2))  # full and idle for a while
    for i in range(1, 90):  # 100 % -> 11 %: 4.45 kWh in 89 minutes
        freezer.tick(timedelta(seconds=30))
        hass.states.async_set(POWER, -3000 - (i % 2), attrs_p)
        freezer.tick(timedelta(seconds=30))
        hass.states.async_set(SOC, 100 - i, attrs_s)
    for i in range(1, 6):  # charging again: closes the swing
        freezer.tick(timedelta(seconds=30))
        hass.states.async_set(POWER, 2000 + (i % 2), attrs_p)
        freezer.tick(timedelta(seconds=30))
        hass.states.async_set(SOC, 11 + i, attrs_s)
    await async_wait_recording_done(hass)

    entry = _entry(reserve_kwh=0.61)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    await async_wait_recording_done(hass)
    await hass.async_block_till_done(wait_background_tasks=True)

    records = entry.runtime_data.records
    assert len(records) == 1 and records[0]["source"] == "history"
    mon = hass.states.get("sensor.marstek_mt1_monitor_status")
    assert mon.state == "measuring"
    pct = float(hass.states.get("sensor.marstek_mt1_capacity_pct").state)
    assert 95 < pct < 101
