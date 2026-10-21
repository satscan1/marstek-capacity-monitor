# Problemen oplossen

*[English](04-troubleshooting.md)*

| Wat je ziet | Waarom | Wat te doen |
|---|---|---|
| **"Verzamelt data"** | De batterij is sinds de start van de monitoring nog niet van 95 % of hoger naar 15 % of lager gezakt. In het najaar en de winter kan dat even duren. | Er is niets mis. Wil je snel een eerste meting: laat de batterij een keer vol laden en daarna helemaal leeglopen. |
| **De scan vindt geen batterij** | De scan zoekt een laadtoestand-sensor (%) en een vermogensensor met "battery power" in de naam, op hetzelfde apparaat of met hetzelfde begin van de naam. Sommige koppelingen gebruiken andere namen. | Kies **Zelf sensoren kiezen** en selecteer de twee sensoren zelf. |
| **Status "Geen recente data"** | De batterij was aan het laden of ontladen (meer dan 50 W), maar laadtoestand en vermogen hebben een uur geen nieuwe waarde doorgegeven. | Controleer de koppeling van de batterij (ESPHome-apparaat, Modbus-brug, MQTT). De status herstelt vanzelf zodra er weer gegevens binnenkomen. |
| **Status "Sensor niet beschikbaar"** | De sensor voor laadtoestand of vermogen is niet beschikbaar; de kaart noemt welke. | Controleer die integratie en de entiteit. Is de entiteit hernoemd, kies hem dan opnieuw via **Configureren** of voeg de batterij opnieuw toe. |
| **Celverschil blijft leeg** | Een meting vraagt een volle lading (≥ 95 %) en 5 minuten rust. Voor de volgende meting moet de batterij eerst onder de 90 % komen. | Niets; het volgt na de volgende volle lading. Controleer of beide celsensoren een spanning tonen (V of mV). |
| **Waarschuwing: "lijkt de AC-/netkant te meten"** | De gekozen vermogensensor heeft "ac", "grid", "net", "p1" of "meter" in de naam. AC-waarden bevatten omzetverlies en geven een verkeerde capaciteit. | Kies de sensor voor het batterijvermogen (DC). Alleen als je zeker weet dat het de DC-kant is: verstuur nogmaals om hem toch te gebruiken. |
| **Melding: "plus en min automatisch omgedraaid"** | Je vermogensensor toont laden als negatief getal. De monitor zag dat bij de eerste volle laad- of ontlaadbeurt en heeft het gecorrigeerd. | Niets. Heeft de herkenning het mis, stel het teken dan zelf in via **Configureren**. |
| **Een meting lijkt te ontbreken na een herstart** | Een herstart van Home Assistant tijdens een ontlading wordt overbrugd als hij hooguit 10 minuten duurt. Duurt hij langer, of was er geen vermogenswaarde vlak vóór de herstart, dan telt die beurt niet mee. | Niets; de volgende volledige ontlading telt weer. |
| **Percentage boven 100 %** | De interne reserve past niet bij je batterij: de bruikbare band staat te klein. | Kijk tot welk percentage je batterij bij een volle ontlading zakt en pas de reserve aan. Zie [Ondersteunde batterijen](05-supported-batteries.nl.md#ontlaaddiepte-per-model). |
| **Statistiekgrafiek op de standaardkaart is leeg** | Home Assistant bouwt langetermijnstatistieken per uur op; maandgemiddelden verschijnen na de eerste metingen. | Een paar dagen wachten; de overzichtskaart toont de waarden meteen. |
| **button-card toont een rode "sensor.marstek_… ?"** | De code van de batterij in de kaart klopt niet met de code die je koos (bv. `mt1`). | Gebruik in de kaart dezelfde code als bij het toevoegen. |

Verwijder je een batterij uit de integratie, dan blijven de metingen in `.storage/` staan. Zo kunnen ze nog steeds helpen bij een melding aan Marstek. Wil je bewust opnieuw beginnen, gebruik dan de actie `marstek_capacity_monitor.reset_measurements`.
