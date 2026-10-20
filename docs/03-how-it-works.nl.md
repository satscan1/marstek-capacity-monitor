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

Gedeeltelijke ontladingen tellen bewust niet mee: een procent onderin levert meer kWh dan een procent bovenin. Valt er tijdens een beurt een gat van meer dan 5 minuten in de vermogensgegevens, bijvoorbeeld door een herstart, dan telt die beurt niet mee.

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
