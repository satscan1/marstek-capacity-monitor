"""Back-up, export and report (0.5.5): one format, three forms, restore."""

import importlib.util
from pathlib import Path
import sys

import pytest

_spec = importlib.util.spec_from_file_location(
    "mcm_export",
    Path(__file__).parents[1] / "custom_components/marstek_capacity_monitor/export.py",
)
ex = importlib.util.module_from_spec(_spec)
sys.modules["mcm_export"] = ex
_spec.loader.exec_module(ex)

BATTERY = {
    "name": "MT1 veranda", "battery_id": "mt1", "share_id": "a1b2c3d4e5", "model": "venus_e_v12",
    "nominal_kwh": 5.12, "reserve_kwh": 0.56, "usable_kwh": 4.56, "purchase_date": "2024-02-14",
    "warranty_years": 10, "cycle_life": 6000, "cycle_eol_pct": 80, "red_pct": 75, "tolerance_pct": 5,
    "initial_cycles": 352, "initial_cycles_from_counter": False, "power_sign": "auto_normal",
    "connection": "esphome", "has_cells": True, "has_temps": True, "soc_sensitivity": "normal",
    "cell_sensitivity": "normal", "notify": True,
    "soc_entity": "sensor.venus_5_12kwh_veranda_marstek_battery_state_of_charge",
    "power_entity": "sensor.venus_5_12kwh_veranda_marstek_battery_power",
}
REC = {"ts": 1792000000.0, "start_ts": 1791980000.0, "direction": "discharge", "soc_start": 100,
       "soc_end": 11, "delta_soc": 89, "duration_min": 330, "e_dc_kwh": 4.366, "valid": True,
       "reason": None, "temp_c": 14.0, "steps": [[100, 0.0]], "edge_ratio": 1.1}
DATA = {
    "tracker": {"soc": 50}, "records": [REC], "cells": {"armed": True}, "cell_records": [],
    "history_until": None, "health": {}, "soc_events": [{"ts": 1792000100.0, "type": "top"}],
    "full_days": ["2026-10-22"], "alive_days": ["2026-10-22"], "soc_since": 1791000000.0,
    "dismissed": {"soc": 1.0}, "notified": {}, "share_id": "a1b2c3d4e5",
}
SUMMARY = {"measured_kwh": 4.37, "measured_pct": 95.8, "expected_pct": 98.6, "status": "good",
           "display_state": "normal", "since_start_pct": None, "trend": [], "soc": {}, "cells": {},
           "monitor": {"state": "measuring"}, "history": [{"date": "x"}]}
META = {"created": "2026-10-26T13:00:00+01:00", "app_version": "0.5.5", "ha_version": "2026.10.2", "language": "nl"}


def test_full_keeps_everything_and_round_trips_through_the_report():
    full = ex.build("full", BATTERY, DATA, SUMMARY, META)
    assert full["format"] == ex.FORMAT and full["schema"] == ex.SCHEMA
    assert full["battery"]["name"] == "MT1 veranda"
    assert full["data"]["tracker"] == {"soc": 50}
    html = ex.render_html(full)
    assert "MT1 veranda" in html and "Rapport downloaden" in html
    back = ex.parse(html)
    assert back["data"]["records"][0]["e_dc_kwh"] == 4.366
    assert back["battery"]["purchase_date"] == "2024-02-14"


@pytest.mark.parametrize("variant", ["anonymous", "marstek"])
def test_shared_forms_hold_no_names_or_ids(variant):
    out = ex.build(variant, BATTERY, DATA, SUMMARY, META)
    blob = ex.render_html(out)
    for secret in ("MT1 veranda", "veranda", "mt1", "sensor.", "2024-02-14", "dismissed", "tracker"):
        assert secret not in blob, secret
    assert out["battery"]["purchase_month"] == "2024-02"
    assert out["battery"]["share_id"] == "a1b2c3d4e5"
    assert "steps" not in out["data"]["records"][0]
    assert "history" not in out["summary"]


def test_anonymous_says_what_you_share_and_marstek_is_english():
    anon = ex.render_html(ex.build("anonymous", BATTERY, DATA, SUMMARY, META))
    assert "Dit deel je" in anon
    marstek = ex.render_html(ex.build("marstek", BATTERY, DATA, SUMMARY, META))
    assert "Battery capacity report" in marstek and "A tool, not proof" in marstek


def test_parse_rejects_other_files_and_newer_versions():
    with pytest.raises(ex.ExportError):
        ex.parse("<html><body>hello</body></html>")
    with pytest.raises(ex.ExportError):
        ex.parse('{"format": "something-else"}')
    with pytest.raises(ex.ExportError):
        ex.parse('{"format": "%s", "schema": 99}' % ex.FORMAT)
    # plain JSON works too
    assert ex.parse('{"format": "%s", "schema": 1, "data": {}}' % ex.FORMAT)["schema"] == 1


def test_merge_keeps_both_and_replace_takes_the_file():
    now = {"records": [REC], "soc_events": [], "full_days": ["2026-10-22"], "tracker": {"soc": 70},
           "dismissed": {"soc": 2.0}}
    older = dict(REC, ts=1780000000.0)
    file = {"records": [older, REC], "soc_events": [{"ts": 5.0, "type": "top"}],
            "full_days": ["2026-06-01"], "tracker": {"soc": 10}, "dismissed": {}}
    merged = ex.merge(now, file, "merge")
    assert [r["ts"] for r in merged["records"]] == [1780000000.0, 1792000000.0]
    assert merged["full_days"] == ["2026-06-01", "2026-10-22"]
    assert merged["tracker"] == {"soc": 70} and merged["dismissed"] == {"soc": 2.0}
    replaced = ex.merge(now, file, "replace")
    assert replaced["tracker"] == {"soc": 10} and len(replaced["records"]) == 2


def test_the_report_cannot_be_broken_by_text_in_the_data():
    bat = dict(BATTERY, name="</script><b>x</b>")
    html = ex.render_html(ex.build("full", bat, DATA, SUMMARY, META))
    assert html.count("</script>") == 2  # data block and download script only
    assert ex.parse(html)["battery"]["name"] == "</script><b>x</b>"
