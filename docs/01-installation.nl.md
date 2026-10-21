# Installatie

*[English](01-installation.md)*

## Wat heb je nodig?

Per batterij twee sensoren die je vrijwel zeker al hebt:

* de **laadtoestand** (SOC, %);
* het **DC-vermogen van de batterij** (W of kW), dus de batterijkant en niet de AC-/netkant.

Je hoeft **geen nieuwe sensoren** te maken. Bij het toevoegen zoekt de integratie zelf welke sensoren er in Home Assistant zijn en doet per batterij een voorstel.

Welke modellen en koppelingen werken: zie [Ondersteunde batterijen](05-supported-batteries.nl.md).

**Plus of min hoef je niet in te stellen.** De ene integratie toont laden als plus, de andere als min. Bij de eerste volle laad- of ontlaadbeurt herkent de tool het zelf en draait het teken zo nodig om. Je krijgt daar een melding van. Je kunt het teken ook vast instellen.

## Integratie installeren

**Via HACS (custom repository)**

1. Ga in HACS naar de drie puntjes → *Custom repositories*. Vul de URL van deze repo in, type *Integration*.
2. Installeer **Marstek Capacity Monitor** en herstart Home Assistant.

**Handmatig**

Kopieer `custom_components/marstek_capacity_monitor` naar `/config/custom_components/` en herstart.

**Per batterij toevoegen**

Ga naar **Instellingen → Apparaten & diensten → Integratie toevoegen → Marstek Capacity Monitor**.

1. Kies een gevonden batterij, of kies zelf de sensoren.
2. Controleer de korte code (`mt1` … `mt6`), de naam en de twee sensoren. Optioneel: de hoogste en laagste celspanning, voor de [celbalans](03-how-it-works.nl.md#celbalans). Die worden ingevuld als de scan ze vindt.
3. Kies het model en vul de installatiedatum in. Bij een Venus E v1/v2, Venus E v3 of Venus D worden de fabrieksgegevens voor je ingevuld (Venus D: ook het aantal pakketten). Bij een ander model vul je de fabrieksgegevens zelf in.

Alle fabrieksgegevens kun je later aanpassen via **Configureren**.

Na het toevoegen toont de batterij **verzamelt data** tot de eerste volledige ontlading (≥ 95 % → ≤ 15 %). De statusregel op de kaart vertelt wat de volgende stap is.

## Kaarten toevoegen

De kaarten gebruiken [button-card](https://github.com/custom-cards/button-card). Installeer die eerst: in HACS zoeken op **button-card** → **Downloaden**, daarna de pagina in je browser vernieuwen (Ctrl+F5).

### Snelste manier: kant-en-klaar dashboard

In [`dashboard/ready-made/nl/`](../dashboard/ready-made/nl/) staat per aantal batterijen een compleet dashboard: `1-batterij.yaml` tot en met `6-batterijen.yaml`. Alles staat er al in, in de [indeling](06-dashboard-gallery.nl.md#indeling) van de galerij.

1. Ga naar **Instellingen → Dashboards → Voeg dashboard toe → Leeg nieuw dashboard**. Geef het een naam, bijvoorbeeld *Batterijcapaciteit*, en open het.
2. Klik rechtsboven op het **potlood**, dan op de **drie puntjes → Ruwe configuratie-editor**.
3. Open het bestand voor jouw aantal batterijen op GitHub, kopieer alles (knop *Copy raw file*) en plak het over wat er in de editor staat (Ctrl+A, dan Ctrl+V).
4. Heb je bij het toevoegen de voorgestelde codes `mt1`, `mt2`, … gehouden? Dan hoef je niets te veranderen. Anders vervang je ze door je eigen codes; die zie je terug in de sensornamen, bijvoorbeeld `sensor.marstek_mt1_capacity_pct`. De namen op de kaarten pas je aan bij `name:`.
5. Klik op **Opslaan** en sluit de editor.

### In een bestaand dashboard

1. **Sjablonen (eenmalig per dashboard):** open het dashboard, klik op het **potlood**, dan op de **drie puntjes → Ruwe configuratie-editor**. Kopieer alles uit [`marstek_capacity_templates.yaml`](../dashboard/button-card/marstek_capacity_templates.yaml) en plak het helemaal bovenaan, boven de regel `views:`. Staat er al een regel `button_card_templates:` (van andere kaarten)? Plak dan alleen wat eronder staat, onder je bestaande sjablonen. Opslaan en de editor sluiten.
2. **Kaarten:** nog steeds in bewerken: **Kaart toevoegen** → helemaal onderaan **Handmatig**. [`examples.yaml`](../dashboard/button-card/examples.yaml) bevat twee voorbeelden, gescheiden door een regel `---`: eerst het overzicht van al je batterijen, daarna de kaart voor één batterij. Plak telkens één voorbeeld, niet het hele bestand. Vervang overal `mt1` door je eigen code (`lang: nl` geeft Nederlandse tekst, `lang: en` Engelse) en sla op. Herhaal dit per batterij en voor het overzicht.

Hoe je de kaarten naast elkaar zet en wat alles op de kaart betekent: [06 – Dashboard en galerij](06-dashboard-gallery.nl.md).

### Zonder button-card

In [`dashboard/standard/`](../dashboard/standard/) staan een entiteitenkaart en een statistiekgrafiek (nog beschikbaar tegenover specificatie per maand) die met de standaardkaarten van Home Assistant werken. Toevoegen gaat zoals bij stap 2 van *In een bestaand dashboard*.
