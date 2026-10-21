"""Every translation must have exactly the keys and placeholders of strings.json."""

import json
import re
from pathlib import Path

import pytest

COMPONENT = Path(__file__).resolve().parent.parent / "custom_components" / "marstek_capacity_monitor"
STRINGS = json.loads((COMPONENT / "strings.json").read_text(encoding="utf-8"))
LANGS = sorted(p.stem for p in (COMPONENT / "translations").glob("*.json"))


def _flat(obj, prefix=""):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield from _flat(value, f"{prefix}.{key}" if prefix else key)
    else:
        yield prefix, obj


def test_languages_present():
    assert {"en", "nl", "de"} <= set(LANGS)


@pytest.mark.parametrize("lang", LANGS)
def test_same_keys_and_placeholders(lang):
    ref = dict(_flat(STRINGS))
    data = dict(_flat(json.loads((COMPONENT / "translations" / f"{lang}.json").read_text(encoding="utf-8"))))
    assert set(data) == set(ref), f"{lang}: missing {set(ref) - set(data)}, extra {set(data) - set(ref)}"
    for key, text in ref.items():
        assert data[key].strip(), f"{lang}: {key} is empty"
        assert set(re.findall(r"{\w+}", data[key])) == set(re.findall(r"{\w+}", text)), (
            f"{lang}: placeholders differ in {key}"
        )


def test_card_has_every_language():
    """The cards know the same languages as the integration (en, nl, de)."""
    card = (COMPONENT / "frontend" / "marstek-capacity-card.js").read_text(encoding="utf-8")
    for loc in ("nl-NL", "de-DE", "en-GB"):
        assert loc in card
