"""Back-up, report and restore inside Home Assistant (0.5.5)."""

from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.marstek_capacity_monitor.const import DOMAIN

SOC = "sensor.test_soc"
POWER = "sensor.test_power"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


def _entry():
    return MockConfigEntry(
        domain=DOMAIN, unique_id="mt1", title="MT1 veranda",
        data={"battery_id": "mt1", "name": "MT1 veranda", "soc_entity": SOC, "power_entity": POWER,
              "power_sign": "auto", "nominal_kwh": 5.12, "reserve_kwh": 0.51, "purchase_date": "2024-02-01",
              "warranty_years": 10, "red_pct": 75, "tolerance_pct": 5, "cycle_life": 6000,
              "cycle_eol_pct": 80, "initial_cycles": 0},
    )


REC = {"ts": 1790000000.0, "start_ts": 1789980000.0, "direction": "discharge", "soc_start": 100,
       "soc_end": 10, "delta_soc": 90, "duration_min": 330, "e_dc_kwh": 4.40, "valid": True}


async def _setup(hass):
    hass.states.async_set(SOC, 60, {"unit_of_measurement": "%"})
    hass.states.async_set(POWER, 0, {"unit_of_measurement": "W"})
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry, entry.runtime_data


async def test_report_view_needs_login_and_serves_three_forms(hass: HomeAssistant, hass_client, hass_client_no_auth) -> None:
    entry, monitor = await _setup(hass)
    monitor.records.append(dict(REC))
    monitor._recalculate()
    client = await hass_client()
    for variant, text in (("full", "MT1 veranda"), ("anonymous", "Dit deel je"), ("marstek", "Battery capacity report")):
        resp = await client.get(f"/api/{DOMAIN}/report/{entry.entry_id}/{variant}")
        assert resp.status == 200
        body = await resp.text()
        assert text in body or text.replace("Dit deel je", "What you share") in body
    assert "MT1 veranda" not in await (await client.get(f"/api/{DOMAIN}/report/{entry.entry_id}/anonymous")).text()
    assert (await client.get(f"/api/{DOMAIN}/report/{entry.entry_id}/other")).status == 404
    anon = await hass_client_no_auth()
    assert (await anon.get(f"/api/{DOMAIN}/report/{entry.entry_id}/full")).status == 401


async def test_signed_link_opens_the_report(hass: HomeAssistant, hass_client_no_auth, hass_admin_user) -> None:
    from homeassistant.components.http.auth import async_sign_path

    entry, _ = await _setup(hass)
    token = await hass.auth.async_create_refresh_token(hass_admin_user, "client")
    path = async_sign_path(hass, f"/api/{DOMAIN}/report/{entry.entry_id}/full", timedelta(minutes=5),
                           refresh_token_id=token.id)
    client = await hass_client_no_auth()
    resp = await client.get(path)
    assert resp.status == 200 and "MT1 veranda" in await resp.text()


async def test_diagnostics_hide_the_name(hass: HomeAssistant) -> None:
    from custom_components.marstek_capacity_monitor.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    entry, monitor = await _setup(hass)
    monitor.records.append(dict(REC))
    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert "MT1 veranda" not in str(diag)
    assert diag["export"]["data"]["records"][0]["e_dc_kwh"] == 4.40
    assert diag["export"]["variant"] == "diagnostics"


@contextmanager
def _upload(path: Path):
    yield path


async def test_restore_from_report_merges_and_backs_up_first(hass: HomeAssistant, tmp_path) -> None:
    entry, monitor = await _setup(hass)
    monitor.records.append(dict(REC))
    report = monitor.report_html("full")
    # start over, as after a fresh installation
    await monitor.async_reset()
    assert monitor.records == []
    file = tmp_path / "backup.html"
    file.write_text(report, encoding="utf-8")

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "restore"})
    assert result["step_id"] == "restore"
    with patch("homeassistant.components.file_upload.process_uploaded_file", return_value=_upload(file)):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"file": "0123456789abcdef0123456789abcdef", "mode": "merge"}
        )
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "restored"
    assert result["description_placeholders"]["full"] == "1"
    assert len(entry.runtime_data.records) == 1
    backups = list(Path(hass.config.path(f"{DOMAIN}/backup")).glob("mt1-before-restore-*.html"))
    assert backups


async def test_restore_rejects_a_foreign_file(hass: HomeAssistant, tmp_path) -> None:
    entry, _ = await _setup(hass)
    file = tmp_path / "x.html"
    file.write_text("<html>not ours</html>", encoding="utf-8")
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "restore"})
    with patch("homeassistant.components.file_upload.process_uploaded_file", return_value=_upload(file)):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"file": "0123456789abcdef0123456789abcdef", "mode": "replace"}
        )
    assert result["type"] is FlowResultType.FORM and result["errors"] == {"base": "restore_invalid"}


async def test_converting_stored_data_writes_a_backup_first(hass: HomeAssistant) -> None:
    entry, monitor = await _setup(hass)
    data = monitor._data()
    data["records"] = [dict(REC)]
    out = await monitor._store._async_migrate_func(0, 1, data)
    assert out["records"][0]["e_dc_kwh"] == 4.40
    assert list(Path(hass.config.path(f"{DOMAIN}/backup")).glob("mt1-before-update-v0.1-*.html"))


async def test_share_code_stays_the_same(hass: HomeAssistant) -> None:
    entry, monitor = await _setup(hass)
    code = monitor.share_id
    await monitor._store.async_save(monitor._data())
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.runtime_data.share_id == code
