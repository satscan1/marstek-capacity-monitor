"""Build the ready-made dashboards in dashboard/ready-made/.

Each file is a complete dashboard: the button-card templates plus one
"Sections" view with 1 to 6 batteries, in English and Dutch. The templates are
copied from dashboard/button-card/marstek_capacity_templates.yaml, so run this
script after changing that file:

    python scripts/build_ready_dashboards.py

tests/test_ready_dashboards.py fails when the files are out of date.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "dashboard" / "button-card" / "marstek_capacity_templates.yaml"
OUT = ROOT / "dashboard" / "ready-made"
DOCS = "https://github.com/satscan1/marstek-capacity-monitor/blob/main/docs"

TEXT = {
    "en": {
        "file": lambda n: f"{n}-batter{'y' if n == 1 else 'ies'}.yaml",
        "count": lambda n: f"{n} batter{'y' if n == 1 else 'ies'}",
        "title": "Battery capacity",
        "free": (
            "**Free spot**\n\n"
            "Use this place for a card of your own.\n\n"
            f"[What the cards show]({DOCS}/06-dashboard-gallery.md)"
        ),
        "head": [
            "Marstek Capacity Monitor: ready-made dashboard for {count}",
            "",
            "Needs button-card (HACS -> search \"button-card\" -> Download).",
            "",
            "1. Settings -> Dashboards -> Add dashboard -> New dashboard from scratch.",
            "   Give it a name and open it.",
            "2. Pencil (top right) -> three dots -> Raw configuration editor.",
            "3. Select everything that is there (Ctrl+A) and paste this whole file over it.",
            "4. Did you give your batteries other codes than {codes}?",
            "   Replace them below (Ctrl+F helps). The names can be changed at name:.",
            "5. Save and close the editor.",
            "",
            "Layout and what the cards show: docs/06-dashboard-gallery.md",
        ],
    },
    "nl": {
        "file": lambda n: f"{n}-batterij{'' if n == 1 else 'en'}.yaml",
        "count": lambda n: f"{n} batterij{'' if n == 1 else 'en'}",
        "title": "Batterijcapaciteit",
        "free": (
            "**Vrije plek**\n\n"
            "Deze plek kun je gebruiken voor een eigen kaart.\n\n"
            f"[Wat de kaarten laten zien]({DOCS}/06-dashboard-gallery.nl.md)"
        ),
        "head": [
            "Marstek Capacity Monitor: kant-en-klaar dashboard voor {count}",
            "",
            "Nodig: button-card (HACS -> zoek \"button-card\" -> Downloaden).",
            "",
            "1. Instellingen -> Dashboards -> Voeg dashboard toe -> Leeg nieuw dashboard.",
            "   Geef het een naam en open het.",
            "2. Potlood (rechtsboven) -> drie puntjes -> Ruwe configuratie-editor.",
            "3. Selecteer alles wat er staat (Ctrl+A) en plak dit hele bestand eroverheen.",
            "4. Heb je je batterijen andere codes gegeven dan {codes}?",
            "   Vervang ze hieronder (Ctrl+F helpt). De namen kun je aanpassen bij name:.",
            "5. Opslaan en de editor sluiten.",
            "",
            "Indeling en wat de kaarten laten zien: docs/06-dashboard-gallery.nl.md",
        ],
    },
}


def templates_block() -> str:
    """The templates file from `button_card_templates:` on (header comments dropped)."""
    text = TEMPLATES.read_text(encoding="utf-8")
    start = text.index("\nbutton_card_templates:") + 1
    return text[start:].rstrip("\n") + "\n"


def battery_card(i: int, lang: str, columns: int) -> list[str]:
    bid = f"mt{i}"
    return [
        "          - type: custom:button-card",
        "            template: marstek_capacity_battery",
        f"            grid_options: {{columns: {columns}, rows: auto}}",
        "            triggers_update:",
        f"              - sensor.marstek_{bid}_capacity_pct",
        f"              - sensor.marstek_{bid}_monitor_status",
        f"              - sensor.marstek_{bid}_measured_capacity",
        "            variables:",
        f"              battery: {bid}",
        f"              name: {bid.upper()}",
        f"              lang: {lang}",
    ]


def overview_card(n: int, lang: str, columns: int, months: int) -> list[str]:
    lines = [
        "          - type: custom:button-card",
        "            template: marstek_capacity_overview",
        f"            grid_options: {{columns: {columns}, rows: auto}}",
        "            triggers_update:",
    ]
    for i in range(1, n + 1):
        lines += [
            f"              - sensor.marstek_mt{i}_capacity_pct",
            f"              - sensor.marstek_mt{i}_monitor_status",
        ]
    lines += [
        "            variables:",
        f"              lang: {lang}",
        f"              months: {months}",
        "              batteries:",
    ]
    lines += [f"                - {{id: mt{i}, name: MT{i}}}" for i in range(1, n + 1)]
    return lines


def free_card(lang: str) -> list[str]:
    lines = [
        "          - type: markdown",
        "            grid_options: {columns: 12, rows: auto}",
        "            content: |",
    ]
    lines += [f"              {line}".rstrip() for line in TEXT[lang]["free"].split("\n")]
    return lines


def view(n: int, lang: str) -> list[str]:
    lines = [
        "views:",
        f"  - title: {TEXT[lang]['title']}",
        "    path: marstek",
        "    type: sections",
        "    max_columns: 3",
        "    sections:",
        "      - type: grid",
        "        column_span: 3",
        "        cards:",
    ]
    if n <= 2:
        # Batteries one third each, the overview to the right (one row of three).
        for i in range(1, n + 1):
            lines += battery_card(i, lang, 12)
        lines += overview_card(n, lang, 12, 3)
    else:
        # Overview two thirds with a free place, then 3 / 2 x 2 / 3 + 2 / 3 + 3.
        lines += overview_card(n, lang, 24, 6)
        lines += free_card(lang)
        width = 18 if n == 4 else 12
        for i in range(1, n + 1):
            lines += battery_card(i, lang, width)
    return lines


def build(n: int, lang: str) -> str:
    t = TEXT[lang]
    codes = ", ".join(f"mt{i}" for i in range(1, n + 1))
    head = [
        f"# {line.format(count=t['count'](n), codes=codes)}".rstrip()
        for line in t["head"]
    ]
    head.append("# Generated by scripts/build_ready_dashboards.py - do not edit by hand.")
    return "\n".join(head) + "\n\n" + templates_block() + "\n" + "\n".join(view(n, lang)) + "\n"


def expected() -> dict[Path, str]:
    return {
        OUT / lang / TEXT[lang]["file"](n): build(n, lang)
        for lang in TEXT
        for n in range(1, 7)
    }


def main() -> None:
    for path, text in expected().items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
