"""Back-up, export and report of the monitor's own data (0.5.5).

No Home Assistant dependency: the integration collects the data, this module
turns it into one file and back.

One format, three forms:

* full        - back-up: everything, also names and the running measurement;
                can be restored (merge or replace)
* anonymous   - to share: no names, entity ids or installation ids; the
                battery gets a random fixed code; installation date as year
                and month only
* marstek     - the readable part that matters for a report to Marstek:
                summary, capacity per month, measurements

The file is an HTML report in the house style (as the HESC report) with the
data embedded as JSON. A person reads the report; the monitor (restore) and
the shared collection read the embedded data. What you see is what you share.

`schema` is the version of the format. A newer monitor always reads an older
file: one converter per step in MIGRATIONS (1 -> 2 -> ...).
"""

from __future__ import annotations

from datetime import datetime
from html import escape
import json
import re
from typing import Any, Callable

FORMAT = "marstek-capacity-monitor-export"
SCHEMA = 1
VARIANTS = ("full", "anonymous", "marstek")

# Parts of the stored data, per form
DATA_KEYS_FULL = (
    "tracker",
    "records",
    "cells",
    "cell_records",
    "history_until",
    "health",
    "soc_events",
    "full_days",
    "alive_days",
    "soc_since",
    "dismissed",
    "notified",
)
DATA_KEYS_SHARED = ("records", "cell_records", "soc_events", "full_days", "alive_days", "soc_since")
DATA_KEYS_MARSTEK = ("records",)

# Battery settings that never point to a person or an installation
BATTERY_KEYS_SHARED = (
    "model",
    "nominal_kwh",
    "reserve_kwh",
    "usable_kwh",
    "purchase_month",
    "warranty_years",
    "cycle_life",
    "cycle_eol_pct",
    "red_pct",
    "tolerance_pct",
    "initial_cycles",
    "initial_cycles_from_counter",
    "power_sign",
    "connection",
    "has_cells",
    "has_temps",
    "soc_sensitivity",
    "cell_sensitivity",
    "notify",
)
# Summary keys kept in the shared forms (all numbers, no names)
SUMMARY_KEYS = (
    "measured_kwh",
    "measured_pct",
    "expected_pct",
    "expected_kwh",
    "margin_kwh",
    "cycles",
    "age_years",
    "status",
    "display_state",
    "baseline_pct",
    "since_start_pct",
    "confirm_count",
    "drop_ref_pct",
    "trend",
    "soc",
    "cells",
    "monitor",
)

_SCRIPT_ID = "mcm-data"

MODEL_NAMES = {
    "venus_e_v12": "Venus E v1 / v2",
    "venus_c": "Venus C",
    "venus_e_v3": "Venus E v3",
    "venus_e_v4": "Venus E 4.0",
    "venus_e_max": "Venus E Max",
    "venus_e_pro": "Venus E Pro",
    "venus_d": "Venus D",
    "other": "–",
}


class ExportError(ValueError):
    """The file is not a monitor export, or from a newer monitor."""


# ---------------------------------------------------------------------------
# Building
# ---------------------------------------------------------------------------


def build(
    variant: str,
    battery: dict[str, Any],
    data: dict[str, Any],
    summary: dict[str, Any],
    meta: dict[str, Any],
) -> dict[str, Any]:
    """One export. `battery` holds every setting (full form); the shared forms
    keep only BATTERY_KEYS_SHARED and the share code."""
    if variant not in VARIANTS:
        raise ExportError(f"unknown variant {variant}")
    out: dict[str, Any] = {
        "format": FORMAT,
        "schema": SCHEMA,
        "variant": variant,
        "created": meta.get("created"),
        "app_version": meta.get("app_version"),
        "ha_version": meta.get("ha_version"),
        "language": meta.get("language"),
    }
    purchase = battery.get("purchase_date")
    bat = dict(battery)
    bat["purchase_month"] = str(purchase)[:7] if purchase else None
    if variant == "full":
        out["battery"] = bat
        out["data"] = {k: data.get(k) for k in DATA_KEYS_FULL if k in data}
        out["summary"] = _jsonable(summary)
        return out
    shared = {k: bat.get(k) for k in BATTERY_KEYS_SHARED}
    shared["share_id"] = battery.get("share_id")
    out["battery"] = shared
    keys = DATA_KEYS_SHARED if variant == "anonymous" else DATA_KEYS_MARSTEK
    out["data"] = {k: _strip(k, data.get(k)) for k in keys if k in data}
    out["summary"] = {k: _jsonable(summary.get(k)) for k in SUMMARY_KEYS if k in summary}
    return out


def _strip(key: str, value: Any) -> Any:
    """Records only hold numbers, times and reasons; drop nothing but the
    replay marker detail that could hint at the set-up."""
    if key == "records" and isinstance(value, list):
        return [{k: v for k, v in r.items() if k != "steps"} for r in value]
    return value


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


# ---------------------------------------------------------------------------
# Reading, converting, merging
# ---------------------------------------------------------------------------

# schema N -> N+1. Add a converter here whenever the format changes; never
# remove one, so every old file stays readable.
MIGRATIONS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {}


def migrate(export: dict[str, Any]) -> dict[str, Any]:
    if export.get("format") != FORMAT:
        raise ExportError("not a Marstek Capacity Monitor export")
    schema = int(export.get("schema") or 0)
    if schema > SCHEMA:
        raise ExportError("made by a newer version of the monitor")
    while schema < SCHEMA:
        if schema not in MIGRATIONS:
            raise ExportError(f"no converter from schema {schema}")
        export = MIGRATIONS[schema](export)
        schema += 1
        export["schema"] = schema
    return export


def parse(text: str) -> dict[str, Any]:
    """Read an export: the HTML report (data embedded) or plain JSON."""
    text = text.strip()
    if text.startswith("{"):
        try:
            return migrate(json.loads(text))
        except json.JSONDecodeError as err:
            raise ExportError("not valid JSON") from err
    m = re.search(
        rf'<script type="application/json" id="{_SCRIPT_ID}">(.*?)</script>', text, re.S
    )
    if not m:
        raise ExportError("no monitor data in this file")
    raw = m.group(1).replace("<\\/", "</")
    try:
        return migrate(json.loads(raw))
    except json.JSONDecodeError as err:
        raise ExportError("damaged monitor data") from err


def _union(old: list, new: list, key: Callable[[dict], Any]) -> list:
    seen = {key(r): r for r in old or []}
    for r in new or []:
        seen.setdefault(key(r), r)
    return sorted(seen.values(), key=lambda r: r.get("ts", 0))


def merge(current: dict[str, Any], incoming: dict[str, Any], mode: str) -> dict[str, Any]:
    """New stored data after a restore.

    replace : the file wins (a full back-up also brings the running
              measurement and the state of the notices back)
    merge   : measurements from both, nothing lost; the running measurement
              and the notices stay as they are now
    """
    if mode == "replace":
        out = dict(current)
        for k, v in incoming.items():
            out[k] = v
        return out
    out = dict(current)
    out["records"] = _union(
        current.get("records", []),
        incoming.get("records", []),
        lambda r: (round(r.get("ts", 0)), r.get("direction")),
    )
    out["cell_records"] = _union(
        current.get("cell_records", []), incoming.get("cell_records", []), lambda r: round(r.get("ts", 0))
    )
    out["soc_events"] = _union(
        current.get("soc_events", []),
        incoming.get("soc_events", []),
        lambda r: (round(r.get("ts", 0)), r.get("type")),
    )
    for k in ("full_days", "alive_days"):
        out[k] = sorted(set(current.get(k) or []) | set(incoming.get(k) or []))
    since = [s for s in (current.get("soc_since"), incoming.get("soc_since")) if s]
    out["soc_since"] = min(since) if since else None
    return out


# ---------------------------------------------------------------------------
# Report (HTML, house style of the HESC report)
# ---------------------------------------------------------------------------

_CSS = (
    ":root{--bg:#f6f7f9;--card:#fff;--tx:#1d2330;--mut:#667085;--ln:#e3e6ea;--ac:#1f7ae0;"
    "--ok:#2e9e5b;--wr:#d9822b;--bad:#d64545}"
    "@media (prefers-color-scheme: dark){:root{--bg:#15181e;--card:#1e2128;--tx:#e8eaed;"
    "--mut:#9aa0a6;--ln:#333744;--ac:#42a5f5;--ok:#66bb6a;--wr:#ffa726;--bad:#ef5350}}"
    "*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);"
    "font:14px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}"
    ".wrap{max-width:1100px;margin:0 auto;padding:16px}h1{font-size:22px;margin:0 0 4px}"
    "h2{font-size:16px;margin:24px 0 8px}.sub{color:var(--mut);font-size:13px}"
    ".box{background:var(--card);border:1px solid var(--ln);border-radius:12px;padding:14px;"
    "margin-top:10px;overflow-x:auto}.kpis{display:grid;grid-template-columns:repeat(auto-fit,"
    "minmax(180px,1fr));gap:10px;margin-top:12px}.kpi{background:var(--card);border:1px solid "
    "var(--ln);border-radius:12px;padding:12px}.kl{font-size:11px;letter-spacing:.6px;"
    "color:var(--mut);text-transform:uppercase}.kb{font-size:24px;font-weight:700}"
    ".ks{font-size:12px;color:var(--mut)}table{border-collapse:collapse;width:100%}"
    "td,th{padding:7px 10px;border-top:1px solid var(--ln);text-align:right;white-space:nowrap}"
    "th{color:var(--mut);font-weight:400;font-size:12px;border-top:0}"
    "td:first-child,th:first-child{text-align:left}"
    ".kv td{white-space:normal}.kv td:first-child{color:var(--mut)}.kv td:last-child{font-weight:600}"
    ".ok{color:var(--ok)}.wr{color:var(--wr)}.bad{color:var(--bad)}.mut{color:var(--mut)}"
    ".chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:14px}.chips a{border:1px solid var(--ln);"
    "border-radius:14px;padding:4px 10px;color:var(--tx);text-decoration:none;font-size:12px;"
    "background:var(--card)}.top{display:flex;justify-content:space-between;align-items:flex-start;"
    "gap:12px;flex-wrap:wrap}button{background:var(--ac);color:#fff;border:0;border-radius:8px;"
    "padding:9px 14px;font-weight:600;cursor:pointer}.btns{display:flex;gap:8px;flex-wrap:wrap}"
    "button.sec{background:transparent;color:var(--tx);border:1px solid var(--ln)}.note{border-left:3px solid var(--ac);"
    "padding:10px 12px}.share td:last-child{white-space:normal;text-align:left;font-weight:400}"
    ".in{border-left:4px solid var(--ok);padding:4px 0 4px 12px}.out{border-left:4px solid var(--mut);"
    "padding:4px 0 4px 12px;margin-top:14px;color:var(--mut)}.out ul{margin:6px 0 0;padding-left:18px}"
    ".bh{font-weight:700;margin-bottom:4px}.in .bh{color:var(--ok)}"
    "@media print{button,.chips{display:none}}"
)

_L: dict[str, dict[str, Any]] = {
    "nl": {
        "title": {"full": "Back-up batterijcapaciteit", "anonymous": "Batterijcapaciteit — anoniem om te delen", "marstek": "Battery capacity report"},
        "made": "gemaakt", "download": "Rapport downloaden", "back": "← Terug naar Home Assistant", "share_in": "Dit staat in het bestand", "share_out": "Dit zit er níet in",
        "sec": {"summary": "Samenvatting", "share": "Dit deel je", "months": "Capaciteit per maand",
                "meas": "Metingen (nieuwste eerst)", "soc": "SOC-meter per maand", "cells": "Cellen per maand",
                "settings": "Instellingen", "runtime": "Werking", "about": "Over dit rapport"},
        "chips": {"summary": "Samenvatting", "share": "Dit deel je", "months": "Per maand", "meas": "Metingen",
                  "soc": "SOC", "cells": "Cellen", "settings": "Instellingen", "runtime": "Werking", "about": "Over"},
        "k": {"battery": "Batterij", "model": "Model", "status": "Status", "measured": "Gemeten (midden laatste 3)",
              "expected": "Specificatie fabrikant", "margin": "Marge t.o.v. specificatie", "since": "Sinds begin meting",
              "cycles": "Volle cycli", "age": "Leeftijd", "count": "Volledige ontladingen gemeten",
              "first": "Eerste meting", "last": "Laatste meting", "installed": "Installatie", "code": "Code (anoniem)",
              "nominal": "Opgegeven capaciteit", "usable": "Bruikbaar (100 % van nieuw)", "red": "Rode grens",
              "tol": "Tolerantie", "spec": "Specificatie", "init": "Cycli vóór de monitor",
              "conn": "Koppeling", "sign": "Teken vermogen", "cells": "Celspanning", "temps": "Celtemperatuur",
              "sens": "Gevoeligheid SOC / cellen", "notify": "Seintjes", "app": "Monitor-versie", "ha": "Home Assistant",
              "made": "Gemaakt op", "monitor": "Status meting", "phase": "Volgende stap", "invalid": "Afgekeurde rondes",
              "soc_level": "SOC-drift", "cell_level": "Celkalibratie"},
        "yes": "ja", "no": "nee", "years": "jaar", "cyc": "cycli",
        "after": "{eol} % na {life} cycli",
        "th_months": ["Maand", "Gemeten %", "Spec. %", "Verschil", "Metingen", "Temp.", "Betrouwbaar"],
        "th_meas": ["Datum", "SOC", "DC-energie", "Capaciteit", "% van nieuw", "Temp.", "Betrouwbaar"],
        "th_soc": ["Maand", "Dagen vol", "Grootste afwijking", "Bijladen op 99 %", "Sprong", "Langst niet vol"],
        "th_cells": ["Maand", "Celverschil", "Metingen"],
        "rel": {"yes": "● ja", "no": "○ minder"},
        "why": {"no_calibration": "niet helemaal vol in de 14 dagen ervoor", "cold": "cellen kouder dan 5 °C",
                "soc_edge": "SOC-meter liep aan het begin of eind niet mee"},
        "state": {"good": "Goed", "attention": "Onder specificatie", "critical": "Melden bij Marstek",
                  "no_measurement": "Nog geen meting", "check_model": "Klopt het model?", "unconfirmed": "Nog niet bevestigd"},
        "ds": {"high_provisional": "boven nieuw, voorlopig", "high_confirmed": "boven nieuw, bevestigd (5 metingen)",
               "drop_unconfirmed": "ineens lager, nog niet bevestigd"},
        "level": {"ok": "in orde", "letop": "let op", "advies": "advies"},
        "share": [
            ("Metingen", "elke lading en ontlading: tijd, SOC van/naar, DC-energie, duur, geldig of niet met reden, temperatuur"),
            ("SOC-gebeurtenissen", "ijkpunten, sprongen, bijladen op 99 %, dagen vol"),
            ("Cellen", "celverschil na volle lading (als ingesteld)"),
            ("Batterij", "model, capaciteit, specificatie, installatie als jaar en maand, koppeling"),
            ("Niet", "je naam en de naam van je batterij, sensornamen, codes van je installatie, je adres of woonplaats, weggeklikte meldingen, de lopende meting"),
        ],
        "about_full": "Volledige back-up van de Marstek Capacity Monitor. Terugzetten: Instellingen → Apparaten en diensten → Marstek Capacity Monitor → Configureren → Back-up terugzetten. Bewaar dit bestand zelf; het bevat de namen van je batterij en sensoren.",
        "about_anonymous": "Anonieme versie om te delen, bijvoorbeeld via het formulier \"Share data\" op GitHub. De gegevens staan in dit bestand; wat je hierboven ziet is wat je deelt.",
        "about_marstek": "Measured with Marstek Capacity Monitor on the DC side of the battery (open source, Home Assistant). Full discharges from 95 % or more to 15 % or less; capacity = DC energy divided by the SOC drop, scaled to the usable band. A tool, not proof.",
        "none": "Nog geen gegevens.",
    },
    "en": {
        "title": {"full": "Battery capacity back-up", "anonymous": "Battery capacity — anonymous to share", "marstek": "Battery capacity report"},
        "made": "made", "download": "Download report", "back": "← Back to Home Assistant", "share_in": "This is in the file", "share_out": "This is not in it",
        "sec": {"summary": "Summary", "share": "What you share", "months": "Capacity per month",
                "meas": "Measurements (newest first)", "soc": "SOC meter per month", "cells": "Cells per month",
                "settings": "Settings", "runtime": "Runtime", "about": "About this report"},
        "chips": {"summary": "Summary", "share": "You share", "months": "Per month", "meas": "Measurements",
                  "soc": "SOC", "cells": "Cells", "settings": "Settings", "runtime": "Runtime", "about": "About"},
        "k": {"battery": "Battery", "model": "Model", "status": "Status", "measured": "Measured (middle of last 3)",
              "expected": "Manufacturer spec", "margin": "Margin to spec", "since": "Since monitoring began",
              "cycles": "Full cycles", "age": "Age", "count": "Full discharges measured",
              "first": "First measurement", "last": "Latest measurement", "installed": "Installed", "code": "Code (anonymous)",
              "nominal": "Rated capacity", "usable": "Usable (100 % of new)", "red": "Red threshold",
              "tol": "Tolerance", "spec": "Spec", "init": "Cycles before the monitor",
              "conn": "Connection", "sign": "Power sign", "cells": "Cell voltage", "temps": "Cell temperature",
              "sens": "Sensitivity SOC / cells", "notify": "Notifications", "app": "Monitor version", "ha": "Home Assistant",
              "made": "Made on", "monitor": "Monitor status", "phase": "Next step", "invalid": "Rejected swings",
              "soc_level": "SOC drift", "cell_level": "Cell calibration"},
        "yes": "yes", "no": "no", "years": "years", "cyc": "cycles",
        "after": "{eol} % after {life} cycles",
        "th_months": ["Month", "Measured %", "Spec %", "Difference", "Measurements", "Temp.", "Reliable"],
        "th_meas": ["Date", "SOC", "DC energy", "Capacity", "% of new", "Temp.", "Reliable"],
        "th_soc": ["Month", "Days full", "Largest deviation", "Top-up at 99 %", "Jump", "Longest not full"],
        "th_cells": ["Month", "Cell spread", "Measurements"],
        "rel": {"yes": "● yes", "no": "○ less"},
        "why": {"no_calibration": "not completely full in the 14 days before", "cold": "cells colder than 5 °C",
                "soc_edge": "SOC meter did not keep pace at the start or end"},
        "state": {"good": "Good", "attention": "Below spec", "critical": "Report to Marstek",
                  "no_measurement": "No measurement yet", "check_model": "Check the model", "unconfirmed": "Not confirmed yet"},
        "ds": {"high_provisional": "above new, provisional", "high_confirmed": "above new, confirmed (5 measurements)",
               "drop_unconfirmed": "suddenly lower, not confirmed yet"},
        "level": {"ok": "fine", "letop": "attention", "advies": "advice"},
        "share": [
            ("Measurements", "every charge and discharge: time, SOC from/to, DC energy, duration, valid or not with reason, temperature"),
            ("SOC events", "calibration points, jumps, top-up at 99 %, days full"),
            ("Cells", "cell spread after a full charge (when set up)"),
            ("Battery", "model, capacity, spec, installation as year and month, connection"),
            ("Not", "your name and the name of your battery, sensor names, ids of your installation, your address or town, dismissed notices, the running measurement"),
        ],
        "about_full": "Full back-up of Marstek Capacity Monitor. Restore: Settings → Devices & services → Marstek Capacity Monitor → Configure → Restore back-up. Keep this file yourself; it holds the names of your battery and sensors.",
        "about_anonymous": "Anonymous version to share, for example with the \"Share data\" form on GitHub. The data is in this file; what you see above is what you share.",
        "about_marstek": "Measured with Marstek Capacity Monitor on the DC side of the battery (open source, Home Assistant). Full discharges from 95 % or more to 15 % or less; capacity = DC energy divided by the SOC drop, scaled to the usable band. A tool, not proof.",
        "none": "No data yet.",
    },
    "de": {
        "title": {"full": "Backup Batteriekapazität", "anonymous": "Batteriekapazität — anonym zum Teilen", "marstek": "Battery capacity report"},
        "made": "erstellt", "download": "Bericht herunterladen", "back": "← Zurück zu Home Assistant", "share_in": "Das steht in der Datei", "share_out": "Das ist nicht enthalten",
        "sec": {"summary": "Zusammenfassung", "share": "Das teilst du", "months": "Kapazität pro Monat",
                "meas": "Messungen (neueste zuerst)", "soc": "SOC-Anzeige pro Monat", "cells": "Zellen pro Monat",
                "settings": "Einstellungen", "runtime": "Betrieb", "about": "Über diesen Bericht"},
        "chips": {"summary": "Zusammenfassung", "share": "Du teilst", "months": "Pro Monat", "meas": "Messungen",
                  "soc": "SOC", "cells": "Zellen", "settings": "Einstellungen", "runtime": "Betrieb", "about": "Über"},
        "k": {"battery": "Batterie", "model": "Modell", "status": "Status", "measured": "Gemessen (Mittelwert letzte 3)",
              "expected": "Herstellerangabe", "margin": "Abstand zur Herstellerangabe", "since": "Seit Beginn der Messung",
              "cycles": "Volle Zyklen", "age": "Alter", "count": "Vollständige Entladungen gemessen",
              "first": "Erste Messung", "last": "Letzte Messung", "installed": "Inbetriebnahme", "code": "Code (anonym)",
              "nominal": "Nennkapazität", "usable": "Nutzbar (100 % von neu)", "red": "Rote Grenze",
              "tol": "Toleranz", "spec": "Herstellerangabe", "init": "Zyklen vor dem Monitor",
              "conn": "Anbindung", "sign": "Vorzeichen Leistung", "cells": "Zellspannung", "temps": "Zelltemperatur",
              "sens": "Empfindlichkeit SOC / Zellen", "notify": "Hinweise", "app": "Monitor-Version", "ha": "Home Assistant",
              "made": "Erstellt am", "monitor": "Status Messung", "phase": "Nächster Schritt", "invalid": "Verworfene Zyklen",
              "soc_level": "SOC-Drift", "cell_level": "Zellkalibrierung"},
        "yes": "ja", "no": "nein", "years": "Jahre", "cyc": "Zyklen",
        "after": "{eol} % nach {life} Zyklen",
        "th_months": ["Monat", "Gemessen %", "Herst. %", "Differenz", "Messungen", "Temp.", "Zuverlässig"],
        "th_meas": ["Datum", "SOC", "DC-Energie", "Kapazität", "% von neu", "Temp.", "Zuverlässig"],
        "th_soc": ["Monat", "Tage voll", "Größte Abweichung", "Nachladen bei 99 %", "Sprung", "Am längsten nicht voll"],
        "th_cells": ["Monat", "Zellspannungsdifferenz", "Messungen"],
        "rel": {"yes": "● ja", "no": "○ weniger"},
        "why": {"no_calibration": "in den 14 Tagen davor nicht ganz voll", "cold": "Zellen kälter als 5 °C",
                "soc_edge": "SOC-Anzeige lief am Anfang oder Ende nicht mit"},
        "state": {"good": "Gut", "attention": "Unter Herstellerangabe", "critical": "An Marstek melden",
                  "no_measurement": "Noch keine Messung", "check_model": "Modell prüfen", "unconfirmed": "Noch nicht bestätigt"},
        "ds": {"high_provisional": "über neu, vorläufig", "high_confirmed": "über neu, bestätigt (5 Messungen)",
               "drop_unconfirmed": "plötzlich tiefer, noch nicht bestätigt"},
        "level": {"ok": "in Ordnung", "letop": "Achtung", "advies": "Empfehlung"},
        "share": [
            ("Messungen", "jede Ladung und Entladung: Zeit, SOC von/bis, DC-Energie, Dauer, gültig oder nicht mit Grund, Temperatur"),
            ("SOC-Ereignisse", "Kalibrierpunkte, Sprünge, Nachladen bei 99 %, Tage voll"),
            ("Zellen", "Zellspannungsdifferenz nach Vollladung (wenn eingerichtet)"),
            ("Batterie", "Modell, Kapazität, Herstellerangabe, Inbetriebnahme als Jahr und Monat, Anbindung"),
            ("Nicht", "dein Name und der Name deiner Batterie, Sensornamen, Kennungen deiner Installation, deine Adresse oder dein Wohnort, ausgeblendete Hinweise, die laufende Messung"),
        ],
        "about_full": "Vollständiges Backup des Marstek Capacity Monitor. Wiederherstellen: Einstellungen → Geräte & Dienste → Marstek Capacity Monitor → Konfigurieren → Backup wiederherstellen. Bewahre diese Datei selbst auf; sie enthält die Namen deiner Batterie und Sensoren.",
        "about_anonymous": "Anonyme Version zum Teilen, zum Beispiel über das Formular \"Share data\" auf GitHub. Die Daten stehen in dieser Datei; was du oben siehst, ist das, was du teilst.",
        "about_marstek": "Measured with Marstek Capacity Monitor on the DC side of the battery (open source, Home Assistant). Full discharges from 95 % or more to 15 % or less; capacity = DC energy divided by the SOC drop, scaled to the usable band. A tool, not proof.",
        "none": "Noch keine Daten.",
    },
}


def _lang(export: dict[str, Any]) -> str:
    if export.get("variant") == "marstek":
        return "en"  # for Marstek support
    lang = str(export.get("language") or "en")[:2]
    return lang if lang in _L else "en"


def _num(v: Any, d: int, lang: str) -> str:
    if v is None or v == "":
        return "–"
    try:
        s = f"{float(v):,.{d}f}"
    except (TypeError, ValueError):
        return escape(str(v))
    if lang in ("nl", "de"):
        s = s.replace(",", "_").replace(".", ",").replace("_", ".")
    return s


def _date(ts: Any, lang: str, with_time: bool = False) -> str:
    if ts is None:
        return "–"
    try:
        d = datetime.fromtimestamp(float(ts)) if not isinstance(ts, str) else datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return escape(str(ts))
    fmt = "%Y-%m-%d %H:%M" if with_time else "%Y-%m-%d"
    if lang in ("nl", "de"):
        fmt = "%d-%m-%Y %H:%M" if with_time else "%d-%m-%Y"
    return d.strftime(fmt)


def _cls(status: str | None) -> str:
    return {"good": "ok", "attention": "wr", "critical": "bad", "check_model": "wr"}.get(status or "", "mut")


def _kv(rows: list[tuple[str, str]]) -> str:
    return '<table class="kv">' + "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a, b in rows) + "</table>"


def _table(head: list[str], rows: list[list[str]]) -> str:
    th = "".join(f"<th>{escape(h)}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table><tr>{th}</tr>{body}</table>"


def _capacity(rec: dict[str, Any], bat: dict[str, Any]) -> float | None:
    delta = rec.get("delta_soc") or 0
    nom = float(bat.get("nominal_kwh") or 0)
    usable = float(bat.get("usable_kwh") or 0)
    if delta <= 0 or nom <= 0:
        return None
    return rec.get("e_dc_kwh", 0) / delta * (usable / nom * 100)


def render_html(export: dict[str, Any]) -> str:
    """The report, with the export itself embedded."""
    lang = _lang(export)
    L = _L[lang]
    K = L["k"]
    v = export.get("variant", "full")
    bat = export.get("battery") or {}
    s = export.get("summary") or {}
    data = export.get("data") or {}
    n = lambda x, d=1: _num(x, d, lang)  # noqa: E731

    full = [r for r in data.get("records") or [] if r.get("direction") == "discharge"
            and r.get("valid", True) and r.get("soc_start", 0) >= 95 and r.get("soc_end", 100) <= 15]
    full.sort(key=lambda r: r.get("ts", 0), reverse=True)

    status = s.get("status")
    st = L["state"].get(status or "", status or "–")
    ds = s.get("display_state")
    if ds in L["ds"] and status != "unconfirmed":
        st += f' <span class="mut">· {L["ds"][ds]}</span>'
    since = s.get("since_start_pct")
    since_txt = "–" if since is None else ("+" if since > 0 else "−" if since < 0 else "± ") + n(abs(since)) + " %"
    name = escape(str(bat.get("name") or bat.get("battery_id") or bat.get("share_id") or "–"))

    sections: list[tuple[str, str]] = []
    summary_rows = [
        (K["battery"] if v == "full" else K["code"], name),
        (K["model"], escape(MODEL_NAMES.get(str(bat.get("model")), str(bat.get("model") or "–")))),
        (K["status"], f'<span class="{_cls(status)}">{st}</span>'),
        (K["measured"], f'{n(s.get("measured_kwh"), 2)} kWh · {n(s.get("measured_pct"))} %'),
        (K["expected"], f'{n(s.get("expected_kwh"), 2)} kWh · {n(s.get("expected_pct"))} %'),
        (K["margin"], f'{n(s.get("margin_kwh"), 2)} kWh'),
        (K["since"], since_txt),
        (K["cycles"], n(s.get("cycles"), 0)),
        (K["age"], f'{n(s.get("age_years"))} {L["years"]}'),
        (K["count"], str(len(full))),
        (K["first"], _date(full[-1]["ts"], lang) if full else "–"),
        (K["last"], _date(full[0]["ts"], lang) if full else "–"),
        (K["made"], escape(str(export.get("created") or "–"))[:16].replace("T", " ")),
    ]
    sections.append(("summary", _kv(summary_rows)))

    if v == "anonymous":
        # Two blocks: what is in the file (green) and what stays out (grey)
        yes = [(a, b) for a, b in L["share"] if a not in ("Niet", "Not", "Nicht")]
        no = [b for a, b in L["share"] if a in ("Niet", "Not", "Nicht")]
        rows = "".join(f"<tr><td>{escape(a)}</td><td>{escape(b)}</td></tr>" for a, b in yes)
        out = f'<div class="in"><div class="bh">✓ {L["share_in"]}</div><table class="kv share">{rows}</table></div>'
        if no:
            items = "".join(f"<li>{escape(x.strip())}</li>" for x in no[0].split(","))
            out += f'<div class="out"><div class="bh">✕ {L["share_out"]}</div><ul>{items}</ul></div>'
        sections.append(("share", out))

    trend = s.get("trend") or []
    if trend:
        why = lambda t: ", ".join(L["why"].get(w, w) for w in str(t.get("why") or "").replace("both", "no_calibration,cold").split(",") if w)  # noqa: E731
        rows = [[escape(t.get("month", "")), f'<b class="{_cls(t.get("status"))}">{n(t.get("pct"))}</b>',
                 n(t.get("expected_pct")), n(t.get("diff_pct")), str(t.get("n", "")),
                 "–" if t.get("temp_c") is None else n(t.get("temp_c"), 0) + " °C",
                 L["rel"]["yes"] if t.get("reliable", True) else f'{L["rel"]["no"]} <span class="mut">({escape(why(t))})</span>']
                for t in trend]
        sections.append(("months", _table(L["th_months"], rows)))
    else:
        sections.append(("months", f'<p class="mut">{L["none"]}</p>'))

    if full:
        rows = []
        for r in full:
            cap = _capacity(r, bat)
            pct = cap / float(bat.get("usable_kwh") or 1) * 100 if cap else None
            rows.append([_date(r.get("ts"), lang, True), f'{n(r.get("soc_start"), 0)} → {n(r.get("soc_end"), 0)} %',
                         f'{n(r.get("e_dc_kwh"), 3)} kWh', f'{n(cap, 2)} kWh', n(pct),
                         "–" if r.get("temp_c") is None else n(r.get("temp_c"), 0) + " °C",
                         L["rel"]["no"] if (r.get("edge_ratio") or 0) >= 2 else L["rel"]["yes"]])
        sections.append(("meas", _table(L["th_meas"], rows)))

    if v != "marstek":
        soc = s.get("soc") or {}
        if soc.get("trend"):
            rows = [[escape(t.get("month", "")), str(t.get("full_days", "")), n(t.get("dev"), 0) + " %",
                     n(t.get("b99"), 0) + " %" if t.get("b99") else "–", n(t.get("jump"), 0) + " %" if t.get("jump") else "–",
                     f'{t.get("no_full_days")} d' if t.get("no_full_days") else "–"] for t in soc["trend"]]
            lvl = L["level"].get(soc.get("level", "ok"), soc.get("level"))
            sections.append(("soc", f'<p>{K["soc_level"]}: <b>{escape(str(lvl))}</b></p>' + _table(L["th_soc"], rows)))
        cells = s.get("cells") or {}
        if cells.get("trend"):
            rows = [[escape(t.get("month", "")), n(t.get("spread_mv"), 0) + " mV", str(t.get("n", ""))] for t in cells["trend"]]
            lvl = L["level"].get(cells.get("level", "ok"), cells.get("level"))
            sections.append(("cells", f'<p>{K["cell_level"]}: <b>{escape(str(lvl))}</b></p>' + _table(L["th_cells"], rows)))

    yn = lambda x: L["yes"] if x else L["no"]  # noqa: E731
    settings = [
        (K["model"], escape(MODEL_NAMES.get(str(bat.get("model")), str(bat.get("model") or "–")))),
        (K["nominal"], f'{n(bat.get("nominal_kwh"), 2)} kWh'),
        (K["usable"], f'{n(bat.get("usable_kwh"), 2)} kWh'),
        (K["spec"], L["after"].format(eol=n(bat.get("cycle_eol_pct"), 0), life=n(bat.get("cycle_life"), 0))),
        (K["red"], f'{n(bat.get("red_pct"), 0)} %'),
        (K["tol"], f'{n(bat.get("tolerance_pct"), 0)} %'),
        (K["installed"], escape(str(bat.get("purchase_date") if v == "full" else bat.get("purchase_month") or "–"))),
        (K["init"], n(bat.get("initial_cycles"), 0)),
    ]
    if v != "marstek":
        settings += [
            (K["conn"], escape(str(bat.get("connection") or "–"))),
            (K["sign"], escape(str(bat.get("power_sign") or "–"))),
            (K["cells"], yn(bat.get("has_cells"))),
            (K["temps"], yn(bat.get("has_temps"))),
            (K["sens"], escape(f'{bat.get("soc_sensitivity") or "–"} / {bat.get("cell_sensitivity") or "–"}')),
            (K["notify"], yn(bat.get("notify"))),
        ]
    if v == "full":
        for key in ("soc_entity", "power_entity", "cell_max_entity", "cell_min_entity", "temp_max_entity", "temp_min_entity"):
            if bat.get(key):
                settings.append((escape(key), escape(str(bat[key]))))
    settings += [(K["app"], escape(str(export.get("app_version") or "–"))), (K["ha"], escape(str(export.get("ha_version") or "–")))]
    sections.append(("settings", _kv(settings)))

    if v != "marstek":
        mon = s.get("monitor") or {}
        invalid = [r for r in data.get("records") or [] if not r.get("valid", True)]
        reasons: dict[str, int] = {}
        for r in invalid:
            reasons[str(r.get("reason") or "?")] = reasons.get(str(r.get("reason") or "?"), 0) + 1
        sections.append(("runtime", _kv([
            (K["monitor"], escape(str(mon.get("state") or "–"))),
            (K["phase"], escape(str(mon.get("phase") or "–"))),
            (K["invalid"], escape(", ".join(f"{k} {c}×" for k, c in sorted(reasons.items())) or "0")),
        ])))

    sections.append(("about", f'<div class="note">{escape(L["about_" + v])}</div>'))

    chips = "".join(f'<a href="#{k}">{L["chips"][k]}</a>' for k, _ in sections)
    body = "".join(f'<h2 id="{k}">{L["sec"][k]}</h2><div class="box">{html}</div>' for k, html in sections)
    title = L["title"][v]
    created = escape(str(export.get("created") or ""))[:16].replace("T", " ")
    payload = json.dumps(export, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    fname = f"marstek-capacity-{v}-{escape(str(bat.get('battery_id') or bat.get('share_id') or 'battery'))}-{created[:10]}.html"
    # Back button (0.5.5): only when opened from Home Assistant. On a phone
    # the report replaces the app view, so this is the way back; in a
    # downloaded copy it is removed (there is no Home Assistant to go to).
    script = (
        "(function(){var k=document.getElementById('back');"
        "if(location.pathname.indexOf('/api/marstek_capacity_monitor/')!==0){k.remove();return;}"
        "k.addEventListener('click',function(){if(window.opener&&!window.opener.closed){window.close();}"
        "var r=document.referrer;location.href=(r&&r.indexOf(location.origin)===0)?r:'/';});})();"
        "document.getElementById('dl').addEventListener('click',function(){var b=new Blob(['<!doctype html>'"
        "+document.documentElement.outerHTML],{type:'text/html'});var a=document.createElement('a');"
        f"a.href=URL.createObjectURL(b);a.download='{fname}';document.body.appendChild(a);a.click();a.remove();}});"
    )
    return (
        f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{escape(title)}</title><style>{_CSS}</style></head><body><div class=\"wrap\">"
        f'<div class="top"><div><h1>{escape(title)}</h1><div class="sub">{name} · {L["made"]} {created} · '
        f'v{escape(str(export.get("app_version") or ""))} · {len(full)} × 95 → 15 %</div></div>'
        f'<div class="btns"><button id="back" class="sec">{L["back"]}</button><button id="dl">{L["download"]}</button></div></div><div class="chips">{chips}</div>{body}</div>'
        f'<script type="application/json" id="{_SCRIPT_ID}">{payload}</script><script>{script}</script></body></html>'
    )
