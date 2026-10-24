# Installation

*[English](01-installation.md) · [Nederlands](01-installation.nl.md)*

## Was du brauchst

Pro Batterie zwei Sensoren, die du so gut wie sicher schon hast:

* den **Ladezustand** (SOC, %);
* die **DC-Leistung der Batterie** (W oder kW), gemessen auf der Batterieseite, nicht auf der AC- bzw. Netzseite.

Du musst **keine Sensoren anlegen**. Beim Hinzufügen einer Batterie durchsucht die Integration Home Assistant und schlägt pro Batterie die passenden Sensoren vor.

Welche Modelle und Anbindungen funktionieren: siehe [Supported batteries](05-supported-batteries.md) (Englisch).

**Plus oder Minus musst du nicht einstellen.** Manche Integrationen zeigen Laden als positiven Wert, andere als negativen. Beim ersten vollständigen Laden oder Entladen erkennt die Überwachung das selbst und dreht das Vorzeichen bei Bedarf um. Du bekommst dann eine Meldung. Du kannst das Vorzeichen auch fest einstellen.

## Integration installieren

**Über HACS (benutzerdefiniertes Repository)**

1. Öffne in HACS die drei Punkte → *Benutzerdefinierte Repositories*. Gib die URL dieses Repos ein, Typ *Integration*.
2. Lade **Marstek Capacity Monitor** herunter und starte Home Assistant neu.

**Von Hand**

Kopiere `custom_components/marstek_capacity_monitor` nach `/config/custom_components/` und starte neu.

**Batterie hinzufügen**

Gehe zu **Einstellungen → Geräte & Dienste → Integration hinzufügen → Marstek Capacity Monitor**.

1. Wähle eine gefundene Batterie oder wähle die Sensoren selbst („✎ Sensoren selbst wählen“).
2. Prüfe den kurzen Code (`mt1` … `mt6`), den Namen und die beiden Sensoren. Optional: höchste und niedrigste Zellspannung für die [Zellbalance](03-how-it-works.md#cell-balance) (Englisch). Sie werden ausgefüllt, wenn die Suche sie findet.
3. Wähle das Modell und gib das Datum der Inbetriebnahme ein. Bei einem bekannten Modell (Venus E v1/v2, v3, 4.0, Max oder Pro, Venus C oder Venus D) werden die Herstellerdaten für dich ausgefüllt (Venus D und Venus E Pro: auch die Anzahl der Packs). Bei einem anderen Modell gibst du die Herstellerdaten selbst ein.
   Eine **Venus C** kann sich mit demselben Code melden wie eine Venus E v1/v2. Wähle dann selbst **Venus C**, auch wenn Venus E v1 / v2 schon ausgewählt ist.

Alle Herstellerdaten kannst du später unter **Konfigurieren** ändern.

Beim Hinzufügen schaut die Integration im Verlauf von Home Assistant (meist die letzten 10 Tage) nach, ob es schon eine vollständige Entladung gab. Wenn ja, gibt es sofort eine erste Messung. Sonst zeigt die Batterie **sammelt Daten** bis zur ersten vollständigen Entladung (≥ 95 % → ≤ 15 %). Die Statuszeile auf der Karte zeigt dir den nächsten Schritt.

## Karten hinzufügen

Ab Version 0.4.0 bringt die Integration ihre eigenen Karten mit. Du musst nichts zusätzlich installieren: kein button-card und keine Vorlagen. Füge zuerst mindestens eine Batterie hinzu. Starte danach Home Assistant neu und lade die Seite im Browser neu (Strg+F5, auf dem Mac Cmd+Shift+R); das gilt auch nach jedem Update.

### Von selbst in der Seitenleiste (ab 0.5.1)

Nach dem Hinzufügen der ersten Batterie und einem Neustart steht **Batteriekapazität** von selbst in der Seitenleiste, mit allen deinen Batterien (1 bis 6, in der [Aufteilung](06-dashboard-gallery.de.md) der Galerie). Du musst nichts einstellen. Dieses Dashboard änderst du nicht; für eine eigene Aufteilung erstellst du selbst ein Dashboard wie unten beschrieben.

- **Ausschalten:** Einstellungen → Geräte & Dienste → Marstek Capacity Monitor → **Konfigurieren** → **Menüeintrag in der Seitenleiste**. Ist er bei einer Batterie aus, verschwindet der ganze Menüeintrag.
- **Ausgeblendet oder an der falschen Stelle?** Halte **Home Assistant** oben in der Seitenleiste gedrückt (oder gehe in dein Profil → Seitenleiste anpassen). Dort blendest du Einträge wieder ein, aus oder verschiebst sie. Das gilt pro Gerät: auf dem Handy stellst du es separat ein.
- Hast du schon ein eigenes Dashboard unter `/marstek-capacity`, lässt der Monitor es in Ruhe.

### Am schnellsten: Dashboard mit einem Klick

1. Gehe zu **Einstellungen → Dashboards → Dashboard hinzufügen**.
2. Wähle unten bei **Community-Dashboards** die Option **Marstek battery capacity**.
3. Gib ihm einen Namen (zum Beispiel *Batteriekapazität*) und klicke auf **Erstellen**.

Das Dashboard ordnet deine Batterien von selbst so an wie in der [Galerie](06-dashboard-gallery.de.md#aufteilung), für 1 bis 6 Batterien. Fügst du später eine Batterie hinzu, erscheint sie ebenfalls von selbst.

Diese Auswahl gibt es ab Home Assistant 2026.5. Mit einer älteren Version: Lege ein **Neues Dashboard von Grund auf** an, öffne es, klicke auf den **Stift**, dann auf die **drei Punkte → Raw-Konfigurationseditor**, ersetze alles durch diese zwei Zeilen und speichere:

```yaml
strategy:
  type: custom:marstek-capacity
```

### Einzelne Karten in deinem eigenen Dashboard

Öffne dein Dashboard, klicke auf den **Stift** und dann auf **Karte hinzufügen**. Suche nach **Marstek**:

- **Marstek capacity (battery)**: eine Batterie, mit Diagramm. Ohne weitere Einstellungen zeigt sie deine erste Batterie.
- **Marstek capacity (overview)**: alle Batterien pro Monat.

Die Karten erkennen deine Batterien, ihre Namen und die Sprache von Home Assistant selbst. Möchtest du etwas ändern, geht das im Code-Editor der Karte:

```yaml
type: custom:marstek-capacity-card
battery: mt2        # Code der Batterie (siehe Sensornamen, z. B. sensor.marstek_mt2_capacity_pct)
name: Garage        # anderer Name auf der Karte
months: 6           # Anzahl der Monate im Trend
lang: de            # de, en oder nl; Standard ist die Sprache von Home Assistant
```

Bei der Übersicht kannst du wählen, welche Batterien sie zeigt: `batteries: [mt1, mt2]`.

Wie du die Karten anordnest und was alles auf der Karte bedeutet: [06 – Dashboard und Galerie](06-dashboard-gallery.de.md).

### Mit button-card (wie vor 0.4.0)

Nutzt du schon die button-card-Karten, funktionieren sie weiter. Umsteigen musst du nicht, du kannst aber: die neuen Karten sehen genauso aus. Die button-card-Vorlagen kennen ab 0.4.0 auch `lang: de`; füge dafür die neue Datei [`marstek_capacity_templates.yaml`](../dashboard/button-card/marstek_capacity_templates.yaml) erneut ein.

Diese Karten brauchen [button-card](https://github.com/custom-cards/button-card). Installiere es zuerst: in HACS nach **button-card** suchen → **Herunterladen**, danach die Seite im Browser neu laden (Strg+F5).

#### Fertiges Dashboard mit button-card

In [`dashboard/ready-made/de/`](../dashboard/ready-made/de/) liegt für jede Anzahl Batterien ein komplettes Dashboard: `1-batterie.yaml` bis `6-batterien.yaml`. Alles ist enthalten, in der [Aufteilung](06-dashboard-gallery.de.md#aufteilung) der Galerie.

1. Gehe zu **Einstellungen → Dashboards → Dashboard hinzufügen → Neues Dashboard von Grund auf**. Gib ihm einen Namen, zum Beispiel *Batteriekapazität*, und öffne es.
2. Klicke oben rechts auf den **Stift**, dann auf die **drei Punkte → Raw-Konfigurationseditor**.
3. Öffne die Datei für deine Anzahl Batterien auf GitHub, kopiere alles (Schaltfläche *Copy raw file*) und ersetze damit den gesamten Inhalt des Editors (Strg+A, dann Strg+V).
4. Hast du beim Hinzufügen die vorgeschlagenen Codes `mt1`, `mt2`, … behalten? Dann musst du nichts ändern. Sonst ersetze sie durch deine eigenen Codes; du findest sie in den Sensornamen, z. B. `sensor.marstek_mt1_capacity_pct`. Die Namen auf den Karten änderst du bei `name:`.
5. Klicke auf **Speichern** und schließe den Editor.

#### In einem bestehenden Dashboard

1. **Vorlagen (einmal pro Dashboard):** Öffne das Dashboard, klicke auf den **Stift**, dann auf die **drei Punkte → Raw-Konfigurationseditor**. Kopiere alles aus [`marstek_capacity_templates.yaml`](../dashboard/button-card/marstek_capacity_templates.yaml) und füge es ganz oben ein, über der Zeile `views:`. Steht dort schon eine Zeile `button_card_templates:` (von anderen Karten)? Dann füge nur den Teil darunter ein, direkt unter deinen vorhandenen Vorlagen. Speichern und den Editor schließen.
2. **Karten:** Noch im Bearbeitungsmodus **Karte hinzufügen** → ganz unten **Manuell**. [`examples.yaml`](../dashboard/button-card/examples.yaml) enthält zwei Beispiele, getrennt durch eine Zeile `---`: zuerst die Übersicht aller Batterien, danach die Karte für eine Batterie. Füge jeweils ein Beispiel ein, nicht die ganze Datei. Ersetze überall `mt1` durch deinen eigenen Code und speichere. Der Text folgt der Sprache von Home Assistant; für eine feste Sprache füge `lang: de`, `lang: en` oder `lang: nl` unter `variables` hinzu. Wiederhole das pro Batterie und für die Übersicht.

Wie du die Karten anordnest und was alles auf der Karte bedeutet: [06 – Dashboard und Galerie](06-dashboard-gallery.de.md).

#### Nur Standardkarten von Home Assistant

In [`dashboard/standard/`](../dashboard/standard/) liegen eine Entitätenkarte und ein Statistikdiagramm („Noch verfügbar“ im Vergleich zur Herstellerangabe, pro Monat), die mit den Standardkarten von Home Assistant funktionieren. Hinzufügen wie in Schritt 2 von *In einem bestehenden Dashboard*.
