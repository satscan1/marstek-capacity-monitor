# Hoe het werkt

*[English](03-how-it-works.md)*

## Drie capaciteiten, strikt gescheiden

| | Betekenis | Venus E 5,12 kWh |
|---|---|---|
| **Opgegeven capaciteit** | Wat er volgens de fabrikant totaal in de cellen zit (nominaal) | 5,12 kWh |
| **Bruikbare capaciteit** | Opgegeven capaciteit maal de ontlaaddiepte (DoD). Dit is **100 % van nieuw**. | 90 % DoD → 4,61 kWh |
| **Gemeten capaciteit** | Wat er bij een **volledige ontlading** werkelijk uit de cellen kwam, omgerekend naar de bruikbare band | bv. 4,46 kWh = 97 % |

## Hoe er gemeten wordt

1. **Event** — elke wijziging van de laadtoestand of het DC-vermogen.
2. **Context** — de tool telt het DC-vermogen op tot energie (net als een Riemann-helper, maximaal 1 minuut per stap) en herkent laad- en ontlaadbeurten. Een beurt sluit pas als de laadtoestand 3 punten terugloopt vanaf het bereikte uiterste. Alleen beurten van minstens 20 punten worden vastgelegd.
3. **Result** — één record per beurt, bewaard in Home Assistant zelf (`.storage`). Je hebt geen InfluxDB nodig.

Alleen **volledige ontladingen** tellen voor de capaciteit: beginnen op 95 % of hoger, eindigen op 15 % of lager. De berekening:

```
gemeten kWh = DC-energie uit de cellen ÷ daling van de laadtoestand × bruikbare band
```

### Omrekening naar 100 % van nieuw

De laadtoestand (SOC) van de batterij loopt van 0 tot 100 % van de **opgegeven capaciteit**. Bruikbaar is alleen het deel binnen de ontlaaddiepte: bij 90 % zijn dat 90 SOC-punten. De tool meet hoeveel kWh er per SOC-punt uit de cellen komt en rekent dat om naar die volle bruikbare band. Dat resultaat is wat de batterij nu levert, en dat wordt vergeleken met de bruikbare capaciteit van een nieuwe batterij (= 100 %).

Voorbeeld (opgegeven 5,12 kWh, reserve 0,61 kWh, dus 88 % bruikbaar = 4,51 kWh):

| Stap | Waarde |
|---|---|
| Gemeten volledige ontlading | 100 % → 11 % = 89 SOC-punten, 4,42 kWh DC |
| Per SOC-punt | 4,42 ÷ 89 = 0,0497 kWh |
| Omgerekend naar de bruikbare band | 0,0497 × 88 = 4,37 kWh |
| Nog beschikbaar | 4,37 ÷ 4,51 = **97 %** |

De bruikbare band verschilt per model; zie [Ondersteunde batterijen](05-supported-batteries.nl.md#ontlaaddiepte-per-model).

De getoonde waarde is de **mediaan van de laatste 3** volledige ontladingen van het afgelopen jaar.

Gedeeltelijke ontladingen tellen bewust niet mee: een procent onderin levert meer kWh dan een procent bovenin. Een herstart van Home Assistant van hooguit 10 minuten wordt overbrugd: de energie in die minuten wordt geschat uit het vermogen vlak ervoor en vlak erna (meestal minder dan 0,5 % verschil). Is de vermogenssensor even niet beschikbaar (bijvoorbeeld een haperende Modbus-verbinding), dan wordt dat op dezelfde manier overbrugd, tot 5 minuten. Duurt de herstart of de onderbreking langer, dan telt die beurt niet mee.

## Specificatie fabrikant en kleuren

De lijn waarmee de meting wordt vergeleken is de **specificatie van de fabrikant per cyclus**: 80 % capaciteit na 6.000 volle cycli, dus 0,0033 punt per cyclus. Het aantal volle cycli is de DC-ontladen kWh gedeeld door de bruikbare capaciteit, plus eventueel de cycli van vóór de monitoring. Het getal "specificatie" op de kaart is die lijn, doorgerekend naar het aantal cycli van nu (bijvoorbeeld 98,8 % bij 369 cycli).

Dit is een **specificatie, geen garantie**. Marstek geeft geen capaciteitsgarantie in jaren; daarom is er geen tijdlijn.

| Kleur | Betekenis |
|---|---|
| 🟢 Groen | Volgens specificatie, of maximaal 5 punten eronder |
| 🟠 Oranje | Onder specificatie, maar boven 75 % |
| 🔴 Rood | **75 % of lager**: meld het bij Marstek **via de Marstek-app** |

De marge laat zien hoeveel kWh de batterij boven of onder de specificatie zit. Alle grenzen kun je aanpassen.

De metingen zijn een **hulpmiddel bij een melding**, geen bewijs: ze laten zien hoe de capaciteit zich over maanden ontwikkelt.

De bronnen voor deze getallen staan in [Ondersteunde batterijen](05-supported-batteries.nl.md#bronnen-voor-de-specificaties-van-de-fabrikant).

## Status meting

Naast de status van de capaciteit heeft elke batterij een **status meting**. Die vertelt of de meting zelf werkt:

| Status | Betekenis |
|---|---|
| Meet | De sensoren leveren gegevens en er is minstens één volledige ontlading gemeten |
| Verzamelt data | De sensoren leveren gegevens; wacht op de eerste volledige ontlading |
| Geen recente data | De batterij was aan het laden of ontladen (meer dan 50 W), maar laadtoestand en vermogen hebben een uur geen nieuwe waarde doorgegeven; controleer de koppeling van de batterij. Een batterij die stilstaat (leeg of vol, rond 0 W) geeft vaak urenlang dezelfde waarden; dat telt niet mee |
| Sensor niet beschikbaar | De sensor voor laadtoestand of vermogen is niet beschikbaar |

De kaart toont de volgende stap op weg naar een meting: laden tot 95 % of meer, daarna ontladen tot 15 % of lager. Een ontlading die onderbroken is (gat in de gegevens) telt niet mee; de kaart meldt dat.

## Celbalans

Optioneel, als je koppeling de hoogste en laagste celspanning levert.

* **Gebeurtenis:** het einde van een volle lading (laadtoestand ≥ 95 %).
* **Context:** de batterij staat 5 minuten in rust (vermogen binnen ±50 W), zodat belasting de spanningen niet vertekent. LFP-cellen verschillen midden in de band nauwelijks; verschillen worden pas zichtbaar bij bijna vol.
* **Resultaat:** het verschil tussen de hoogste en laagste cel, in mV. Eén meting per volle lading; voor de volgende meting moet de batterij eerst onder de 90 % komen. De kaart toont het midden (mediaan) per maand, trendkolom eerst, nieuw → oud.

Het celverschil heeft **nog geen kleuren**: Marstek publiceert geen normaalwaarde. Grenzen komen er pas als genoeg gegevens van echte batterijen ze onderbouwen.

## Celtemperatuur (experimenteel)

Optioneel. Als je de hoogste en/of laagste celtemperatuur instelt, bewaart de monitor bij elke volledige ontlading de gemiddelde celtemperatuur bij die meting. De kaart toont die per maand onder de capaciteit (bijv. *spec. 98 · 16 °C*) en in de grafiek.

Waarom: een koude batterij geeft minder af. Een lagere meting in de winter wordt dan verklaard door de temperatuur, in plaats van aangezien voor slijtage. De temperatuur is alleen context; hij verandert de gemeten capaciteit en de kleuren niet.

Alleen **cel**temperaturen horen hier. Sommige koppelingen geven MOSFET-temperaturen (van de schakeltransistors) door als "celtemperatuur"; de scan stelt nooit sensoren voor met *mos*, *internal* of *board* in de naam.

## Grafiek

Druk op het knopje **Grafiek** onder de status om een grafiek te openen of te sluiten (oud → nieuw, van links naar rechts): de gemeten capaciteit per maand, de specificatie van de fabrikant als grijze stippellijn en 75 % als rode lijn. Standaard zie je de laatste 3 jaar; met *hele garantie* de hele garantietijd. Ga met de muis over een stip voor het getal en de celtemperatuur in die maand. Zie [06 – Dashboard en galerij](06-dashboard-gallery.nl.md) voor de kaart genummerd uitgelegd.
