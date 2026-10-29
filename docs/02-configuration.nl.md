# Instellingen

*[English](02-configuration.md)*

Alle waarden stel je in bij het toevoegen van een batterij. Later wijzigen kan via **Instellingen → Apparaten en diensten → Marstek Capacity Monitor → Configureren**.

**Andere sensor nodig?** Kies bij Configureren **Sensoren wisselen** (vanaf 0.5.5). De scan stelt de sensoren voor die hij vindt, met hun waarde van nu; of kies ze zelf. Je metingen blijven bij de batterij. Waren ze met een verkeerde sensor gemaakt, zet dan **Opnieuw beginnen met meten** aan.

| Instelling | Standaard | Betekenis |
|---|---|---|
| Opgegeven capaciteit | 5,12 kWh | Totaal in de cellen volgens de fabrikant |
| Interne reserve | 0,51 kWh | Deel dat de batterij nooit afgeeft; opgegeven capaciteit × (100 % − ontlaaddiepte). 0,51 = 90 %, 0,61 = 88 % |
| Model | – | Venus E v1/v2, Venus E v3, Venus E 4.0, Venus E Max, Venus E Pro, Venus C, Venus D of ander model. Een Venus C kan zich melden als Venus E v1/v2: kies dan zelf Venus C. Vult bij het toevoegen de fabrieksgegevens in; zie [Ondersteunde batterijen](05-supported-batteries.nl.md#fabrieksgegevens-per-model) |
| Installatiedatum | – | Voor de leeftijd en het einde van de garantietermijn |
| Garantietermijn | 10 jaar | Alleen ter informatie op de kaart |
| Opgegeven aantal cycli | 6.000 | Specificatie fabrikant |
| Capaciteit na die cycli | 80 % | Specificatie fabrikant; samen met het aantal cycli de specificatielijn |
| Cycli vóór de monitoring | 0 | Voor een batterij die al in gebruik was: totaal ontladen kWh ÷ bruikbare capaciteit. Heeft de batterij een teller *totaal ontladen* (Modbus, ESPHome), dan vult de monitor dit zelf in. Die teller meet aan de AC-kant: een schatting, minder precies dan de cycli die de monitor zelf aan de DC-kant telt. Zie [Extra sensoren gevonden](#extra-sensoren-gevonden) |
| Rode grens | 75 % | Op of onder dit percentage: melden via de Marstek-app |
| Marge onder specificatie | 5 punten | Zolang de meting hooguit zoveel onder de specificatie zit, blijft de status groen |
| Teken van de vermogensensor | Automatisch | Alleen aanpassen als de automatische herkenning het mis heeft |
| Hoogste / laagste celtemperatuur | leeg | Optioneel, experimenteel. Wordt bij elke meting bewaard als context (een koude batterij geeft minder af). Alleen celtemperaturen, nooit MOS- of printplaattemperaturen |
| Hoogste / laagste celspanning | leeg | Optioneel, voor de celbalans. Vul beide in of geen van beide. Alleen cel**spanningen**: sommige koppelingen geven MOSFET-temperaturen door als "celtemperatuur" |
| Gevoeligheid SOC-drift / celkalibratie | Normaal | Uit (alleen op de kaart), Ruim (SOC 8 %, cellen 3× normaal), Normaal (5 %, 2×) of Extra (3 %, 1,5×). Zie [Hoe het werkt](03-how-it-works.nl.md#seintjes-en-wegklikken-vanaf-05) |
| Seintjes | aan | Bericht op je telefoon en onder Reparaties bij SOC-drift of celkalibratie, alleen bij een patroon. Uit = geen berichten; de kaart laat het wel zien. Zie [Hoe het werkt](03-how-it-works.nl.md#seintjes-en-wegklikken-vanaf-05) |
| Menu-item in de zijbalk | aan | Vanaf 0.5.1: **Batterijcapaciteit** in de zijbalk, met al je batterijen. Geldt voor het hele menu-item: uit bij één batterij = geen menu-item. Zie [Installatie](01-installation.nl.md#vanzelf-in-de-zijbalk-vanaf-051) |

## Sensoren

| Entiteit | Wat |
|---|---|
| `sensor.marstek_mt1_measured_capacity` | Gemeten capaciteit (kWh). Attributen: `trend` (per maand, nieuw → oud) en `history` (laatste 10 volledige ontladingen), allebei met `temp_c` als er celtemperatuur-sensoren zijn ingesteld |
| `sensor.marstek_mt1_capacity_pct` | Nog beschikbaar: gemeten capaciteit als % van nieuw |
| `sensor.marstek_mt1_expected_capacity` | Specificatie fabrikant (%) bij het huidige aantal cycli. Attributen: `cycles`, `initial_cycles` (cycli vóór de monitoring), `cycle_counter` (de teller waar die vandaan komt, leeg = zelf ingevuld) |
| `sensor.marstek_mt1_margin` | Marge ten opzichte van de specificatie (kWh) |
| `sensor.marstek_mt1_cycles` | Aantal volle cycli |
| `sensor.marstek_mt1_warranty_status` | Status beschikbare capaciteit: `good` / `attention` / `critical` / `no_measurement` |
| `sensor.marstek_mt1_monitor_status` | Werkt de meting zelf: `measuring` (meet) / `collecting` (verzamelt data) / `no_recent_data` (geen recente data) / `sensor_missing` (sensor niet beschikbaar). Attributen: `phase` (volgende stap naar een meting), `soc`, `full_discharges`, `power_sign` |
| `sensor.marstek_mt1_cell_spread` | Alleen met celsensoren: verschil tussen hoogste en laagste cel na de laatste volle lading (mV). Attributen: `trend` (mediaan per maand, nieuw → oud) en `history` |
| `sensor.marstek_mt1_soc_health` | SOC-drift: `ok` / `letop` / `advies`. Attributen: `count` (voorvallen in 45 dagen), `since`, `last_size` (%), `last_calibration` (laatst helemaal vol), `dismissed` (weggeklikt), `notify`, `trend` (per maand: `full_days`, `dev`, `b99`, `jump`, `hang`, `no_full_days`) |
| `sensor.marstek_mt1_cell_health` | Alleen met celsensoren: celkalibratie `ok` / `letop` / `advies`. Attributen: `count`, `since`, `base_mv` (normaal, eerste 3 maanden), `limit_mv` (2× normaal), `last_mv`, `dismissed`, `notify`, `trend` (per maand: `spread_mv`, `n`, `rest_h`, `temp_c`) |
| `sensor.marstek_mt1_last_full_discharge` · `_last_full_charge` | Datum en tijd van de laatste volledige ontlading (≥ 95 % → ≤ 15 %) en volledige lading (≤ 15 % → ≥ 95 %) |
| `sensor.marstek_mt1_nominal_capacity` · `_usable_capacity` · `_red_threshold` · `_warranty_end` · `_dc_discharged` | Diagnostiek. `_dc_discharged` toont ook welke sensoren gebruikt worden en hoe het teken is herkend |

Na elke vastgelegde beurt verstuurt de integratie het event `marstek_capacity_monitor_session`. Daarmee kun je de records zelf doorsturen, bijvoorbeeld naar InfluxDB.

Verandert de stand van SOC-drift of celkalibratie, dan verstuurt hij `marstek_capacity_monitor_advice` (`entry_id`, `name`, `battery`, `kind` = `soc` of `cells`, `level`, `count`, `size`). Handig voor een eigen melding, bijvoorbeeld op een speaker.

De schrijfbelasting blijft laag:

* de lijsten `trend` en `history` gaan niet naar de recorder-database;
* de sensoren veranderen alleen na een meting of één keer per uur.

## Extra sensoren gevonden

Staan er op het apparaat van een batterij sensoren die de monitor nog niet gebruikt, dan meldt hij dat onder **Instellingen → Reparaties** (*MT1: extra sensoren gevonden*). Dat gebeurt na het opstarten, dus ook na een update:

* **Celspanning hoogste en laagste**, als die nog niet zijn ingevuld. Daarmee volgt de monitor de celbalans.
* **Teller totaal ontladen**, als *Cycli vóór de monitoring* nog 0 is. De monitor rekent uit: (teller − wat hij zelf al heeft geteld) ÷ bruikbare capaciteit. Die teller meet aan de AC-kant, dus dit is een schatting, minder precies dan de cycli die de monitor zelf aan de DC-kant telt. Een waarde die je zelf hebt ingevuld wordt nooit overschreven.

Open de melding, vink aan wat je wilt toevoegen en kies **Verzenden**. Vink je iets niet aan, dan vraagt hij er niet meer om; later toevoegen kan altijd via **Configureren**. Bij een nieuwe batterij gebeurt dit meteen bij het toevoegen.

## Een melding wegklikken

De actie `marstek_capacity_monitor.dismiss_advice` met `battery` (bijv. `mt1`) en `kind` (`soc` of `cells`) doet hetzelfde als **Wegklikken** op de kaart: de melding verdwijnt overal en komt pas terug bij een nieuwe reeks.

## Metingen wissen

Gebruik de actie `marstek_capacity_monitor.reset_measurements` met de batterij als doel. Dit kan niet ongedaan worden gemaakt.

Verwijder je een batterij uit de integratie, dan blijven de metingen in `.storage/` staan. Ze kunnen helpen bij een melding aan Marstek.
