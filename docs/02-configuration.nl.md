# Instellingen

*[English](02-configuration.md)*

Alle waarden stel je in bij het toevoegen van een batterij. Later wijzigen kan via **Instellingen → Apparaten & diensten → Marstek Capacity Monitor → Configureren**.

| Instelling | Standaard | Betekenis |
|---|---|---|
| Opgegeven capaciteit | 5,12 kWh | Totaal in de cellen volgens de fabrikant |
| Interne reserve | 0,51 kWh | Deel dat de batterij nooit afgeeft; opgegeven capaciteit × (100 % − ontlaaddiepte). 0,51 = 90 %, 0,61 = 88 % |
| Model | – | Venus E v1/v2, Venus E v3, Venus D of ander model. Vult bij het toevoegen de fabrieksgegevens in; zie [Ondersteunde batterijen](05-supported-batteries.nl.md#fabrieksgegevens-per-model) |
| Installatiedatum | – | Voor de leeftijd en het einde van de garantietermijn |
| Garantietermijn | 10 jaar | Alleen ter informatie op de kaart |
| Opgegeven aantal cycli | 6.000 | Specificatie fabrikant |
| Capaciteit na die cycli | 80 % | Specificatie fabrikant; samen met het aantal cycli de specificatielijn |
| Cycli vóór de monitoring | 0 | Schatting voor een batterij die al in gebruik was: totaal ontladen kWh ÷ bruikbare capaciteit |
| Rode grens | 75 % | Op of onder dit percentage: melden via de Marstek-app |
| Marge onder specificatie | 5 punten | Zolang de meting hooguit zoveel onder de specificatie zit, blijft de status groen |
| Teken van de vermogensensor | Automatisch | Alleen aanpassen als de automatische herkenning het mis heeft |
| Hoogste / laagste celtemperatuur | leeg | Optioneel, experimenteel. Wordt bij elke meting bewaard als context (een koude batterij geeft minder af). Alleen celtemperaturen, nooit MOS- of printplaattemperaturen |
| Hoogste / laagste celspanning | leeg | Optioneel, voor de celbalans. Vul beide in of geen van beide. Alleen cel**spanningen**: sommige koppelingen geven MOSFET-temperaturen door als "celtemperatuur" |

## Sensoren

| Entiteit | Wat |
|---|---|
| `sensor.marstek_mt1_measured_capacity` | Gemeten capaciteit (kWh). Attributen: `trend` (per maand, nieuw → oud) en `history` (laatste 10 volledige ontladingen), allebei met `temp_c` als er celtemperatuur-sensoren zijn ingesteld |
| `sensor.marstek_mt1_capacity_pct` | Nog beschikbaar: gemeten capaciteit als % van nieuw |
| `sensor.marstek_mt1_expected_capacity` | Specificatie fabrikant (%) bij het huidige aantal cycli |
| `sensor.marstek_mt1_margin` | Marge ten opzichte van de specificatie (kWh) |
| `sensor.marstek_mt1_cycles` | Aantal volle cycli |
| `sensor.marstek_mt1_warranty_status` | Status beschikbare capaciteit: `good` / `attention` / `critical` / `no_measurement` |
| `sensor.marstek_mt1_monitor_status` | Werkt de meting zelf: `measuring` (meet) / `collecting` (verzamelt data) / `no_recent_data` (geen recente data) / `sensor_missing` (sensor niet beschikbaar). Attributen: `phase` (volgende stap naar een meting), `soc`, `full_discharges`, `power_sign` |
| `sensor.marstek_mt1_cell_spread` | Alleen met celsensoren: verschil tussen hoogste en laagste cel na de laatste volle lading (mV). Attributen: `trend` (mediaan per maand, nieuw → oud) en `history` |
| `sensor.marstek_mt1_last_full_discharge` · `_last_full_charge` | Datum en tijd van de laatste volledige ontlading (≥ 95 % → ≤ 15 %) en volledige lading (≤ 15 % → ≥ 95 %) |
| `sensor.marstek_mt1_nominal_capacity` · `_usable_capacity` · `_red_threshold` · `_warranty_end` · `_dc_discharged` | Diagnostiek. `_dc_discharged` toont ook welke sensoren gebruikt worden en hoe het teken is herkend |

Na elke vastgelegde beurt verstuurt de integratie het event `marstek_capacity_monitor_session`. Daarmee kun je de records zelf doorsturen, bijvoorbeeld naar InfluxDB.

De schrijfbelasting blijft laag:

* de lijsten `trend` en `history` gaan niet naar de recorder-database;
* de sensoren veranderen alleen na een meting of één keer per uur.

## Metingen wissen

Gebruik de actie `marstek_capacity_monitor.reset_measurements` met de batterij als doel. Dit kan niet ongedaan worden gemaakt.

Verwijder je een batterij uit de integratie, dan blijven de metingen in `.storage/` staan. Ze kunnen helpen bij een melding aan Marstek.
