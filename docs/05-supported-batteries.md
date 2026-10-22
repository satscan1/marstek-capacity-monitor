# Supported batteries

*[Nederlands](05-supported-batteries.nl.md)*

| Marstek | Usually connected via | State of charge | DC power |
|---|---|---|---|
| Venus E v1 / v2 | RS485, through ESPHome (LilyGo, M5Stack) or an RS485 network bridge (Elfin EW11) with a Modbus integration | register 32104 | register 32102 |
| Venus E v3, Venus A, Venus D | Built-in LAN port with Modbus TCP | register 34002 | register 30001 |

**Modbus is not required.** Any connection works as long as it provides the state of charge and the **DC** battery power as Home Assistant sensors: ESPHome, Modbus (RS485 or LAN) or another integration. The table lists the verified models and Modbus routes; only the registers differ, the data is the same.

**MQTT (hm2mqtt):** tested with a simulated Venus E v1/v2: the scan finds *Battery State of Charge* and *Battery Power*, and both signs work. Not yet confirmed with a real battery; whether older v1/v2 firmware sends *Battery Power* is unknown. For the cell balance check with hm2mqtt: turn on *Cell Data* in hm2mqtt and enable the entities *Max Cell Voltage* and *Min Cell Voltage* in Home Assistant (they are off by default). Experiences are welcome via Issues.

**Cell temperatures:** some connections (including MQTT on the v1/v2) report MOSFET temperatures as "cell temperature". This tool only uses real cell temperatures (optional, as context per measurement), never MOS temperatures; the scan skips sensors with MOS, board or internal in the name. For the cell balance check it uses the highest and lowest cell **voltage**.

Integrations such as [marstek_venus_modbus](https://github.com/ViperRNMC/marstek_venus_modbus) and [Omnibattery](https://github.com/ffunes/Omnibattery), as well as the common ESPHome configs, provide both sensors.

**Not supported:** connections that only provide AC power, which includes most cloud connections. AC values include conversion losses and would give a wrong capacity. If you pick a sensor that looks like AC, you get a warning.

## Factory data per model

When adding a battery you pick the model; these values are filled in. You can change them later under **Configure**.

| Model | Rated capacity | Reserve (DoD) | Cycles · capacity after | Warranty period |
|---|---|---|---|---|
| Venus E v1 / v2 | 5.12 kWh | 0.51 kWh (90 %) | 6,000 · 80 % | 10 years |
| Venus E v3 | 5.12 kWh | 0.51 kWh (90 %) | 6,000 · 80 % | 10 years |
| Venus D | 2.56 kWh per pack (1–6 packs) | 10 % of rated (90 %) | 6,000 · 80 % ¹ | 10 years ² |
| Venus E 4.0 | 5.024 kWh | 0.60 kWh (88 %) | 10,000 · 80 % ³ | 10 years ² |
| Venus E Max | 10.048 kWh | 1.00 kWh (90 %) | 10,000 · 80 % ³ | 10 years ² |
| Venus E Pro | 2.08 kWh per pack (1–6 packs: base unit plus 0–5 extra) | 10 % of rated (90 %) | 10,000 · 80 % ³ | 10 years ² |
| Other model | enter yourself | enter yourself | enter yourself | enter yourself |

¹ Marstek lists more than 10,000 cycles for the Venus D but no capacity percentage; the monitor uses the more cautious Venus E line.
² Not listed for this model; check your own terms.
³ Marstek lists more than 10,000 cycles (25 °C) but no capacity percentage; the monitor assumes 80 % after 10,000 cycles. The line is flatter than that of the older models.

The Venus E Mini is not in the list: it only connects via Bluetooth and Wi-Fi, so there is no local DC power sensor. If you do have state of charge and DC power locally, choose *Other model*. The Venus D AC version follows once its specs are clear. Venus E v1 and v2 stay one choice: same firmware, registers and model code.

The Venus A has no preset yet: no public capacity figure was found. Choose *Other model* and enter its factory data.

## Depth of discharge per model

**The band is not the same for every model.** You set it per battery through the internal reserve (rated capacity × (100 % − depth of discharge)):

| Model | Depth of discharge | Reserve at 5.12 kWh | Source |
|---|---|---|---|
| Venus E v1 / v2 | 90 % per datasheet; in practice some units stop around 11–12 %, i.e. 88 % | 0.51 kWh (or 0.61 kWh at 88 %) | Venus E datasheet / own measurement |
| Venus E v3 | 90 % | 0.51 kWh | Venus E 3.0 manual |
| Venus D (2.56 kWh) | Not listed as a spec; Marstek's product page calculates with 90 % | 0.26 kWh | Venus D product page |
| Venus E 4.0 (5.024 kWh) | 88 % | 0.60 kWh | Venus E 4.0 brochure |
| Venus E Max (10.048 kWh) | 90 % | 1.00 kWh | Venus E Max brochure |
| Venus E Pro (2.08 kWh per pack) | 90 % | 0.21 kWh per pack | Venus E Pro brochure |

Tip: check down to which percentage your battery goes during a full discharge. If it stops around 10 %, use 90 %; if it stops around 12 %, use 88 %.

## Sources for the manufacturer specs

Checked on 20 October 2026 (new models on 22 October 2026). Where sources disagree, the monitor uses the most cautious value; you can change everything yourself.

| Item | Value | Source |
|---|---|---|
| Capacity retention after cycles | 80 % after more than 6,000 cycles | [Marstek – Venus E Gen 3.0 (English)](https://marstekenergy.com/en-us/products/marstek-venus-e-gen-3) |
| Same, other language version | 80 % after more than 10,000 cycles (monitor uses 6,000) | [Marstek – Venus E Gen 3.0 (Dutch)](https://marstekenergy.com/nl-nl/products/marstek-venus-e-gen-3) |
| Rated capacity Venus E, cycles, warranty | 5,120 Wh · more than 6,000 cycles · 10-year warranty | [Marstek – Venus C/E](https://marstekenergy.com/en-us/pages/marstek-venus-c-e) |
| Depth of discharge Venus E 3.0 | 90 % · 5,120 Wh · more than 6,000 cycles (25 °C) | [Marstek – Download Center, Venus E 3.0 user manual](https://marstekenergy.com/en-us/pages/download-center) |
| Depth of discharge Venus E (earlier version) | 90 % · 5,120 Wh · more than 6,000 cycles (25 °C) | Venus E "plug-in battery" spec sheet as distributed by resellers (no public link at Marstek) |
| Venus D | 2.56 kWh per unit · more than 10,000 cycles · examples calculated with 90 % DoD | [Marstek – Venus D](https://marstekenergy.com/en-us/products/marstek-venus-d-ac-version) |
| Venus E 4.0 | 5,024 Wh (314 Ah, 16 V) · 88 % DoD · more than 10,000 cycles (25 °C) | [Marstek – Venus E 4.0 brochure (PDF)](https://cdn.shopify.com/s/files/1/0746/1575/0952/files/MARSTEK_VENUS-4.0.pdf) |
| Venus E Max | 10,048 Wh (314 Ah, 32 V) · 90 % DoD · more than 10,000 cycles (25 °C) | [Marstek – Venus E Max brochure (PDF)](https://cdn.shopify.com/s/files/1/0746/1575/0952/files/VENUS_E_MAX.pdf) |
| Venus E Pro | 2,080 Wh per pack (41.6 V), base unit plus up to 5 extra packs · 90 % DoD · more than 10,000 cycles (25 °C) · LAN with Modbus | [Marstek – Venus E Pro brochure (PDF)](https://cdn.shopify.com/s/files/1/0746/1575/0952/files/VENUS_E_Pro_EU_EN.pdf), [product page](https://marstekenergy.com/de-de/products/venus-e-pro) |
| Warranty | Material and manufacturing defects; no capacity percentage; normal wear and use with third-party hardware/software excluded | [Marstek – Warranty policy](https://marstekenergy.com/en-us/pages/warranty) |

Check your own terms. You can change the values under **Settings → Devices & services → Marstek Capacity Monitor → Configure**.
