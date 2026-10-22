# Marstek Capacity Monitor

*[English](README.md) · [Deutsch](README.de.md)*

Volg in Home Assistant of je Marstek-thuisbatterij zijn capaciteit houdt, gemeten aan de **DC-kant** (de batterij zelf, niet het stopcontact). Tot **6 batterijen**.

> **Houdt mijn batterij zijn capaciteit vast, vergeleken met wat de fabrikant specificeert?**

![Marstek Capacity Monitor](screenshots/infographic-nl.png)

## In het kort

- **Twee sensoren die je al hebt:** laadtoestand en DC-vermogen van de batterij. De integratie vindt ze zelf.
- **Gemeten bij een volle ontlading** (≥ 95 % → ≤ 15 %) en vergeleken met de bruikbare capaciteit van een nieuwe batterij.
- **Specificatie van de fabrikant** als maatstaf: 80 % na 6.000 cycli. Groen volgens specificatie, oranje eronder, rood bij 75 % of lager: melden via de Marstek-app.
- **Elke koppeling die laadtoestand en DC-vermogen levert:** ESPHome, Modbus (RS485 of LAN) of een andere integratie. Venus E v1, v2, v3, 4.0, Max, Pro, Venus A, Venus D.
- **Plug & play:** kies je model en installatiedatum; de fabrieksgegevens worden voor je ingevuld. De cycli van vóór de monitor komen uit de teller van de batterij als die er is (AC-kant, een schatting). Later gevonden sensoren staan klaar onder Reparaties.
- **Laat zien of het werkt:** een status per batterij, en "verzamelt data" tot de eerste volledige ontlading.
- **Optioneel: celbalans:** het verschil tussen de hoogste en laagste cel na een volle lading.
- **SOC-drift en celkalibratie** (nieuw in 0.5): de monitor ziet wanneer de SOC-meter gaat afwijken of de cellen uit balans raken, en geeft alleen bij een patroon een seintje met wat je kunt doen. Eén klik en het is weg.
- **Celtemperatuur als context (experimenteel)** en knopjes **Grafiek · SOC · Cellen** op de batterijkaart.
- **Licht en lokaal:** alles in Home Assistant, geen InfluxDB of cloud.

## Installeren in 3 stappen

1. In HACS: drie puntjes → *Custom repositories* → URL van deze repo, type *Integration*. Installeer **Marstek Capacity Monitor** en herstart Home Assistant.
2. **Instellingen → Apparaten en diensten → Voeg integratie toe → Marstek Capacity Monitor**.
3. Kies de gevonden batterij, kies het model en vul de installatiedatum in. Klaar.

Herstart daarna Home Assistant en ga naar **Instellingen → Dashboards → Voeg dashboard toe → Marstek battery capacity** (Home Assistant 2026.5 en nieuwer; oudere versies: zie de handleiding). Het dashboard zet je batterijen (1 tot 6) vanzelf goed neer. De kaarten zitten in de integratie zelf; button-card is niet meer nodig. Volledige uitleg: [docs/01-installation.nl.md](docs/01-installation.nl.md).

## Documentatie

| Document | Inhoud |
|---|---|
| [01 – Installatie](docs/01-installation.nl.md) | Wat je nodig hebt, HACS, batterij toevoegen, kaarten |
| [02 – Instellingen](docs/02-configuration.nl.md) | Instellingen, sensoren, metingen wissen |
| [03 – Hoe het werkt](docs/03-how-it-works.nl.md) | Drie capaciteiten, meten, omrekening naar 100 %, specificatie en kleuren |
| [04 – Problemen oplossen](docs/04-troubleshooting.nl.md) | Veelvoorkomende meldingen en wat te doen |
| [05 – Ondersteunde batterijen](docs/05-supported-batteries.nl.md) | Modellen, ontlaaddiepte per model, **bronnen voor de specificaties van de fabrikant** |
| [06 – Dashboard en galerij](docs/06-dashboard-gallery.nl.md) | Indeling bij 1 tot 6 batterijen, de kaart genummerd uitgelegd, galerij met en zonder grafiek |

Wijzigingen per versie: [CHANGELOG](CHANGELOG.md) (Engels).

## Schermafbeeldingen

> De schermafbeeldingen gebruiken **demogegevens**: vier voorbeeldbatterijen (Venus E v1 via ESPHome, Venus E v2 via LilyGo RS485, Venus E v3 en Venus D via Modbus TCP) met verzonnen metingen (ongeveer 2 % capaciteitsverlies per jaar). Ze laten zien hoe de schermen eruitzien, niet hoe deze modellen in werkelijkheid verouderen.

**1. Batterij toevoegen: de scan vindt de sensoren die je al hebt**

![Scan](screenshots/01-scan.png)

**2. Voorgestelde sensoren controleren**

![Sensoren](screenshots/02-sensors.png)

**3. Fabrieksgegevens (standaardwaarden uit de datasheet van de Venus E; hier het instellingenscherm van een bestaande batterij)**

![Fabrieksgegevens](screenshots/03-factory-data.png)

**4. Instellingen later aanpassen, ook plus/min van de vermogensensor**

![Instellingen](screenshots/04-settings.png)

**5. Eén apparaat per batterij**

![Integratie](screenshots/05-integration.png)

![Apparaat](screenshots/06-device.png)

**6. De kaarten: overzicht en batterijkaarten, met het SOC-venster open (Nederlands en Engels). Meer voorbeelden, van 1 tot 6 batterijen: [galerij](docs/06-dashboard-gallery.nl.md)**

![Dashboard NL](screenshots/08-dashboard-nl.png)

![Dashboard EN](screenshots/07-dashboard-en.png)

**7. Standaardkaarten (geen HACS nodig)**

![Standaardkaarten](screenshots/09-standard-cards.png)

De installatieschermen van Home Assistant zijn in het Engels gemaakt; in een Nederlandstalige HA staan dezelfde schermen in het Nederlands.

## Licentie

[GPL-3.0](LICENSE)
