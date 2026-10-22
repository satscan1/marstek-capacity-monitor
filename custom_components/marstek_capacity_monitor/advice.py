"""Texts of the "let op" and advice messages (phone, Repairs), in nl/en/de.

The cards have their own texts (button-card templates); these are for the
messages Home Assistant sends.
"""

from __future__ import annotations

from typing import Any

from .const import KIND_CELLS, MODEL_UPS

TITLE = "Marstek Capacity Monitor"

DISMISS = {"nl": "Wegklikken", "en": "Dismiss", "de": "Ausblenden"}

_SOC = {
    "nl": {
        "letop": "{name}: let op, de SOC-meter zat de laatste tijd 2× flink ernaast{last}. "
        "Om SOC-drift te voorkomen: ontlaad de batterij één keer tot de ontlaadgrens en laad "
        "hem daarna in één keer vol, tot het laden echt stopt.",
        "advies": "{name}: SOC-drift geconstateerd, de SOC-meter zat {count}× in 45 dagen flink "
        "ernaast{last}. Advies: ontlaad de batterij twee keer tot de ontlaadgrens en laad hem "
        "elke keer in één keer vol, tot het laden echt stopt.",
        "last": " (laatst {dev} %)",
    },
    "en": {
        "letop": "{name}: attention, the SOC meter was clearly off twice recently{last}. "
        "To prevent SOC drift: discharge the battery once down to the discharge limit, then "
        "charge it to full in one go, until charging really stops.",
        "advies": "{name}: SOC drift detected, the SOC meter was clearly off {count}× in 45 "
        "days{last}. Advice: discharge the battery twice down to the discharge limit and charge "
        "it to full in one go each time, until charging really stops.",
        "last": " (last {dev} %)",
    },
    "de": {
        "letop": "{name}: Achtung, die SOC-Anzeige lag zuletzt 2× deutlich daneben{last}. "
        "Um SOC-Drift vorzubeugen: entlade die Batterie einmal bis zur Entladegrenze und lade sie "
        "danach in einem Zug voll, bis das Laden wirklich stoppt.",
        "advies": "{name}: SOC-Drift festgestellt, die SOC-Anzeige lag {count}× in 45 Tagen "
        "deutlich daneben{last}. Empfehlung: entlade die Batterie zweimal bis zur Entladegrenze "
        "und lade sie jedes Mal in einem Zug voll, bis das Laden wirklich stoppt.",
        "last": " (zuletzt {dev} %)",
    },
}

_CELLS = {
    "nl": {
        "letop": "{name}: let op, het celverschil na volle lading is 2× hoger dan normaal "
        "({mv} mV, normaal {base} mV). Laad de batterij vol en laat hem ongeveer 4 uur vol staan{ups4}.",
        "advies": "{name}: celverschil na volle lading {count}× in 45 dagen 2× hoger dan normaal "
        "({mv} mV, normaal {base} mV). Advies: celkalibratie — {how8} Blijft het celverschil "
        "daarna hoog, meld het dan via de Marstek-app.",
        "ups4_yes": " (zet in de Marstek-app UPS-modus 4 uur aan en daarna terug naar je eigen modus)",
        "ups4_maybe": " (UPS-modus 4 uur aan als je model dat heeft)",
        "how8_ups": "laad vol en zet in de Marstek-app UPS-modus 8 uur aan (heeft je model geen "
        "UPS-modus: laat hem 8 uur in de laadmodus staan), zet hem daarna terug naar je eigen modus.",
        "how8": "laad vol en laat hem 8 uur in de laadmodus staan (of UPS-modus, als je model dat "
        "heeft), zet hem daarna terug naar je eigen modus.",
    },
    "en": {
        "letop": "{name}: attention, the cell spread after a full charge is 2× higher than normal "
        "({mv} mV, normally {base} mV). Charge the battery to full and keep it full for about 4 hours{ups4}.",
        "advies": "{name}: cell spread after a full charge {count}× in 45 days 2× higher than "
        "normal ({mv} mV, normally {base} mV). Advice: cell calibration — {how8} If the spread "
        "stays high after that, report it via the Marstek app.",
        "ups4_yes": " (switch on UPS mode in the Marstek app for 4 hours, then back to your own mode)",
        "ups4_maybe": " (UPS mode for 4 hours if your model has it)",
        "how8_ups": "charge to full and switch on UPS mode in the Marstek app for 8 hours (no UPS "
        "mode on your model: leave it in charge mode for 8 hours), then back to your own mode.",
        "how8": "charge to full and leave it in charge mode for 8 hours (or UPS mode, if your "
        "model has it), then back to your own mode.",
    },
    "de": {
        "letop": "{name}: Achtung, die Zellspannungsdifferenz nach Vollladung ist 2× höher als "
        "normal ({mv} mV, normal {base} mV). Lade die Batterie voll und lass sie etwa 4 Stunden voll stehen{ups4}.",
        "advies": "{name}: Zellspannungsdifferenz nach Vollladung {count}× in 45 Tagen 2× höher "
        "als normal ({mv} mV, normal {base} mV). Empfehlung: Zellkalibrierung — {how8} Bleibt die "
        "Differenz danach hoch, melde es über die Marstek-App.",
        "ups4_yes": " (in der Marstek-App den UPS-Modus 4 Stunden einschalten, danach zurück in deinen Modus)",
        "ups4_maybe": " (UPS-Modus 4 Stunden, wenn dein Modell ihn hat)",
        "how8_ups": "lade voll und schalte in der Marstek-App den UPS-Modus 8 Stunden ein (kein "
        "UPS-Modus: lass sie 8 Stunden im Lademodus), danach zurück in deinen Modus.",
        "how8": "lade voll und lass sie 8 Stunden im Lademodus (oder UPS-Modus, wenn dein Modell "
        "ihn hat), danach zurück in deinen Modus.",
    },
}


def lang_of(language: str | None) -> str:
    code = (language or "en")[:2]
    return code if code in ("nl", "de") else "en"


def _num(value: float | None, lang: str, digits: int = 0) -> str:
    if value is None:
        return "?"
    text = f"{value:.{digits}f}"
    return text.replace(".", ",") if lang in ("nl", "de") else text


def message(kind: str, level: str, name: str, result: dict[str, Any], model: str | None, language: str | None) -> str:
    lang = lang_of(language)
    if kind == KIND_CELLS:
        t = _CELLS[lang]
        ups = MODEL_UPS.get(model or "", False)
        ups4 = t["ups4_yes"] if ups is True else t["ups4_maybe"] if ups is None else ""
        how8 = t["how8_ups"] if ups in (True, None) else t["how8"]
        return t[level].format(
            name=name,
            count=result.get("count") or 3,
            mv=_num(result.get("last_size"), lang),
            base=_num(result.get("base_mv"), lang),
            ups4=ups4,
            how8=how8,
        )
    t = _SOC[lang]
    size = result.get("last_size")
    last = t["last"].format(dev=_num(size, lang)) if size else ""
    return t[level].format(name=name, count=result.get("count") or 3, last=last)
