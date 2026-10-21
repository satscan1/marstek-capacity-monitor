# Changelog

## v0.4.0 — 2026-10-21

**Plug & play cards: no button-card, a dashboard in one click, and a first measurement from history.**

- New: the integration brings its own cards, **Marstek capacity (battery)** and **Marstek capacity (overview)**. After restarting Home Assistant (with at least one battery added) they are in the card picker; no button-card, no templates, no resources. They find your batteries, their names and the Home Assistant language by themselves, and look the same as the button-card cards.
- New: **dashboard in one click**: Settings → Dashboards → Add dashboard → *Marstek battery capacity* (Home Assistant 2026.5 and later). It arranges 1 to 6 batteries by itself and picks up new batteries. Older versions: two lines in the raw configuration editor (see the installation guide).
- New: when you add a battery, the recorder history (usually 10 days) is checked for full discharges that already happened, so there can be a measurement right away.
- New: **German** (Deutsch): settings screens, cards, the one-click dashboard, ready-made dashboards (`dashboard/ready-made/de/`) and the guides [README.de.md](README.de.md), [01 – Installation](docs/01-installation.de.md) and [06 – Dashboard und Galerie](docs/06-dashboard-gallery.de.md). The cards follow the Home Assistant language; `lang: de` forces German.
- The chart always shows the most recent 3 years; the header says *recent 3 years of warranty*. The *full warranty* choice is gone (it read as one phrase with *3 years* and added little while a battery is still young). Applies to the button-card templates too: paste the new `marstek_capacity_templates.yaml` again if you use them.
- The button-card templates and ready-made dashboards keep working.
- Home Assistant 2025.3 or newer is required (it already was in practice; now HACS says so too).

Upgrade: update in HACS, restart Home Assistant and refresh your browser (Ctrl+F5). Measurements and settings are unchanged.

## v0.3.2 — 2026-10-21

**Measurements survive a restart, ready-made dashboards and no false "no recent data" at night.**

- Fix: a battery standing still (empty or full, around 0 W) no longer shows *no recent data · check the connection*. Its state of charge and power simply do not change for hours. The status now only appears when the battery was charging or discharging (more than 50 W) and no new value came in for an hour. The minutes shown are now updated every hour.
- Fix: a Home Assistant restart in the middle of a full discharge no longer throws the measurement away. A restart of up to 10 minutes is bridged: the energy in that gap is estimated from the power just before and just after. Such a measurement is marked `bridged_s` (seconds bridged).
- Fix ([#1](https://github.com/satscan1/marstek-capacity-monitor/issues/1)): when the power sensor was briefly *unavailable* during a discharge, the energy of those minutes was silently missing and the measurement still counted, so the capacity came out too low. An outage of up to 5 minutes is now bridged the same way; a longer one makes the discharge not count. Thanks to @brauwers1981.
- New: ready-made dashboards for 1 to 6 batteries, in English and Dutch, in `dashboard/ready-made/`. Paste one into a new dashboard and you are done.
- Fix: *Reset measurements* (service `reset_measurements`) gave an error and did nothing.
- Installation guide: step by step how to add the cards, in a new or an existing dashboard.

Upgrade: update in HACS and restart Home Assistant. Measurements, settings and cards are unchanged.

## v0.3.1 — 2026-10-21

**Icon and automatic checks.**

- The integration now has its own icon, shown in Home Assistant 2026.3 and later.
- Every change on GitHub is checked automatically (HACS validation and hassfest).
- Preparation for the HACS default list.

Upgrade: update in HACS and restart Home Assistant. Measuring, settings and cards are unchanged.

## v0.3.0 — 2026-10-21

**Plug & play: pick your model and installation date. Plus a monitor status per battery, an optional cell balance check, cell temperature as context, a chart on the battery card and measurements kept for the whole 10-year warranty.**

Adding a battery
- New step: choose the model (Venus E v1/v2, Venus E v3, Venus D or other) and the installation date. For a known model the factory data are filled in; only "other" asks for them. The model is pre-selected when the device name or model gives it away.
- Venus D: asks for the number of packs (1–6) and calculates rated capacity and reserve from it.
- "Purchase date" is now called "Installation date".
- Optional: highest and lowest cell voltage. Filled in when the scan finds them on the same device.

Measuring
- New: `sensor.marstek_<id>_monitor_status` — measuring / collecting data / no recent data / sensor unavailable, with the next step towards a measurement (charge to ≥ 95 %, then discharge to ≤ 15 %). Only written when something changes, to keep the database load low.
- Measurements are kept for the whole warranty period: full discharges are no longer removed with the other swings (previously only the last 500 swings were kept, roughly 8 months). The monthly trend now covers 10 years instead of 12 months.
- New, experimental (with cell temperature sensors): the average cell temperature during every full discharge is stored with the measurement and shown per month, so a lower value in winter can be explained.
- New (with cell sensors): `sensor.marstek_<id>_cell_spread` — spread between the highest and lowest cell after a full charge, measured after 5 minutes at rest; one sample per full charge, monthly median. No colours yet: Marstek publishes no normal value.

Dashboard
- button-card battery card: a small "Chart" button under the status opens and closes a chart. It shows the last 3 years, or the whole warranty period with "full warranty"; subtle dots per month, the manufacturer spec as a dashed line, 75 % as a red line, and a short "How to read this?" text. Hover over a dot for the value and the cell temperature.
- button-card battery card: status line with the next step; "collecting data" instead of an empty measured value; cell spread section (trend column first, new → old).
- button-card overview card: "collecting data" in the Now column and a status symbol per battery (✓ ⏳ ⚠).
- Examples: `triggers_update` added to both cards, so they redraw when a battery changes.
- New: `layout-sections.yaml` — layout for 1 to 6 batteries in a Sections dashboard (three per row; the overview next to 1–2 batteries, two thirds wide above 3 or more).
- The cards accept a `demo` variable with fake data, used for the gallery. Nothing is written to Home Assistant.
- Standard battery card: monitor status row; cell spread as an optional row.

Documentation
- Modbus is not required: any connection with state of charge and DC power works. MQTT (hm2mqtt) tested with a simulated Venus E v1/v2, not yet with a real battery.
- Factory data per model, with sources.
- New: [06 – Dashboard and gallery](docs/06-dashboard-gallery.md): layout, the battery card explained with numbers, and screenshots for 1 to 6 batteries with and without chart.

Upgrade: install v0.3.0 over v0.2.1 and restart Home Assistant. Existing batteries and measurements are kept. Replace the three templates in your dashboard with the new `marstek_capacity_templates.yaml`. To use the cell balance check or cell temperature on an existing battery, fill in the sensors under **Configure**.

## v0.2.1 — 2026-10-20

**Cleaner battery scan and the date of the last full discharge and full charge.**

Adding a battery
- The scan no longer proposes car batteries (e.g. BYD, Tesla, EV), phones or tablets.
- The scan no longer proposes sum sensors such as "house total" or "all batteries".

Measuring
- New: `sensor.marstek_<id>_last_full_discharge` and `sensor.marstek_<id>_last_full_charge` (date and time).

Dashboard
- button-card detail card: the footer shows the last full discharge and full charge.
- button-card detail card: the warranty date line is removed from the footer (manufacturer spec is not a warranty); the explanation now also names orange.
- button-card overview card: compact columns instead of full width.
- Standard battery card: the warranty end row is removed.

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
