# Ondersteunde batterijen

*[English](05-supported-batteries.md)*

| Marstek | Hoe hij meestal in HA zit | Laadtoestand | DC-vermogen |
|---|---|---|---|
| Venus E v1 / v2, Venus C | RS485 via ESPHome (LilyGo, M5Stack) of via een RS485-netwerkbrug (Elfin EW11) met een Modbus-integratie | register 32104 | register 32102 |
| Venus E v3, Venus A, Venus D | Ingebouwde LAN-poort met Modbus TCP | register 34002 | register 30001 |

**Modbus is niet nodig.** Elke koppeling werkt, zolang die de laadtoestand en het **DC**-vermogen van de batterij als sensor in Home Assistant levert: ESPHome, Modbus (RS485 of LAN) of een andere integratie. De tabel geeft de gecontroleerde modellen en Modbus-routes; alleen de registers verschillen, de gegevens zijn hetzelfde.

**MQTT (hm2mqtt):** getest met een nagebootste Venus E v1/v2: de scan vindt *Battery State of Charge* en *Battery Power*, en beide tekens werken. Nog niet bevestigd met een echte batterij; of oudere v1/v2-firmware *Battery Power* meestuurt, is onbekend. Voor de celbalans met hm2mqtt: zet in hm2mqtt *Cell Data* aan en schakel in Home Assistant de entiteiten *Max Cell Voltage* en *Min Cell Voltage* in (die staan standaard uit). Ervaringen zijn welkom via Issues.

**Celtemperaturen:** sommige koppelingen (waaronder MQTT bij de v1/v2) geven MOSFET-temperaturen door als "celtemperatuur". Deze tool gebruikt alleen echte celtemperaturen (optioneel, als context bij elke meting), nooit MOS-temperaturen; de scan slaat sensoren met MOS, board of internal in de naam over. Voor de celbalans gebruikt hij de hoogste en laagste cel**spanning**.

Integraties zoals [marstek_venus_modbus](https://github.com/ViperRNMC/marstek_venus_modbus) en [Omnibattery](https://github.com/ffunes/Omnibattery), en de gangbare ESPHome-configuraties, leveren beide sensoren.

**Niet ondersteund:** koppelingen die alleen het AC-vermogen leveren, zoals de meeste cloudkoppelingen. AC-waarden bevatten omzetverlies en geven daardoor een verkeerde capaciteit. Kies je toch een sensor die op AC lijkt, dan krijg je een waarschuwing.

## Fabrieksgegevens per model

Bij het toevoegen kies je het model; deze waarden worden dan ingevuld. Je kunt ze later aanpassen via **Configureer**.

| Model | Opgegeven capaciteit | Reserve (ontlaaddiepte) | Cycli · capaciteit daarna | Garantietermijn |
|---|---|---|---|---|
| Venus E v1 / v2 | 5,12 kWh | 0,51 kWh (90 %) | 6.000 · 80 % | 10 jaar |
| Venus E v3 | 5,12 kWh | 0,51 kWh (90 %) | 6.000 · 80 % | 10 jaar |
| Venus C | 2,56 kWh | 0,26 kWh (90 %) | 6.000 · 80 % ⁴ | 10 jaar |
| Venus D | 2,56 kWh per pakket (1–6 pakketten) | 10 % van opgegeven (90 %) | 6.000 · 80 % ¹ | 10 jaar ² |
| Venus E 4.0 | 5,024 kWh | 0,60 kWh (88 %) | 10.000 · 80 % ³ | 10 jaar ² |
| Venus E Max | 10,048 kWh | 1,00 kWh (90 %) | 10.000 · 80 % ³ | 10 jaar ² |
| Venus E Pro | 2,08 kWh per pakket (1–6 pakketten: basis plus 0–5 extra) | 10 % van opgegeven (90 %) | 10.000 · 80 % ³ | 10 jaar ² |
| Ander model | zelf invullen | zelf invullen | zelf invullen | zelf invullen |

¹ Marstek noemt voor de Venus D meer dan 10.000 cycli, maar geen capaciteitspercentage; de monitor gebruikt de voorzichtigere lijn van de Venus E.
² Niet genoemd voor dit model; controleer je eigen voorwaarden.
³ Marstek noemt meer dan 10.000 cycli (25 °C), maar geen capaciteitspercentage; de monitor gaat uit van 80 % na 10.000 cycli. De lijn is vlakker dan bij de oudere modellen.
⁴ Marstek noemt voor de Venus C meer dan 6.000 cycli, maar geen capaciteitspercentage; de monitor gebruikt dezelfde lijn als bij de Venus E.

De Venus C is een halve Venus E (2,56 kWh) met dezelfde Modbus-registers als de Venus E v1/v2. Hij kan zich ook met dezelfde modelcode melden (HMG). Kies bij het toevoegen dus zelf *Venus C*, ook als *Venus E v1 / v2* al is aangevinkt. Is toch de Venus E gekozen, dan komt de meting uit op ongeveer de helft. De kaart toont dan *Klopt het model?* in plaats van rood, en onder Reparaties staat hoe je het aanpast.

De Venus E Mini staat niet in de lijst: die koppelt alleen via Bluetooth en wifi, dus er is geen lokale sensor voor het DC-vermogen. Heb je laadtoestand en DC-vermogen wel lokaal, kies dan *Ander model*. De Venus D AC-versie volgt zodra de specificaties duidelijk zijn. Venus E v1 en v2 blijven één keuze: zelfde firmware, registers en modelcode.

De Venus A heeft nog geen vooraf ingevulde waarden: er is geen openbare capaciteit gevonden. Kies *Ander model* en vul de fabrieksgegevens zelf in.

## Ontlaaddiepte per model

**De band is niet bij elk model gelijk.** Je stelt hem per batterij in via de interne reserve (opgegeven capaciteit × (100 % − ontlaaddiepte)):

| Model | Ontlaaddiepte | Reserve bij 5,12 kWh | Bron |
|---|---|---|---|
| Venus E v1 / v2 | 90 % volgens de datasheet; in de praktijk stoppen sommige exemplaren rond 11–12 %, dus 88 % | 0,51 kWh (of 0,61 kWh bij 88 %) | Datasheet Venus E / eigen meting |
| Venus E v3 | 90 % | 0,51 kWh | Handleiding Venus E 3.0 |
| Venus C (2,56 kWh) | 90 % volgens een verkoper; Marstek noemt het niet; in de praktijk stopt hij soms rond 11 % | 0,26 kWh (of 0,28 kWh als hij rond 11 % stopt) | Productpagina verkoper (sun.store) / gebruiker |
| Venus D (2,56 kWh) | Niet als specificatie vermeld; Marstek rekent op de productpagina met 90 % | 0,26 kWh | Productpagina Venus D |
| Venus E 4.0 (5,024 kWh) | 88 % | 0,60 kWh | Brochure Venus E 4.0 |
| Venus E Max (10,048 kWh) | 90 % | 1,00 kWh | Brochure Venus E Max |
| Venus E Pro (2,08 kWh per pakket) | 90 % | 0,21 kWh per pakket | Brochure Venus E Pro |

Tip: kijk bij een volledige ontlading tot welk percentage jouw batterij zakt. Stopt hij rond 10 %, gebruik dan 90 %; stopt hij rond 12 %, gebruik dan 88 %. Een Venus C die rond 11 % stopt (er blijft dan ongeveer 0,28 kWh in), vul je in met een reserve van 0,28 kWh. Kijk wel of de ontlaadgrens in de Marstek-app op het laagste staat; anders meet je je eigen instelling en niet de reserve van de batterij. Dit verandert alleen de **kWh** (bruikbaar en gemeten), niet het **percentage nog beschikbaar**: dat volgt uit de opgegeven capaciteit. Een percentage boven 100 % los je hier dus niet mee op; zie [Problemen oplossen](04-troubleshooting.nl.md).

## Bronnen voor de specificaties van de fabrikant

Geraadpleegd op 20-10-2026 (nieuwe modellen op 22-10-2026). Waar bronnen elkaar tegenspreken, gebruikt de tool de voorzichtigste waarde; je kunt alles zelf aanpassen.

| Gegeven | Waarde | Bron |
|---|---|---|
| Capaciteitsbehoud na cycli | 80 % na meer dan 6.000 cycli | [Marstek – Venus E Gen 3.0 (Engels)](https://marstekenergy.com/en-us/products/marstek-venus-e-gen-3) |
| Idem, andere taalversie | 80 % na meer dan 10.000 cycli (tool gebruikt 6.000) | [Marstek – Venus E Gen 3.0 (Nederlands)](https://marstekenergy.com/nl-nl/products/marstek-venus-e-gen-3) |
| Opgegeven capaciteit Venus E, cycli, garantie | 5.120 Wh · meer dan 6.000 cycli · 10 jaar garantie | [Marstek – Venus C/E](https://marstekenergy.com/en-us/pages/marstek-venus-c-e) |
| Ontlaaddiepte Venus E 3.0 | 90 % · 5.120 Wh · meer dan 6.000 cycli (25 °C) | [Marstek – Download Center, gebruikershandleiding Venus E 3.0](https://marstekenergy.com/en-us/pages/download-center) |
| Ontlaaddiepte Venus E (eerdere uitvoering) | 90 % · 5.120 Wh · meer dan 6.000 cycli (25 °C) | Specificatieblad Venus E "plug-in battery", zoals verspreid door verkopers (geen openbare link bij Marstek) |
| Venus C | 2.560 Wh (51,2 V, LiFePO4 16S) · meer dan 6.000 cycli · 10 jaar garantie · RS485 | [Marstek – Venus C/E](https://marstekenergy.com/en-us/pages/marstek-venus-c-e), [Marstek.de – Venus C](https://marstek.de/en/products/venus-c) |
| Ontlaaddiepte Venus C | 90 % | [sun.store – Venus C](https://sun.store/en/product/marstek-venus-c-47353) |
| Registers Venus C | zelfde generatie als Venus E en Venus E Gen 2.0 | [evcc – Marstek Venus C](https://docs.evcc.io/en/meters/marstek-venus-c) |
| Venus D | 2,56 kWh per unit · meer dan 10.000 cycli · rekenvoorbeelden met 90 % ontlaaddiepte | [Marstek – Venus D](https://marstekenergy.com/en-us/products/marstek-venus-d-ac-version) |
| Venus E 4.0 | 5.024 Wh (314 Ah, 16 V) · 88 % ontlaaddiepte · meer dan 10.000 cycli (25 °C) | [Marstek – brochure Venus E 4.0 (pdf)](https://cdn.shopify.com/s/files/1/0746/1575/0952/files/MARSTEK_VENUS-4.0.pdf) |
| Venus E Max | 10.048 Wh (314 Ah, 32 V) · 90 % ontlaaddiepte · meer dan 10.000 cycli (25 °C) | [Marstek – brochure Venus E Max (pdf)](https://cdn.shopify.com/s/files/1/0746/1575/0952/files/VENUS_E_MAX.pdf) |
| Venus E Pro | 2.080 Wh per pakket (41,6 V), basis plus maximaal 5 extra pakketten · 90 % ontlaaddiepte · meer dan 10.000 cycli (25 °C) · LAN met Modbus | [Marstek – brochure Venus E Pro (pdf)](https://cdn.shopify.com/s/files/1/0746/1575/0952/files/VENUS_E_Pro_EU_EN.pdf), [productpagina](https://marstekenergy.com/de-de/products/venus-e-pro) |
| Garantie | Materiaal- en fabricagefouten; geen capaciteitspercentage; normale slijtage en aansluiting op hardware/software van derden uitgesloten | [Marstek – Garantiebeleid](https://marstekenergy.com/nl-nl/pages/warranty) |

Controleer je eigen voorwaarden. Je past de waarden aan via **Instellingen → Apparaten en diensten → Marstek Capacity Monitor → Configureren**.
