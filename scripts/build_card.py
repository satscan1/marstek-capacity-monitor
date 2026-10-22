"""Build the integration's own Lovelace card from the button-card templates.

The card logic lives in one place: dashboard/button-card/marstek_capacity_templates.yaml.
This script copies the JavaScript of the battery card and the overview card into
custom_components/marstek_capacity_monitor/frontend/marstek-capacity-card.js and
adds the glue for a normal custom card (no button-card needed). Run it after
changing the templates:

    python scripts/build_card.py

tests/test_card.py fails when the card is out of date.
"""

from __future__ import annotations

import json
from pathlib import Path
import re

import yaml

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "dashboard" / "button-card" / "marstek_capacity_templates.yaml"
MANIFEST = ROOT / "custom_components" / "marstek_capacity_monitor" / "manifest.json"
OUT = ROOT / "custom_components" / "marstek_capacity_monitor" / "frontend" / "marstek-capacity-card.js"

# (old, new): the only changes to the template code. Each must occur exactly once.
BATTERY_EDITS = [
    (
        "const panel = (this && this._mcPanel) || '';",
        "const panel = ctx.panel || '';",
    ),
    (
        "const gone = (this && this._mcGone) || '';",
        "const gone = ctx.gone || '';",
    ),
    (
        'const act = js => `onclick="event.stopPropagation();const h=this.getRootNode().host;${js}h._config={...h._config};"`;',
        "const act = js => `data-mc=\"${js}\"`;",
    ),
    (
        "((this && this.offsetWidth) || 360)",
        "(ctx.width || 360)",
    ),
]


def _body(template: str) -> str:
    src = yaml.safe_load(TEMPLATES.read_text(encoding="utf-8"))["button_card_templates"][
        template
    ]["custom_fields"]["body"].strip()
    assert src.startswith("[[[") and src.endswith("]]]"), template
    return src[3:-3].strip("\n")


def battery_body() -> str:
    code = _body("marstek_capacity_battery")
    for old, new in BATTERY_EDITS:
        assert code.count(old) == 1, old
        code = code.replace(old, new)
    assert not re.search(r"\bthis\b\s*(\.|&&|\))", code), "template code still uses `this`"
    return code


def overview_body() -> str:
    code = _body("marstek_capacity_overview")
    assert not re.search(r"\bthis\b\s*(\.|&&|\))", code)
    return code


def build() -> str:
    version = json.loads(MANIFEST.read_text(encoding="utf-8"))["version"]
    return (
        (ROOT / "scripts" / "card_glue.js")
        .read_text(encoding="utf-8")
        .replace("__VERSION__", version)
        .replace("/*__BATTERY_BODY__*/", battery_body())
        .replace("/*__OVERVIEW_BODY__*/", overview_body())
    )


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(), encoding="utf-8")
    print(OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
