# 07 – Hoe de monitor meet

*[English](07-measuring-method.md) · [Deutsch](07-measuring-method.de.md)*

## Wat is 100 %?

**100 % is wat er volgens de fabrikant bruikbaar is: de capaciteit op het typeplaatje min de vaste reserve (ontlaaddiepte).**

Voorbeeld met een Venus E van 5,12 kWh en een reserve van 11 %:

| | kWh | % |
|---|---|---|
| Typeplaatje | 5,12 | |
| Vaste reserve (11 %) | − 0,56 | |
| **Bruikbaar volgens specificatie** | **4,56** | **100 %** |
| Gemeten door de monitor | 4,87 | 106,7 % |

### Hoe de monitor op dat getal komt
De monitor meet een volledige ontlading: begin op 95 % of hoger, einde op 15 % of lager. Hij hoeft dus niet van precies 100 naar 0 te gaan. Hij rekent de gemeten energie om naar het hele bruikbare deel en zet dat naast de specificatie. In het voorbeeld kwam daar 4,87 kWh uit: iets meer dan beloofd.

### Waarom de Marstek-app een ander getal geeft
De app toont bijvoorbeeld 5,59 kWh voor een lading van 11 naar 100 %. Dat is gemeten aan de **AC-kant**: wat er de batterij in gaat, inclusief de verliezen van omvormer en laden. De monitor meet aan de **DC-kant**: wat er echt uit de batterij komt. Het app-getal is daarom altijd hoger. Die twee kun je niet vergelijken.

### Waarom bijladen de meting ongeldig maakt
Een meting is één ontlading in één keer, van 95 % of hoger naar 15 % of lager. Laadt de batterij onderweg 3 procentpunten of meer bij (zon, een automation of EMS), dan stopt die meting en telt hij niet mee. Laden kost meer energie per procent dan ontladen oplevert. Meng je die twee, dan is niet zuiver vast te stellen hoeveel er echt uit de batterij kwam. Meer daarover hieronder.

## Kun je de capaciteit ook meten als de batterij tussendoor laadt?

De monitor meet alleen bij een volledige ontlading (van 95 % of meer naar 15 % of minder). Kan het niet slimmer, door laden en ontladen tussendoor uit elkaar te halen? Om dat uit te zoeken is bijna een jaar data van twee Venus E's bekeken (december 2025 – oktober 2026). Conclusie: technisch kan het, maar je meet dan niet betrouwbaar de capaciteit. De beperking zit in de SOC-meter van de batterij zelf.

### AC of DC maakt hier niet uit
De monitor meet aan de batterijkant (DC). Ter controle: bij elke volledige ontlading was AC eruit gedeeld door DC eruit steeds 0,84–0,87. De DC-meting klopt dus.

### Wat de data laat zien
- **Laden en ontladen netto optellen is onzuiver.** In het midden kost laden ongeveer 54 Wh per procent, terwijl ontladen ongeveer 50 Wh oplevert. Meng je die twee, dan is de fout even groot als de slijtage die je zoekt (bij de testbatterijen ongeveer 3 % in anderhalf jaar).
- **Alleen de ontlaadstukjes tellen is te onrustig.** Zelfs in rustige maanden schommelt het midden per week tussen 46 en 53 Wh per procent. Dat is ± 5 %, terwijl de slijtage 1,5–2 % per jaar is.
- **De batterij meldt altijd 5,12 kWh als totale capaciteit**, ook een exemplaar van ruim twee jaar oud. Een procent is dus wat de batterij zelf een procent noemt, geen vaste hoeveelheid energie uit de cellen.
- **De SOC-meter kan wekenlang verschuiven.** Van eind maart tot eind april leverde één batterij per procent 15–30 % minder energie. Dat gold in het midden én over een volledige ontlading (3,1–3,9 kWh in plaats van ongeveer 4,2). De AC-meting bevestigde het. Daarna was het weer normaal.

### Waarom er (nog) geen goede oplossing is
Voor een zuivere meting heb je twee echte ijkpunten nodig: echt vol en echt leeg. Vol lukt, want dan zet de batterij zijn teller zelf recht. Leeg lukt niet: de batterij stopt op de ontlaadgrens uit de app, dus op een SOC-percentage en niet op een spanning. In het midden is de spanning van LiFePO4 te vlak om als ijkpunt te dienen.

### Wat de monitor daarom doet
Hij meet alleen bij volledige ontladingen en toont de mediaan van de laatste drie. Een meting krijgt een open stip (minder betrouwbaar) als er geen recent ijkpunt was, als de cellen koud waren of als de randen afwijken. Het blijft een hulpmiddel en geen bewijs, maar wel het beste wat met de SOC van de batterij kan.

## Waarom een batterij boven 100 % kan uitkomen

Marstek rekent de capaciteit op het typeplaatje met 3,2 V per cel: 16 cellen × 3,2 V × 100 Ah = 5,12 kWh. In werkelijkheid ligt de spanning tijdens het ontladen rond 52–53 V. Daardoor komt er per procent ongeveer 2 % meer energie uit dan het typeplaatje zegt. Dat is een rekenafspraak, geen verborgen reserve: die energie krijg je nu al. Het is bij iedereen zo en blijft gelijk, dus voor de daling door de tijd maakt het niets uit. De monitor corrigeert er daarom bewust niet voor. Daarnaast leveren nieuwe cellen vaak iets meer dan het typeplaatje.

De echte reserve is de ontlaaddiepte: de batterij gebruikt ongeveer 90 % van zijn cellen (sommige exemplaren 88 %). Het onderste stuk blijft onbenut.

## Hoe zeker is de waarde op de kaart?

- **Boven 100 %:** grijs met "voorlopig" tot **5 metingen achter elkaar** boven 100 % liggen, niet meer dan 3 punten uit elkaar. Daarna groen met "boven nieuw".
- **Ineens meer dan 5 punten lager:** grijs met "nog niet bevestigd". Echte slijtage gaat langzaam; zo'n sprong is bijna altijd een tijdelijk verschoven SOC-meter (zie hierboven). Blijft de lagere waarde 5 metingen achter elkaar, dan telt hij als echt. Herstelt hij, dan verdwijnt de melding vanzelf.
- **Sinds begin meting:** de verandering ten opzichte van het midden van de eerste 3 metingen van deze monitor. Zo maakt het niet uit of een batterij op 96 % of op 105 % begon.
