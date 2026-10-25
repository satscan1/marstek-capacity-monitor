# Installatie

*[English](01-installation.md) · [Deutsch](01-installation.de.md)*

## Wat heb je nodig?

Per batterij twee sensoren die je vrijwel zeker al hebt:

* de **laadtoestand** (SOC, %);
* het **DC-vermogen van de batterij** (W of kW), dus de batterijkant en niet de AC-/netkant.

Je hoeft **geen nieuwe sensoren** te maken. Bij het toevoegen zoekt de integratie zelf welke sensoren er in Home Assistant zijn en doet per batterij een voorstel.

Welke modellen en koppelingen werken: zie [Ondersteunde batterijen](05-supported-batteries.nl.md).

**Plus of min hoef je niet in te stellen.** De ene integratie toont laden als plus, de andere als min. Bij de eerste volle laad- of ontlaadbeurt herkent de tool het zelf en draait het teken zo nodig om. Je krijgt daar een melding van. Je kunt het teken ook vast instellen.

## Integratie installeren

**Via HACS**

[![Open in HACS in je Home Assistant](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=satscan1&repository=marstek-capacity-monitor&category=integration)

Deze knop opent de monitor meteen in HACS in je eigen Home Assistant. Of zonder knop:

1. Zoek in HACS op **Marstek Capacity Monitor**.
2. Download hem en herstart Home Assistant.

Niet gevonden in HACS? Voeg hem toe als custom repository: drie puntjes → *Custom repositories* → URL van deze repo, type *Integration*. Ga daarna verder met stap 2.

**Handmatig**

Kopieer `custom_components/marstek_capacity_monitor` naar `/config/custom_components/` en herstart.

**Per batterij toevoegen**

Ga naar **Instellingen → Apparaten en diensten → Voeg integratie toe → Marstek Capacity Monitor**.

1. Kies een gevonden batterij, of kies zelf de sensoren.
2. Controleer de korte code (`mt1` … `mt6`), de naam en de twee sensoren. Optioneel: de hoogste en laagste celspanning, voor de [celbalans](03-how-it-works.nl.md#celbalans). Die worden ingevuld als de scan ze vindt.
3. Kies het model en vul de installatiedatum in. Bij een bekend model (Venus E v1/v2, v3, 4.0, Max of Pro, Venus C of Venus D) worden de fabrieksgegevens voor je ingevuld (Venus D en Venus E Pro: ook het aantal pakketten). Bij een ander model vul je de fabrieksgegevens zelf in.
   Een **Venus C** kan zich melden met dezelfde code als een Venus E v1/v2. Kies dan zelf **Venus C**, ook als Venus E v1 / v2 al is aangevinkt.

Alle fabrieksgegevens kun je later aanpassen via **Configureer**.

Bij het toevoegen kijkt de tool in de geschiedenis van Home Assistant (meestal de laatste 10 dagen) of er al een volledige ontlading was. Zo ja, dan staat er meteen een eerste meting. Anders toont de batterij **verzamelt data** tot de eerste volledige ontlading (≥ 95 % → ≤ 15 %). De statusregel op de kaart vertelt wat de volgende stap is.

## Kaarten toevoegen

Vanaf versie 0.4.0 heeft de integratie zijn eigen kaarten. Je hoeft niets extra's te installeren: geen button-card en geen sjablonen. Voeg eerst minstens één batterij toe. Herstart daarna Home Assistant en vernieuw de pagina in je browser (Ctrl+F5, op een Mac Cmd+Shift+R); dat geldt ook na elke update.

### Vanzelf in de zijbalk (vanaf 0.5.1)

Na het toevoegen van de eerste batterij en een herstart staat **Batterijcapaciteit** vanzelf in de zijbalk, met al je batterijen erin (1 tot 6, in de [indeling](06-dashboard-gallery.nl.md#indeling) van de galerij). Je hoeft niets in te stellen. Dit dashboard pas je niet aan; wil je een eigen indeling, maak dan zelf een dashboard zoals hieronder.

- **Uitzetten:** Instellingen → Apparaten en diensten → Marstek Capacity Monitor → **Configureren** → **Menu-item in de zijbalk**. Staat het bij één batterij uit, dan verdwijnt het hele menu-item.
- **Verborgen of op de verkeerde plek?** Houd **Home Assistant** bovenaan de zijbalk ingedrukt (of ga naar je profiel → zijbalk aanpassen). Daar zet je items terug, verberg je ze of verschuif je ze. Dat geldt per apparaat: op je telefoon stel je het apart in.
- Heb je zelf al een dashboard op het adres `/marstek-capacity`, dan laat de monitor dat met rust.

### Snelste manier: dashboard met één klik

1. Ga naar **Instellingen → Dashboards → Voeg dashboard toe**.
2. Kies onderaan, bij **Community-dashboards**, **Marstek battery capacity**.
3. Geef het een naam (bijvoorbeeld *Batterijcapaciteit*) en klik op **Maak aan**.

Het dashboard zet je batterijen vanzelf in de [indeling](06-dashboard-gallery.nl.md#indeling) van de galerij, voor 1 tot 6 batterijen. Voeg je later een batterij toe, dan staat die er ook vanzelf bij.

Deze keuze zit in Home Assistant 2026.5 en nieuwer. Met een oudere versie: maak een **Leeg nieuw dashboard**, open het, klik op het **potlood**, dan op de **drie puntjes → Ruwe configuratie-editor**, vervang alles door deze twee regels en sla op:

```yaml
strategy:
  type: custom:marstek-capacity
```

### Losse kaarten in je eigen dashboard

Open je dashboard, klik op het **potlood** en dan op **Voeg kaart toe**. Zoek op **Marstek**:

- **Marstek capacity (battery)**: één batterij, met de grafiek. Zonder instelling pakt hij je eerste batterij.
- **Marstek capacity (overview)**: al je batterijen per maand.

De kaarten vinden je batterijen, hun namen en de taal van Home Assistant zelf. Wil je iets anders, dan kan dat in de code-editor van de kaart:

```yaml
type: custom:marstek-capacity-card
battery: mt2        # de code van de batterij (zie de sensornamen, bijv. sensor.marstek_mt2_capacity_pct)
name: Garage        # andere naam op de kaart
months: 6           # aantal maanden in de trend
lang: nl            # nl, en of de; standaard de taal van Home Assistant
```

Bij het overzicht kun je kiezen welke batterijen erin staan: `batteries: [mt1, mt2]`.

Hoe je de kaarten naast elkaar zet en wat alles op de kaart betekent: [06 – Dashboard en galerij](06-dashboard-gallery.nl.md).

### Met button-card (zoals vóór 0.4.0)

Gebruik je de button-card-kaarten al, dan blijven die gewoon werken. Overstappen hoeft niet, maar het kan: de nieuwe kaarten zien er hetzelfde uit.

Deze kaarten gebruiken [button-card](https://github.com/custom-cards/button-card). Installeer die eerst: in HACS zoeken op **button-card** → **Downloaden**, daarna de pagina in je browser vernieuwen (Ctrl+F5).

#### Kant-en-klaar dashboard met button-card

In [`dashboard/ready-made/nl/`](../dashboard/ready-made/nl/) staat per aantal batterijen een compleet dashboard: `1-batterij.yaml` tot en met `6-batterijen.yaml`. Alles staat er al in, in de [indeling](06-dashboard-gallery.nl.md#indeling) van de galerij.

1. Ga naar **Instellingen → Dashboards → Voeg dashboard toe → Leeg nieuw dashboard**. Geef het een naam, bijvoorbeeld *Batterijcapaciteit*, en open het.
2. Klik rechtsboven op het **potlood**, dan op de **drie puntjes → Ruwe configuratie-editor**.
3. Open het bestand voor jouw aantal batterijen op GitHub, kopieer alles (knop *Copy raw file*) en plak het over wat er in de editor staat (Ctrl+A, dan Ctrl+V).
4. Heb je bij het toevoegen de voorgestelde codes `mt1`, `mt2`, … gehouden? Dan hoef je niets te veranderen. Anders vervang je ze door je eigen codes; die zie je terug in de sensornamen, bijvoorbeeld `sensor.marstek_mt1_capacity_pct`. De namen op de kaarten pas je aan bij `name:`.
5. Klik op **Bewaar** en sluit de editor.

#### In een bestaand dashboard

1. **Sjablonen (eenmalig per dashboard):** open het dashboard, klik op het **potlood**, dan op de **drie puntjes → Ruwe configuratie-editor**. Kopieer alles uit [`marstek_capacity_templates.yaml`](../dashboard/button-card/marstek_capacity_templates.yaml) en plak het helemaal bovenaan, boven de regel `views:`. Staat er al een regel `button_card_templates:` (van andere kaarten)? Plak dan alleen wat eronder staat, onder je bestaande sjablonen. Bewaar en sluit de editor.
2. **Kaarten:** nog steeds in bewerken: **Voeg kaart toe** → helemaal onderaan **Handmatig**. [`examples.yaml`](../dashboard/button-card/examples.yaml) bevat twee voorbeelden, gescheiden door een regel `---`: eerst het overzicht van al je batterijen, daarna de kaart voor één batterij. Plak telkens één voorbeeld, niet het hele bestand. Vervang overal `mt1` door je eigen code en sla op. De tekst volgt de taal van Home Assistant; een vaste taal kan met `lang: nl`, `lang: en` of `lang: de` onder `variables`. Herhaal dit per batterij en voor het overzicht.

Hoe je de kaarten naast elkaar zet en wat alles op de kaart betekent: [06 – Dashboard en galerij](06-dashboard-gallery.nl.md).

#### Alleen standaardkaarten van Home Assistant

In [`dashboard/standard/`](../dashboard/standard/) staan een entiteitenkaart en een statistiekgrafiek (nog beschikbaar tegenover specificatie per maand) die met de standaardkaarten van Home Assistant werken. Toevoegen gaat zoals bij stap 2 van *In een bestaand dashboard*.
