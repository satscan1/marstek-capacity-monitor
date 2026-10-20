# Supported batteries

*[Nederlands](05-supported-batteries.nl.md)*

| Marstek | Usually connected via | State of charge | DC power |
|---|---|---|---|
| Venus E v1 / v2 | RS485, through ESPHome (LilyGo, M5Stack) or an RS485 network bridge (Elfin EW11) with a Modbus integration | register 32104 | register 32102 |
| Venus E v3, Venus A, Venus D | Built-in LAN port with Modbus TCP | register 34002 | register 30001 |

**Any Marstek model with Modbus works**, over RS485 or LAN, as long as a Home Assistant integration provides the state of charge and the DC power as sensors. The table lists the verified models; only the registers differ, the data is the same. For another model, enter its own factory data when adding it (capacity, depth of discharge, cycles); the defaults are those of the Venus E 5.12 kWh.

Integrations such as [marstek_venus_modbus](https://github.com/ViperRNMC/marstek_venus_modbus) and [Omnibattery](https://github.com/ffunes/Omnibattery), as well as the common ESPHome configs, provide both sensors.

**Not supported:** connections that only provide AC power, which includes most cloud connections. AC values include conversion losses and would give a wrong capacity. If you pick a sensor that looks like AC, you get a warning.

## Depth of discharge per model

**The band is not the same for every model.** You set it per battery through the internal reserve (rated capacity × (100 % − depth of discharge)):

| Model | Depth of discharge | Reserve at 5.12 kWh | Source |
|---|---|---|---|
| Venus E v1 / v2 | 90 % per datasheet; in practice some units stop around 11–12 %, i.e. 88 % | 0.51 kWh (or 0.61 kWh at 88 %) | Venus E datasheet / own measurement |
| Venus E v3 | 90 % | 0.51 kWh | Venus E 3.0 manual |
| Venus D (2.56 kWh) | Not listed as a spec; Marstek's product page calculates with 90 % | 0.26 kWh | Venus D product page |

Tip: check down to which percentage your battery goes during a full discharge. If it stops around 10 %, use 90 %; if it stops around 12 %, use 88 %.

## Sources for the manufacturer specs

Checked on 20 October 2026. Where sources disagree, the monitor uses the most cautious value; you can change everything yourself.

| Item | Value | Source |
|---|---|---|
| Capacity retention after cycles | 80 % after more than 6,000 cycles | [Marstek – Venus E Gen 3.0 (English)](https://marstekenergy.com/en-us/products/marstek-venus-e-gen-3) |
| Same, other language version | 80 % after more than 10,000 cycles (monitor uses 6,000) | [Marstek – Venus E Gen 3.0 (Dutch)](https://marstekenergy.com/nl-nl/products/marstek-venus-e-gen-3) |
| Rated capacity Venus E, cycles, warranty | 5,120 Wh · more than 6,000 cycles · 10-year warranty | [Marstek – Venus C/E](https://marstekenergy.com/en-us/pages/marstek-venus-c-e) |
| Depth of discharge Venus E 3.0 | 90 % · 5,120 Wh · more than 6,000 cycles (25 °C) | [Marstek – Download Center, Venus E 3.0 user manual](https://marstekenergy.com/en-us/pages/download-center) |
| Depth of discharge Venus E (earlier version) | 90 % · 5,120 Wh · more than 6,000 cycles (25 °C) | Venus E "plug-in battery" spec sheet as distributed by resellers (no public link at Marstek) |
| Venus D | 2.56 kWh per unit · more than 10,000 cycles · examples calculated with 90 % DoD | [Marstek – Venus D](https://marstekenergy.com/en-us/products/marstek-venus-d-ac-version) |
| Warranty | Material and manufacturing defects; no capacity percentage; normal wear and use with third-party hardware/software excluded | [Marstek – Warranty policy](https://marstekenergy.com/en-us/pages/warranty) |

Check your own terms. You can change the values under **Settings → Devices & services → Marstek Capacity Monitor → Configure**.
