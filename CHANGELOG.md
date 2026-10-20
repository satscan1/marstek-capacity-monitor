# Changelog

## v0.2.1 — 2026-10-20

**Cleaner battery scan and the date of the last full discharge and full charge.**

Adding a battery
- The scan no longer proposes car batteries (e.g. BYD, Tesla, EV), phones or tablets.
- The scan no longer proposes sum sensors such as "house total" or "all batteries".

Measuring
- New: `sensor.marstek_<id>_last_full_discharge` and `sensor.marstek_<id>_last_full_charge` (date and time).

Dashboard
- button-card detail card: the footer shows the last full discharge and full charge.

Upgrade: install v0.2.1 over v0.2.0 and restart Home Assistant. Existing measurements are kept; the two dates fill in from the measurements already stored.

## v0.2.0 — 2026-10-20

**First release: measured DC capacity of up to six Marstek batteries, compared with the manufacturer spec.**

Measuring
- Measures the usable capacity on every full discharge (≥ 95 % → ≤ 15 %) on the battery (DC) side; the value shown is the median of the last 3.
- Rated, usable and measured capacity are kept apart; the usable band (depth of discharge) is set per battery.
- Measurements are stored in Home Assistant itself (`.storage`); no InfluxDB needed.
- A gap of more than 5 minutes in the power data invalidates that swing.

Manufacturer spec and status
- The measurement is compared with the manufacturer spec per cycle (default 80 % after 6,000 cycles; not a warranty).
- `sensor.marstek_<id>_warranty_status`: good · below spec · report to Marstek (75 % or lower, via the Marstek app).

Adding a battery
- Scans Home Assistant for existing state-of-charge and DC power sensors and proposes each battery.
- Warns when a power sensor looks like the AC / grid side.
- Detects automatically whether the power sensor shows charging as positive or negative.
- Fixed: an abandoned attempt to add a battery no longer blocks a new one.

Dashboard
- button-card: overview of up to 6 batteries (trend column first, newest → oldest) and a detail card per battery, in English and Dutch.
- Standard cards that need no extra installation.

Upgrade from an earlier test version: remove the old `custom_components/marstek_capacity_monitor` folder, install v0.2.0, then restart Home Assistant.
