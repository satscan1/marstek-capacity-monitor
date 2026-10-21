"""The ready-made dashboards must match the templates and the layout rules."""

import importlib.util
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "build_ready_dashboards", ROOT / "scripts" / "build_ready_dashboards.py"
)
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)


def test_files_are_up_to_date():
    for path, text in build.expected().items():
        assert path.exists(), f"missing {path}: run scripts/build_ready_dashboards.py"
        assert path.read_text(encoding="utf-8") == text, (
            f"{path.name} is out of date: run scripts/build_ready_dashboards.py"
        )


@pytest.mark.parametrize("lang", ["en", "nl"])
@pytest.mark.parametrize("n", range(1, 7))
def test_layout(n, lang):
    cfg = yaml.safe_load(build.build(n, lang))
    templates = yaml.safe_load(build.TEMPLATES.read_text(encoding="utf-8"))
    assert cfg["button_card_templates"] == templates["button_card_templates"]

    (v,) = cfg["views"]
    assert v["type"] == "sections" and v["max_columns"] == 3
    (section,) = v["sections"]
    assert section["column_span"] == 3
    cards = section["cards"]

    batteries = [c for c in cards if c.get("template") == "marstek_capacity_battery"]
    (overview,) = [c for c in cards if c.get("template") == "marstek_capacity_overview"]
    assert [c["variables"]["battery"] for c in batteries] == [f"mt{i}" for i in range(1, n + 1)]
    assert [b["id"] for b in overview["variables"]["batteries"]] == [
        f"mt{i}" for i in range(1, n + 1)
    ]
    assert all(c["variables"]["lang"] == lang for c in batteries)
    assert overview["variables"]["lang"] == lang

    widths = [c["grid_options"]["columns"] for c in cards]
    if n <= 2:
        assert cards[-1] is overview
        assert widths == [12] * (n + 1)
        assert overview["variables"]["months"] == 3
    else:
        assert cards[0] is overview and cards[1]["type"] == "markdown"
        battery_width = 18 if n == 4 else 12
        assert widths == [24, 12] + [battery_width] * n
        assert overview["variables"]["months"] == 6

    for c in batteries:
        bid = c["variables"]["battery"]
        assert f"sensor.marstek_{bid}_capacity_pct" in c["triggers_update"]
    for i in range(1, n + 1):
        assert f"sensor.marstek_mt{i}_monitor_status" in overview["triggers_update"]
