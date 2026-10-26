# Marstek Capacity Monitor

[![Release](https://img.shields.io/github/v/release/satscan1/marstek-capacity-monitor)](https://github.com/satscan1/marstek-capacity-monitor/releases/latest) [![HACS Default](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=satscan1&repository=marstek-capacity-monitor&category=integration) [![Stars](https://img.shields.io/github/stars/satscan1/marstek-capacity-monitor?style=flat)](https://github.com/satscan1/marstek-capacity-monitor/stargazers) [![Ko-fi](https://img.shields.io/badge/Ko--fi-satscan-FF5E5B?logo=kofi&logoColor=white)](https://ko-fi.com/satscan)

*[English](README.md) · [Nederlands](README.nl.md)* 

Behalte in Home Assistant im Blick, ob dein Marstek-Heimspeicher seine Kapazität hält, gemessen auf der **DC-Seite** (an der Batterie selbst, nicht an der Steckdose). Bis zu **6 Batterien**.

> **Hält meine Batterie ihre Kapazität, verglichen mit der Herstellerangabe?**

![Marstek Capacity Monitor](https://raw.githubusercontent.com/satscan1/marstek-capacity-monitor/main/screenshots/infographic-de.png)

## Kurz gesagt 

- **Zwei Sensoren, die du schon hast:** Ladezustand und DC-Leistung der Batterie. Die Integration findet sie selbst. 
- **Gemessen bei einer vollständigen Entladung** (≥ 95 % → ≤ 15 %) und verglichen mit der nutzbaren Kapazität im Neuzustand.
- **Herstellerangabe** als Maßstab: 80 % nach 6000 Zyklen. Grün im Rahmen der Herstellerangabe, orange darunter, rot bei 75 % oder weniger: über die Marstek-App melden.
- **Jede Anbindung, die Ladezustand und DC-Leistung liefert:** ESPHome, Modbus (RS485 oder LAN) oder eine andere Integration. Venus E v1, v2, v3, 4.0, Max, Pro, Venus A, Venus C, Venus D.
- **Plug & Play:** Modell und Datum der Inbetriebnahme wählen; die Herstellerdaten werden für dich ausgefüllt. Die Zyklen vor dem Monitor kommen aus dem Zähler der Batterie, wenn es einen gibt (AC-Seite, eine Schätzung). Später gefundene Sensoren stehen unter Reparaturen bereit.
- **Eigene Karten und ein Dashboard mit einem Klick:** kein button-card nötig.
- **Zeigt, ob es funktioniert:** ein Status pro Batterie und „sammelt Daten“ bis zur ersten vollständigen Entladung. Gab es in den letzten Tagen schon eine, gibt es sofort eine erste Messung.
- **Optional:** Zellspannungsdifferenz nach Vollladung und Zelltemperatur als Kontext (experimentell).
- **SOC-Drift und Zellkalibrierung** (neu in 0.5): Der Monitor erkennt, wenn die SOC-Anzeige abweicht oder die Zellen aus dem Gleichgewicht geraten, und gibt nur bei einem Muster einen Hinweis mit dem, was zu tun ist. Ein Klick blendet ihn aus.
- Schaltflächen **Diagramm · SOC · Zellen** auf der Batteriekarte.
- **Schlank und lokal:** alles in Home Assistant, ohne InfluxDB und ohne Cloud.

## Installation in 3 Schritten

1. In HACS nach **Marstek Capacity Monitor** suchen, herunterladen und Home Assistant neu starten. (Nicht gefunden? Drei Punkte → *Benutzerdefinierte Repositories* → URL dieses Repos, Typ *Integration*.)
2. **Einstellungen → Geräte & Dienste → Integration hinzufügen → Marstek Capacity Monitor**.
3. Die gefundene Batterie wählen, das Modell auswählen und das Datum der Inbetriebnahme eingeben. Fertig.

Starte Home Assistant danach neu und gehe zu **Einstellungen → Dashboards → Dashboard hinzufügen → Marstek battery capacity** (Home Assistant 2026.5 und neuer; ältere Versionen: siehe Anleitung). Das Dashboard ordnet deine Batterien (1 bis 6) von selbst an. Die Karten gehören zur Integration; button-card ist nicht mehr nötig. Ausführliche Anleitung: [docs/01-installation.de.md](docs/01-installation.de.md).

## Dokumentation

| Dokument | Inhalt |
|---|---|
| [01 – Installation](docs/01-installation.de.md) | Was du brauchst, HACS, Batterie hinzufügen, Karten |
| [06 – Dashboard und Galerie](docs/06-dashboard-gallery.de.md) | Aufteilung für 1 bis 6 Batterien, die Karte mit Nummern erklärt, Galerie |
| [02 – Configuration](docs/02-configuration.md) (Englisch) | Einstellungen, Sensoren, Messungen löschen |
| [03 – How it works](docs/03-how-it-works.md) (Englisch) | Drei Kapazitäten, Messung, Umrechnung auf 100 %, Herstellerangabe und Farben |
| [04 – Fehlerbehebung](docs/04-troubleshooting.de.md) | Häufige Meldungen und Fragen, und was zu tun ist |
| [05 – Supported batteries](docs/05-supported-batteries.md) (Englisch) | Modelle, Entladetiefe pro Modell, **Quellen der Herstellerangaben** |
| [07 – Wie der Monitor misst](docs/07-measuring-method.de.md) | Warum nur vollständige Entladungen zählen, und warum Messen bei Zwischenladen nicht zuverlässig ist |

Änderungen pro Version: [CHANGELOG](CHANGELOG.md) (Englisch).

## Screenshots

Die Screenshots verwenden **Demodaten**: fünf Beispielbatterien (Venus C, Venus E v1, v2, v3 und Venus D) mit erfundenen Messungen. Sie zeigen, wie die Bildschirme aussehen, nicht wie diese Modelle tatsächlich altern. Mehr Beispiele, von 1 bis 6 Batterien: [Galerie](docs/06-dashboard-gallery.de.md).

**1. Batterie hinzufügen: der Scan findet die Sensoren, die du schon hast**

![Scan](screenshots/de/01-scan.png)

**2. Vorgeschlagene Sensoren prüfen (Zellspannung und Zelltemperatur sind optional)**

![Sensoren](screenshots/de/02-sensors.png)

**3. Modell und Datum der Inbetriebnahme wählen: die Herstellerdaten werden für dich ausgefüllt**

![Modell](screenshots/de/03-model.png)

**4. Alles später unter Konfigurieren ändern: Herstellerdaten und Garantie…**

![Herstellerdaten](screenshots/de/03-factory-data.png)

**…und weiter unten das Vorzeichen des Leistungssensors, Hinweise, der Menüeintrag in der Seitenleiste und die Empfindlichkeit für SOC-Drift und Zellkalibrierung**

![Einstellungen](screenshots/de/04-settings.png)

**5. Ein Gerät pro Batterie**

![Integration](screenshots/de/05-integration.png)

![Gerät](screenshots/de/06-device.png)

**6. Die Batteriekarte (v0.5.1)**

![Batteriekarte](screenshots/card/de/1-karte.png)

Nach einem Klick auf **Diagramm**: die Kapazität pro Monat, verglichen mit der Herstellerangabe

![Diagramm](screenshots/card/de/2-diagramm.png)

Nach einem Klick auf **SOC**: stimmt die SOC-Anzeige noch?

![SOC](screenshots/card/de/3-soc.png)

Nach einem Klick auf **Zellen**: sind die Zellen noch im Gleichgewicht?

![Zellen](screenshots/card/de/4-zellen.png)

## Projekt unterstützen

Findest du das Tool nützlich? Gib ihm einen ⭐ auf GitHub, damit andere es auch finden.

Möchtest du noch etwas mehr tun? Unterstütze mich über [Ko-fi](https://ko-fi.com/satscan).

## Lizenz

[GPL-3.0](LICENSE)
