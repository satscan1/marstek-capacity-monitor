"""The integration's own card: up to date with the templates, served, and laid out right."""

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("build_card", ROOT / "scripts" / "build_card.py")
build_card = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_card)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


def test_card_is_up_to_date():
    assert build_card.OUT.read_text(encoding="utf-8") == build_card.build(), (
        "run scripts/build_card.py"
    )


async def test_card_is_loaded_on_every_page(hass: HomeAssistant) -> None:
    from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL

    assert await async_setup_component(hass, "marstek_capacity_monitor", {})
    await hass.async_block_till_done()
    version = json.loads(build_card.MANIFEST.read_text())["version"]
    urls = hass.data[DATA_EXTRA_MODULE_URL].urls
    import hashlib
    tag = hashlib.sha1(build_card.OUT.read_bytes()).hexdigest()[:8]
    assert f"/marstek_capacity_monitor_frontend/marstek-capacity-card.js?v={version}-{tag}" in urls


NODE_TEST = r"""
const fs = require("fs");
global.HTMLElement = class {};
const defined = {};
global.customElements = { get: (n) => defined[n], define: (n, c) => { defined[n] = c; } };
global.window = {};
global.console = { info() {}, log: console.log };
eval(fs.readFileSync(process.argv[2], "utf8"));
(async () => {
  const S = defined["ll-strategy-dashboard-marstek-capacity"];
  const out = {};
  for (let n = 0; n <= 6; n++) {
    const entities = {}, devices = {};
    for (let i = 1; i <= n; i++) {
      entities[`sensor.marstek_mt${i}_monitor_status`] = { platform: "marstek_capacity_monitor", device_id: `d${i}` };
      entities[`sensor.marstek_mt${i}_capacity_pct`] = { platform: "marstek_capacity_monitor", device_id: `d${i}` };
      devices[`d${i}`] = { name: `MT${i}`, name_by_user: i === 2 ? "Garage" : null };
    }
    entities["sensor.other"] = { platform: "esphome" };
    const cfg = await S.generate({}, { entities, devices, locale: { language: "nl" } });
    out[n] = cfg.views[0].sections[0].cards.map((c) => [c.type, (c.grid_options || {}).columns || null, c.battery || null, c.name || null]);
  }
  out.titles = {};
  for (const lang of ["en", "nl", "de", "fr"]) {
    const cfg = await S.generate({}, { entities: {}, devices: {}, locale: { language: lang } });
    out.titles[lang] = cfg.title;
  }
  out.cards = window.customCards.map((c) => c.type);
  out.strategies = window.customStrategies.map((s) => [s.type, s.strategyType]);
  process.stdout.write(JSON.stringify(out));
})();
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_dashboard_layout_for_1_to_6_batteries(tmp_path):
    script = tmp_path / "t.js"
    script.write_text(NODE_TEST)
    out = json.loads(subprocess.run(
        ["node", str(script), str(build_card.OUT)], capture_output=True, text=True, check=True
    ).stdout)
    B, O, M = "custom:marstek-capacity-card", "custom:marstek-capacity-overview-card", "markdown"
    assert out["0"] == [[M, None, None, None]]
    assert out["1"] == [[B, 12, "mt1", "MT1"], [O, 12, None, None]]
    assert out["2"] == [[B, 12, "mt1", "MT1"], [B, 12, "mt2", "Garage"], [O, 12, None, None]]
    for n, width in ((3, 12), (4, 18), (5, 12), (6, 12)):
        cards = out[str(n)]
        assert cards[0] == [O, 24, None, None] and cards[1][:2] == [M, 12]
        assert [c[2] for c in cards[2:]] == [f"mt{i}" for i in range(1, n + 1)]
        assert all(c[1] == width for c in cards[2:])
    assert out["titles"] == {"en": "Battery capacity", "nl": "Batterijcapaciteit",
                             "de": "Batteriekapazität", "fr": "Battery capacity"}
    assert out["cards"] == ["marstek-capacity-card", "marstek-capacity-overview-card"]
    assert out["strategies"] == [["marstek-capacity", "dashboard"]]


ACTION_TEST = r"""
const fs = require("fs");
global.HTMLElement = class {};
const defined = {};
global.customElements = { get: (n) => defined[n], define: (n, c) => { defined[n] = c; } };
global.window = {};
global.console = { info() {}, log: console.log };
eval(fs.readFileSync(process.argv[2], "utf8"));
const S = {
  "sensor.marstek_mt1_measured_capacity": { state: "4.4", attributes: { trend: [] } },
  "sensor.marstek_mt1_capacity_pct": { state: "97", attributes: {} },
  "sensor.marstek_mt1_expected_capacity": { state: "96", attributes: {} },
  "sensor.marstek_mt1_soc_health": { state: "advies", attributes: { count: 3, last_size: 12, trend: [] } },
  "sensor.marstek_mt1_cell_health": { state: "ok", attributes: { trend: [] } },
};
const card = new defined["marstek-capacity-card"]();
const calls = [];
card._config = { battery: "mt1" };
card._hass = { states: S, entities: {}, devices: {}, callService: (...a) => calls.push(a) };
const out = {};
const acts = (html) => [...html.matchAll(/data-mc="([^"]*)"/g)].map((m) => m[1]);
const pills = (html) => acts(html).filter((a) => a.includes("_mcPanel"));
out.closed = pills(card._html()).length;
out.closedHasAdvice = /twice/.test(card._html());
card._action(pills(card._html())[1]);
out.panel = card._panel;
const html = card._html();
out.advice = html.includes("twice") && html.includes("position:fixed");
card._action(acts(html).find((a) => a.includes("dismiss_advice")));
out.calls = calls;
card._action(pills(card._html())[1]);
out.closedAgain = card._panel;
process.stdout.write(JSON.stringify(out));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_card_buttons_open_panels_and_dismiss(tmp_path):
    script = tmp_path / "t.js"
    script.write_text(ACTION_TEST)
    out = json.loads(subprocess.run(
        ["node", str(script), str(build_card.OUT)], capture_output=True, text=True, check=True
    ).stdout)
    assert out["closed"] == 3  # Chart · SOC · Cells
    assert not out["closedHasAdvice"]  # SOC and Cells only open as a popup
    assert out["panel"] == "soc"
    assert out["advice"]
    assert out["calls"] == [["marstek_capacity_monitor", "dismiss_advice", {"battery": "mt1", "kind": "soc"}]]
    assert out["closedAgain"] == ""


TEXT_TEST = r"""
const fs = require("fs");
global.HTMLElement = class {};
const defined = {};
global.customElements = { get: (n) => defined[n], define: (n, c) => { defined[n] = c; } };
global.window = {};
global.console = { info() {}, log: console.log };
eval(fs.readFileSync(process.argv[2], "utf8"));
const S = {
  "sensor.marstek_mt1_measured_capacity": { state: "4.4", attributes: { trend: [], measurement_count: 3 } },
  "sensor.marstek_mt1_capacity_pct": { state: "97", attributes: {} },
  "sensor.marstek_mt1_expected_capacity": { state: "96", attributes: {
    cycles: 400, initial_cycles: 352, cycle_counter: "sensor.x_total_discharging_energy", trend: [] } },
  "sensor.marstek_mt1_monitor_status": { state: "measuring", attributes: {} },
};
const out = {};
for (const [lang, cfg] of [["nl", {}], ["de", {}], ["nl", { lang: "en" }]]) {
  const card = new defined["marstek-capacity-card"]();
  card._config = { battery: "mt1", ...cfg };
  card._hass = { states: S, entities: {}, devices: {}, locale: { language: lang }, language: lang };
  out[lang + (cfg.lang || "")] = card._html();
}
process.stdout.write(JSON.stringify(out));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_card_language_foot_and_cycles_note(tmp_path):
    script = tmp_path / "t.js"
    script.write_text(TEXT_TEST)
    out = json.loads(subprocess.run(
        ["node", str(script), str(build_card.OUT)], capture_output=True, text=True, check=True
    ).stdout)
    # Language follows Home Assistant unless the card sets one
    assert "cycli" in out["nl"] and "Zyklen" in out["de"] and "cycles" in out["nlen"]
    # No "n=" for users in the foot line
    assert "n=" not in out["nl"]
    # Cycles before monitoring: from the counter, AC side, an estimate
    assert "Waarvan 352 vóór de monitoring" in out["nl"] and "AC-kant" in out["nl"]
    assert "AC side" in out["nlen"]
