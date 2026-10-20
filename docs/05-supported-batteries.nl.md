# Ondersteunde batterijen

*[English](05-supported-batteries.md)*

| Marstek | Hoe hij meestal in HA zit | Laadtoestand | DC-vermogen |
|---|---|---|---|
| Venus E v1 / v2 | RS485 via ESPHome (LilyGo, M5Stack) of via een RS485-netwerkbrug (Elfin EW11) met een Modbus-integratie | register 32104 | register 32102 |
| Venus E v3, Venus A, Venus D | Ingebouwde LAN-poort met Modbus TCP | register 34002 | register 30001 |

**Elk Marstek-model met Modbus werkt**, via RS485 of via LAN, zolang een HA-koppeling de laadtoestand en het DC-vermogen als sensor levert. De tabel geeft de gecontroleerde modellen; alleen de registers verschillen, de gegevens zijn hetzelfde. Bij een ander model vul je bij het toevoegen de eigen fabrieksgegevens in (capaciteit, ontlaaddiepte, cycli); de standaardwaarden zijn die van de Venus E 5,12 kWh.

Integraties zoals [marstek_venus_modbus](https://github.com/ViperRNMC/marstek_venus_modbus) en [Omnibattery](https://github.com/ffunes/Omnibattery), en de gangbare ESPHome-configuraties, leveren beide sensoren.

**Niet ondersteund:** koppelingen die alleen het AC-vermogen leveren, zoals de meeste cloudkoppelingen. AC-waarden bevatten omzetverlies en geven daardoor een verkeerde capaciteit. Kies je toch een sensor die op AC lijkt, dan krijg je een waarschuwing.

## Ontlaaddiepte per model

**De band is niet bij elk model gelijk.** Je stelt hem per batterij in via de interne reserve (opgegeven capaciteit × (100 % − ontlaaddiepte)):

| Model | Ontlaaddiepte | Reserve bij 5,12 kWh | Bron |
|---|---|---|---|
| Venus E v1 / v2 | 90 % volgens de datasheet; in de praktijk stoppen sommige exemplaren rond 11–12 %, dus 88 % | 0,51 kWh (of 0,61 kWh bij 88 %) | Datasheet Venus E / eigen meting |
| Venus E v3 | 90 % | 0,51 kWh | Handleiding Venus E 3.0 |
| Venus D (2,56 kWh) | Niet als specificatie vermeld; Marstek rekent op de productpagina met 90 % | 0,26 kWh | Productpagina Venus D |

Tip: kijk bij een volledige ontlading tot welk percentage jouw batterij zakt. Stopt hij rond 10 %, gebruik dan 90 %; stopt hij rond 12 %, gebruik dan 88 %.

## Bronnen voor de specificaties van de fabrikant

Geraadpleegd op 20-10-2026. Waar bronnen elkaar tegenspreken, gebruikt de tool de voorzichtigste waarde; je kunt alles zelf aanpassen.

| Gegeven | Waarde | Bron |
|---|---|---|
| Capaciteitsbehoud na cycli | 80 % na meer dan 6.000 cycli | [Marstek – Venus E Gen 3.0 (Engels)](https://marstekenergy.com/en-us/products/marstek-venus-e-gen-3) |
| Idem, andere taalversie | 80 % na meer dan 10.000 cycli (tool gebruikt 6.000) | [Marstek – Venus E Gen 3.0 (Nederlands)](https://marstekenergy.com/nl-nl/products/marstek-venus-e-gen-3) |
| Opgegeven capaciteit Venus E, cycli, garantie | 5.120 Wh · meer dan 6.000 cycli · 10 jaar garantie | [Marstek – Venus C/E](https://marstekenergy.com/en-us/pages/marstek-venus-c-e) |
| Ontlaaddiepte Venus E 3.0 | 90 % · 5.120 Wh · meer dan 6.000 cycli (25 °C) | [Marstek – Download Center, gebruikershandleiding Venus E 3.0](https://marstekenergy.com/en-us/pages/download-center) |
| Ontlaaddiepte Venus E (eerdere uitvoering) | 90 % · 5.120 Wh · meer dan 6.000 cycli (25 °C) | Specificatieblad Venus E "plug-in battery", zoals verspreid door verkopers (geen openbare link bij Marstek) |
| Venus D | 2,56 kWh per unit · meer dan 10.000 cycli · rekenvoorbeelden met 90 % ontlaaddiepte | [Marstek – Venus D](https://marstekenergy.com/en-us/products/marstek-venus-d-ac-version) |
| Garantie | Materiaal- en fabricagefouten; geen capaciteitspercentage; normale slijtage en aansluiting op hardware/software van derden uitgesloten | [Marstek – Garantiebeleid](https://marstekenergy.com/nl-nl/pages/warranty) |

Controleer je eigen voorwaarden. Je past de waarden aan via **Instellingen → Apparaten & diensten → Marstek Capacity Monitor → Configureren**.
