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

Marstek publiceert geen normaalwaarde voor het celverschil. Vanaf 0.5 vergelijkt de monitor daarom met wat normaal is voor **jouw** batterij (de eerste 3 maanden): een ⚠ bij 2× zo veel. Zie Celkalibratie hieronder.

## SOC-drift (vanaf 0.5)

**Wat is het?** De batterij weet niet precies hoe vol hij is; de laadtoestand (SOC) is een schatting die hij bijhoudt door stroom op te tellen. Kleine fouten stapelen zich op. Alleen als de batterij helemaal vol is (het laden stopt vanzelf) zet hij de teller weer recht. Gebeurt dat lang niet, dan gaat de SOC-meter steeds verder ernaast zitten: **SOC-drift**. Je merkt het aan sprongen (bijv. van 57 % naar 91 % in een minuut), aan "99 %" waarbij nog veel bijgeladen wordt, of aan een batterij die lang op 100 % blijft hangen terwijl hij ontlaadt.

**Waarom is het belangrijk?** Met een scheve SOC-meter stopt de batterij te vroeg of te laat, en een capaciteitsmeting wordt minder zeker. Daarom krijgt een meting in de grafiek een **open stip** als de batterij in de 14 dagen ervoor niet helemaal vol is geweest (of als de cellen kouder waren dan 5 °C).

**Hoe meet de monitor het?**
* **Gebeurtenis:** de laadtoestand verandert.
* **Context:** het opgetelde DC-vermogen. Loopt de SOC meer dan 3 % harder dan de energie verklaart, dan is dat een correctie. Gaten in de gegevens, een herstart, kortstondig 0 % en sprongen die tegelijk bij een andere batterij gebeuren (dan ligt het aan de koppeling) tellen niet mee.
* **Resultaat:** een **voorval** is een afwijking van 5 % of meer, of 14 dagen niet helemaal vol (terwijl Home Assistant draaide). Een voorval telt alleen als de batterij in de 14 dagen ervoor op minder dan 7 dagen helemaal vol was; een batterij die bijna elke dag vol is, corrigeert zichzelf al.

**De meldladder** (termijn 45 dagen):

| Aantal voorvallen in 45 dagen | Wat je ziet | Wat te doen |
|---|---|---|
| 1 | niets, alleen vastgelegd | – |
| 2 | ⚠ **Let op** | ontlaad de batterij **één keer** tot de ontlaadgrens en laad hem daarna in één keer vol, tot het laden echt stopt |
| 3 | 🔧 **SOC-drift geconstateerd** | doe dat **twee keer** |

De monitor ziet zelf wanneer je dat gedaan hebt (een ontlading tot 20 % of lager, daarna helemaal vol); de melding verdwijnt dan. Na 45 dagen zonder nieuw voorval verdwijnt hij ook vanzelf.

## Celkalibratie (vanaf 0.5)

**Wat is het?** De cellen in een batterij lopen langzaam uit elkaar: de ene cel is eerder vol dan de andere. De batterij brengt ze weer gelijk (balanceren), maar alleen als hij een tijd **vol en in rust** staat. Staat hij nooit lang vol, dan wordt het celverschil groter en kan de batterij minder kwijt.

**Hoe meet de monitor het?** Met de hoogste en laagste celspanning (optioneel, zie Celbalans hierboven). Wat normaal is, verschilt per batterij; de monitor neemt daarom het midden van de **eerste 3 maanden** als normaal. Een **voorval** is een celverschil van **2× normaal** of meer.

| Wanneer | Wat je ziet | Wat te doen |
|---|---|---|
| 2 voorvallen achter elkaar | ⚠ **Let op** | laad de batterij vol en laat hem ongeveer **4 uur** vol staan (heeft je model een UPS-modus: zet die in de Marstek-app 4 uur aan en daarna terug naar je eigen modus) |
| 3 voorvallen in 45 dagen | 🔧 **Celkalibratie aanbevolen** | laad vol en zet **UPS-modus 8 uur** aan (geen UPS-modus: laat hem 8 uur in de laadmodus staan), daarna terug naar je eigen modus. Kalibreren duurt lang. Blijft het celverschil daarna hoog, meld het dan via de Marstek-app |

De monitor ziet zelf hoe lang de batterij vol en in rust stond (4 uur bij let op, 8 uur bij advies); de melding verdwijnt dan.

## Seintjes en wegklikken (vanaf 0.5)

* **Waar:** op de kaart (knoppen **SOC** en **Cellen** met ⚠ of 🔧), als bericht op je telefoon (Home Assistant-app) en onder **Instellingen → Reparaties**.
* **Wegklikken:** één klik is genoeg: **Wegklikken** op de kaart, in het bericht op je telefoon, of **Negeren** onder Reparaties. Dat geldt overal. De melding komt pas terug bij een nieuwe reeks voorvallen.
* **Helemaal uit:** per batterij via **Configureren → Seintjes** (staat standaard aan). De kaart blijft de stand tonen; je krijgt alleen geen berichten meer.
* Voor automatiseringen: de sensoren `sensor.marstek_<id>_soc_health` en `sensor.marstek_<id>_cell_health` (ok / letop / advies), het event `marstek_capacity_monitor_advice` en de dienst `marstek_capacity_monitor.dismiss_advice`.

## Celtemperatuur (experimenteel)

Optioneel. Als je de hoogste en/of laagste celtemperatuur instelt, bewaart de monitor bij elke volledige ontlading de gemiddelde celtemperatuur bij die meting. De kaart toont die per maand onder de capaciteit (bijv. *spec. 98 · 16 °C*) en in de grafiek.

Waarom: een koude batterij geeft minder af. Een lagere meting in de winter wordt dan verklaard door de temperatuur, in plaats van aangezien voor slijtage. De temperatuur is alleen context; hij verandert de gemeten capaciteit en de kleuren niet.

Alleen **cel**temperaturen horen hier. Sommige koppelingen geven MOSFET-temperaturen (van de schakeltransistors) door als "celtemperatuur"; de scan stelt nooit sensoren voor met *mos*, *internal* of *board* in de naam.

## Grafiek

Onder de status staan drie knopjes: **Grafiek · SOC · Cellen**. Er is steeds één paneel open; druk nog eens op hetzelfde knopje om het te sluiten. De grafiek (oud → nieuw, van links naar rechts) toont de meest recente 3 jaar en verder alleen:

* **●** gemeten, geijkt
* **○** minder betrouwbaar: in de 14 dagen vóór de meting niet helemaal vol, of cellen kouder dan 5 °C
* **grijze stippellijn**: verwacht volgens specificatie
* **rode stippellijn**: melden bij Marstek (75 %)

Ga met de muis over een stip voor het getal, de celtemperatuur en waarom hij minder betrouwbaar is. Het paneel **SOC** toont per maand *Dagen helemaal vol* en *SOC-meter klopte* (✓ of ⚠ met hoeveel hij ernaast zat); **Cellen** toont *Cellen in balans* (celverschil in mV, ⚠ bij 2× normaal). Ook daar staan de details bij aanwijzen van een vakje. Zie [06 – Dashboard en galerij](06-dashboard-gallery.nl.md) voor de kaart genummerd uitgelegd.
