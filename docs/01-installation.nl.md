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
2. Controleer de korte code (`mt1` … `mt6`), de naam en de twee sensoren.
3. Vul de fabrieksgegevens in: fabriekscapaciteit, reserve, aankoopdatum, garantietermijn en cycli. De standaardwaarden komen uit de datasheet van de Venus E.

## Kaarten toevoegen

| Map | Vereist | Inhoud |
|---|---|---|
| `dashboard/button-card/` | [button-card](https://github.com/custom-cards/button-card) (HACS) | Overzicht van maximaal 6 batterijen: per maand, trendkolom eerst, nieuw → oud. Daarnaast een detailkaart per batterij. Taal instellen met `lang: nl` of `en`. |
| `dashboard/standard/` | niets | Entiteitenkaart en statistiekgrafiek (nog beschikbaar tegenover specificatie per maand) |
