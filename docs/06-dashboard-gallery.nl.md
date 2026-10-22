# 06 – Dashboard: indeling, kaart en galerij

*[English](06-dashboard-gallery.md) · [Deutsch](06-dashboard-gallery.de.md)*

Op deze pagina zie je hoe de kaarten eruitzien bij 1 tot 6 batterijen, wat elk onderdeel van de batterijkaart betekent en hoe je de kaarten neerzet.

> Alle afbeeldingen op deze pagina gebruiken **demogegevens**: zes verzonnen batterijen met verschillende leeftijden en toestanden. Ze laten zien hoe de kaarten eruitzien, niet hoe een echte batterij veroudert.

## Indeling

De batterijkaart is gemaakt voor **een derde van de breedte**: drie batterijen naast elkaar.

| Aantal batterijen | Indeling |
|---|---|
| 1 of 2 | De batterijen, met het overzicht rechts ernaast (één rij van drie) |
| 3 | Overzicht twee derde breed, daaronder 3 batterijen |
| 4 | Overzicht twee derde breed, daaronder 2 × 2 |
| 5 | Overzicht twee derde breed, daaronder 3 + 2 |
| 6 | Overzicht twee derde breed, daaronder 3 + 3 |

Naast het overzicht is vanaf 3 batterijen een derde vrij voor een eigen kaart. Zet je daar niets neer, dan schuift Home Assistant de eerste batterij omhoog naast het overzicht; wil je de batterijen op een nieuwe rij, zet er dan een kaart neer (het dashboard met één klik, de kant-en-klare dashboards en de galerij gebruiken een tekstkaart "Vrije plek").

Het [dashboard met één klik](01-installation.nl.md#snelste-manier-dashboard-met-één-klik) gebruikt deze indeling vanzelf. Voor button-card staan er [kant-en-klare dashboards](01-installation.nl.md#kant-en-klaar-dashboard-met-button-card) klaar, één per aantal batterijen.

Zelf indelen? Gebruik hiervoor de standaardindeling van Home Assistant met **secties** ("Sections"). Een voorbeeld staat in [`dashboard/button-card/layout-sections.yaml`](../dashboard/button-card/layout-sections.yaml). Je geeft elke kaart een breedte met `grid_options`: in een sectie van drie kolommen is `columns: 12` een derde en `columns: 24` twee derde. Bij 4 batterijen gebruik je `columns: 18` per batterij.

## De batterijkaart

![Batterijkaart met nummers](../screenshots/gallery/card-numbered-nl.png)

1. **Status**: *Goed*, *Onder specificatie*, *Melden bij Marstek (app)* of *Verzamelt data*. De kleur volgt de laatste meting.
2. **Werkt de meting?** Groen: de meting werkt en zoveel volledige ontladingen zijn gemeten. Blauw: nog data aan het verzamelen. Oranje of rood: geen nieuwe gegevens of een sensor ontbreekt. De regel eronder zegt wat de volgende stap is (bijvoorbeeld *volledig laden tot 95 %*).
3. **Grafiek · SOC · Cellen** (vanaf 0.5 drie knopjes onder de regel *Meting werkt*): druk op een knopje om dat paneel te openen, nog eens om het te sluiten. Een ⚠ (let op) of 🔧 (advies) op *SOC* of *Cellen* betekent: kijk even. De rest van de kaart doet niets als je erop klikt. Het SOC-paneel beantwoordt *Klopt mijn SOC-meter nog?* met per maand *Dagen helemaal vol* en *SOC-meter klopte*; het Cellen-paneel *Zijn mijn cellen nog in balans?*. Bij let op of advies staat er een kader met wat je kunt doen en een knop **Wegklikken**. Zie [Hoe het werkt](03-how-it-works.nl.md#soc-drift-vanaf-05).
4. **Periode**: *recente 3 jaar van garantieperiode*: de grafiek toont de meest recente 3 jaar sinds de installatie.
5. **Grafiek**: elke stip is een maand, met hoeveel procent van de bruikbare capaciteit er toen nog was. De grijze stippellijn is wat de fabrikant op die leeftijd verwacht, de rode lijn is 75 %. Ga met de muis over een stip voor het precieze getal en de celtemperatuur in die maand (als je temperatuursensoren hebt gekoppeld). Een open stip ○ betekent *minder betrouwbaar*: de batterij was in de 14 dagen ervoor niet helemaal vol, of de cellen waren kouder dan 5 °C.
6. **Drie capaciteiten**: *Opgegeven* (op het typeplaatje), *Bruikbaar* (opgegeven min de reserve die de batterij zelf vasthoudt) en *Gemeten* (wat er nu echt uitkomt, en hoeveel procent van bruikbaar dat is).
7. **Balk**: de gemeten capaciteit, met een wit streepje voor de specificatie van de fabrikant en een rood streepje bij 75 %.
8. **Specificatie van de fabrikant** bij het huidige aantal cycli en de leeftijd, en de marge: hoeveel je erboven (+) of eronder (−) zit.
9. **Trend per maand**: eerst de richting (▲ ▬ ▼), dan de maanden van nieuw naar oud. Groot getal = gemeten, klein getal = specificatie voor die maand, en eventueel de celtemperatuur.
10. **Laatste volle ontlading en volle lading**, en het aantal metingen.

Heb je sensoren voor de hoogste en laagste celspanning gekoppeld, dan staat het **celverschil na volle lading** in het paneel **Cellen** (tot en met 0.4 onder de trend).

## Het overzicht

Het overzicht zet alle batterijen (tot 6) onder elkaar:

- **Batterij**: met ✓ (meting werkt), ⏳ (verzamelt data) of ⚠ (controleer de koppeling). Vanaf 0.5 ook ⚠ (let op) of 🔧 (advies) voor SOC-drift of celkalibratie; wijs hem aan om te zien welke, en open de kaart van die batterij.
- **Trend**: ▲ stijgend, ▬ gelijk, ▼ dalend over de getoonde maanden.
- **Nu**: de laatste meting.
- **Maanden**, van nieuw naar oud: groot getal = gemeten, klein getal = specificatie voor die maand.
- **Specificatie**: wat de fabrikant nu verwacht.

Groen: binnen 5 punten van de specificatie. Oranje: daaronder. Rood: 75 % of lager, melden via de Marstek-app.

## Galerij

De zes demobatterijen laten elk een andere situatie zien:

| Batterij | Situatie |
|---|---|
| Demo 1 | 4 jaar oud, goed; staat buiten, dus open stippen in de winter; SOC-meter 2× flink ernaast: ⚠ let op bij SOC |
| Demo 2 | 1,6 jaar oud, goed, met celverschil: 🔧 celkalibratie aanbevolen |
| Demo 3 | Net geïnstalleerd: verzamelt data voor de eerste meting |
| Demo 4 | 6,5 jaar oud, onder specificatie (oranje) |
| Demo 5 | 9 jaar oud, net onder 75 %: melden bij Marstek (rood), cellen in balans |
| Demo 6 | 2,8 jaar oud, goed, maar al even geen nieuwe gegevens (⚠) |

### 1 batterij

![1 batterij](../screenshots/gallery/1-battery.png)
![1 batterij met grafiek](../screenshots/gallery/1-battery-chart.png)

### 2 batterijen

![2 batterijen](../screenshots/gallery/2-batteries.png)
![2 batterijen met grafieken](../screenshots/gallery/2-batteries-chart.png)

### 3 batterijen

![3 batterijen](../screenshots/gallery/3-batteries.png)
![3 batterijen met grafieken](../screenshots/gallery/3-batteries-chart.png)

### 4 batterijen

![4 batterijen](../screenshots/gallery/4-batteries.png)
![4 batterijen met grafieken](../screenshots/gallery/4-batteries-chart.png)

### 5 batterijen

![5 batterijen](../screenshots/gallery/5-batteries.png)
![5 batterijen met grafieken](../screenshots/gallery/5-batteries-chart.png)

### 6 batterijen

![6 batterijen](../screenshots/gallery/6-batteries.png)
![6 batterijen met grafieken](../screenshots/gallery/6-batteries-chart.png)

## Zelf een demo bekijken

De kaarten kennen nepgegevens via de optie `demo` (bij button-card: de variabele `demo`). De galerij hierboven is daarmee gemaakt. Die gegevens staan alleen in de dashboardinstellingen: er worden geen sensoren aangemaakt en er komt niets in je geschiedenis. Voor normaal gebruik heb je dit niet nodig.
