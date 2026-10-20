# Marstek Capacity Monitor

*[English](README.md)*

Volg in Home Assistant of je thuisbatterij zijn capaciteit houdt. De meting gebeurt aan de **DC-kant**: de batterij zelf, niet het stopcontact. Werkt voor maximaal **6 batterijen**.

## Welke vraag beantwoordt het?

> **Houdt mijn batterij zijn capaciteit vast, vergeleken met wat je na dit gebruik mag verwachten?**

## Wat heb je nodig?

Per batterij twee sensoren die je vrijwel zeker al hebt:

* de **laadtoestand** (SOC, %);
* het **DC-vermogen van de batterij** (W of kW), dus de batterijkant en niet de AC-/netkant.

Je hoeft **geen nieuwe sensoren** te maken. Bij het toevoegen zoekt de integratie zelf welke sensoren er in Home Assistant zijn en doet per batterij een voorstel.

| Marstek | Hoe hij meestal in HA zit | Laadtoestand | DC-vermogen |
|---|---|---|---|
| Venus E v1 / v2 | RS485 via ESPHome (LilyGo, M5Stack) of via een RS485-netwerkbrug (Elfin EW11) met een Modbus-integratie | register 32104 | register 32102 |
| Venus E v3, Venus A, Venus D | Ingebouwde LAN-poort met Modbus TCP | register 34002 | register 30001 |

**Elk Marstek-model met Modbus werkt**, via RS485 of via LAN, zolang een HA-koppeling de laadtoestand en het DC-vermogen als sensor levert. De tabel geeft de gecontroleerde modellen; alleen de registers verschillen, de gegevens zijn hetzelfde. Bij een ander model vul je bij het toevoegen de eigen fabrieksgegevens in (capaciteit, ontlaaddiepte, cycli); de standaardwaarden zijn die van de Venus E 5,12 kWh.

 Integraties zoals [marstek_venus_modbus](https://github.com/ViperRNMC/marstek_venus_modbus) en [Omnibattery](https://github.com/ffunes/Omnibattery), en de gangbare ESPHome-configuraties, leveren beide sensoren.

**Niet ondersteund:** koppelingen die alleen het AC-vermogen leveren, zoals de meeste cloudkoppelingen. AC-waarden bevatten omzetverlies en geven daardoor een verkeerde capaciteit. Kies je toch een sensor die op AC lijkt, dan krijg je een waarschuwing.

**Plus of min hoef je niet in te stellen.** De ene integratie toont laden als plus, de andere als min. Bij de eerste volle laad- of ontlaadbeurt herkent de tool het zelf en draait het teken zo nodig om. Je krijgt daar een melding van. Je kunt het teken ook vast instellen.

## Drie capaciteiten, strikt gescheiden

| | Betekenis | Venus E 5,12 kWh |
|---|---|---|
| **Fabriekscapaciteit** | Wat er totaal in de cellen zit (nominaal) | 5,12 kWh |
| **Bruikbare capaciteit** | Fabriekscapaciteit maal de ontlaaddiepte (DoD). Dit is **100 % van nieuw**. | 90 % DoD → 4,61 kWh |
| **Gemeten capaciteit** | Wat er bij een **volledige ontlading** werkelijk uit de cellen kwam, omgerekend naar de bruikbare band | bv. 4,46 kWh = 97 % |

## Hoe er gemeten wordt

1. **Event** — elke wijziging van de laadtoestand of het DC-vermogen.
2. **Context** — de tool telt het DC-vermogen op tot energie (net als een Riemann-helper, maximaal 1 minuut per stap) en herkent laad- en ontlaadbeurten. Een beurt sluit pas als de laadtoestand 3 punten terugloopt vanaf het bereikte uiterste. Alleen beurten van minstens 20 punten worden vastgelegd.
3. **Result** — één record per beurt, bewaard in Home Assistant zelf (`.storage`). Je hebt geen InfluxDB nodig.

Alleen **volledige ontladingen** tellen voor de capaciteit: beginnen op 95 % of hoger, eindigen op 15 % of lager. De berekening:

```
gemeten kWh = DC-energie uit de cellen ÷ daling van de laadtoestand × bruikbare band
```

De bruikbare band is 90 punten bij 90 % ontlaaddiepte. De getoonde waarde is de **mediaan van de laatste 3** volledige ontladingen van het afgelopen jaar.

Gedeeltelijke ontladingen tellen bewust niet mee: een procent onderin levert meer kWh dan een procent bovenin. Valt er tijdens een beurt een gat van meer dan 5 minuten in de vermogensgegevens, bijvoorbeeld door een herstart, dan telt die beurt niet mee.

## Verwachting en kleuren

De verwachting volgt de **fabrieksopgave per cyclus**: 80 % capaciteit na 6.000 volle cycli, dus 0,0033 punt per cyclus. Het aantal volle cycli is de DC-ontladen kWh gedeeld door de bruikbare capaciteit, plus eventueel de cycli van vóór de monitoring.

Marstek geeft **geen capaciteitsgarantie in jaren**. Daarom is er geen tijdlijn.

| Kleur | Betekenis |
|---|---|
| 🟢 Groen | Op de verwachting, of maximaal 5 punten eronder |
| 🟠 Oranje | Verder onder de verwachting, maar boven 75 % |
| 🔴 Rood | **75 % of lager**: meld het bij Marstek **via de Marstek-app** |

De marge laat zien hoeveel kWh de batterij boven of onder de verwachting zit. Alle grenzen kun je aanpassen.

### Waar komen de getallen vandaan?

* **5.120 Wh, meer dan 6.000 cycli (bij 25 °C), 90 % ontlaaddiepte**: datasheet van de Venus E.
* **80 % capaciteitsbehoud na 6.000 cycli**: [productpagina Venus E Gen 3.0 van Marstek](https://marstekenergy.com/en-us/products/marstek-venus-e-gen-3). De Nederlandse versie van die pagina noemt 10.000 cycli.
* **10 jaar garantie**: productpagina's van Marstek. Het [garantiebeleid](https://marstekenergy.com/nl-nl/pages/warranty) dekt materiaal- en fabricagefouten en noemt geen capaciteitspercentage.

Controleer je eigen voorwaarden. Je past ze aan via **Instellingen → Apparaten & diensten → Marstek Capacity Monitor → Configureren**.

## Installatie

**Via HACS (custom repository)**

1. Ga in HACS naar de drie puntjes → *Custom repositories*. Vul de URL van deze repo in, type *Integration*.
2. Installeer **Marstek Capacity Monitor** en herstart Home Assistant.

**Handmatig**

Kopieer `custom_components/marstek_capacity_monitor` naar `/config/custom_components/` en herstart.

**Per batterij toevoegen**

Ga naar **Instellingen → Apparaten & diensten → Integratie toevoegen → Marstek Capacity Monitor**.

1. Kies een gevonden batterij, of kies zelf de sensoren.
2. Controleer de korte code (`mt1` … `mt6`), de naam en de twee sensoren.
3. Vul de fabrieksgegevens in: fabriekscapaciteit, reserve, aankoopdatum, garantietermijn en cycli. De standaardwaarden komen uit de datasheet van de Venus E.

## Sensoren (per batterij, voorbeeld `mt1`)

| Entiteit | Wat |
|---|---|
| `sensor.marstek_mt1_measured_capacity` | Gemeten capaciteit (kWh). Attributen: `trend` (per maand, nieuw → oud) en `history` (laatste 10 volledige ontladingen) |
| `sensor.marstek_mt1_capacity_pct` | Gemeten capaciteit als % van nieuw |
| `sensor.marstek_mt1_expected_capacity` | Verwachte capaciteit (%) volgens de cycluslijn |
| `sensor.marstek_mt1_margin` | Marge ten opzichte van de verwachting (kWh) |
| `sensor.marstek_mt1_cycles` | Aantal volle cycli |
| `sensor.marstek_mt1_warranty_status` | `good` / `attention` / `critical` / `no_measurement` |
| `sensor.marstek_mt1_nominal_capacity` · `_usable_capacity` · `_red_threshold` · `_warranty_end` · `_dc_discharged` | Diagnostiek. `_dc_discharged` toont ook welke sensoren gebruikt worden en hoe het teken is herkend |

Na elke vastgelegde beurt verstuurt de integratie het event `marstek_capacity_monitor_session`. Daarmee kun je de records zelf doorsturen, bijvoorbeeld naar InfluxDB.

De schrijfbelasting blijft laag:

* de lijsten `trend` en `history` gaan niet naar de recorder-database;
* de sensoren veranderen alleen na een meting of één keer per uur.

## Kaarten

| Map | Vereist | Inhoud |
|---|---|---|
| `cards/button-card/` | [button-card](https://github.com/custom-cards/button-card) (HACS) | Overzicht van maximaal 6 batterijen: per maand, trendkolom eerst, nieuw → oud. Daarnaast een detailkaart per batterij. Taal instellen met `lang: nl` of `en`. |
| `cards/standard/` | niets | Entiteitenkaart en statistiekgrafiek (gemeten tegenover verwacht per maand) |

![voorbeeld](docs/preview.png)

## Metingen wissen

Gebruik de actie `marstek_capacity_monitor.reset_measurements` met de batterij als doel. Dit kan niet ongedaan worden gemaakt.

Verwijder je een batterij uit de integratie, dan blijven de metingen in `.storage/` staan. Ze kunnen bewijs zijn bij een melding aan Marstek.

## Tests

```
pip install pytest-homeassistant-custom-component
pytest
```
