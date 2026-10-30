# Changelog

## v1.0.0 — 2026-10-30

**One layout. Every project. Facts, only facts matter.** Everything since v0.5.2 in one version. The test versions v0.5.5-dev1 to rc5 below show each step.

**Settings on the card.**

- The gear ⚙ on a battery card opens an own settings window: tabs **Standard** and **Experiment**, columns by subject (sensors · battery · messages and data), own fields (−/+, sliders, switches, choice buttons) and an ⓘ with the explanation for every setting. Only for an administrator; the settings screen of Home Assistant stays as a fallback.
- **Sensors, plug and play:** your state of charge and power sensor with their value of now; choose another pair from what Home Assistant has, or search yourself. Your measurements stay with the battery; **Start measuring over** clears them.
- **Make a back-up** and **restore a back-up** in the window. **Clear measurements** asks twice, in red, and offers a back-up first.

**Facts, only facts matter.**

- Above 100 % stays *provisional* and a sudden drop stays *not confirmed yet*, until 5 measurements in a row show the same. *Provisional x/5* counts only measurements above 100 % that lie within 3 points of each other; the ⓘ shows how far apart the last 5 are. A small line shows the change since monitoring began.
- **Red only when it is sure:** after 5 full discharges in a row at or below 75 %, one message under Repairs and on the phone, with the Marstek report to attach.
- A measurement above **130 %** of new cannot be right and never counts: status *Check the power sensor*, with what to check.

**Report, back-up and sharing.**

- Button **Report** on the card: full, anonymous to share, or for Marstek (English). Share your anonymous report on GitHub via the issue form **Share data (anonymous)**, so batteries can be compared.
- One versioned data format: a newer monitor always reads an older back-up.

**Smooth updates and installs.**

- After an update the card offers one tap to load the new card; before the restart it says to restart Home Assistant.
- Right after adding the first battery the monitor says to refresh the page once (no more *Timeout waiting for strategy element*).
- Removing a battery also removes its messages under Repairs.
- The card says when a full discharge has been reached and that the measurement is saved as soon as the battery charges again.

**Demo of every situation** (action `marstek_capacity_monitor.demo`) and a guide in English, Dutch and German, with the new page *How the monitor measures*.

Thanks to everyone on Tweakers and the Home Assistant forum who tested and reported, among them dannyro, amvolleb, 3DWim, DeBeginner and Driek.

## v0.5.5-rc5 — release candidate (not released, became v1.0.0)

**Settings window, polished.**

- Three columns on a wide screen, grouped by subject: **sensors** (state of charge and power, sign of the power sensor, cell voltage) · **battery** (factory data, warranty, limits) · **messages and data**. Two columns on a medium screen, one on a phone.
- **Make a back-up right in the window:** one file with all measurements of the battery, downloaded to your device and also kept in Home Assistant (folder `marstek_capacity_monitor/backup`). A report (button Report on the card) stays something else: for reading and sharing.
- **Restore a back-up right in the window:** press **Run** and choose the back-up file, pick **Merge** or **Replace**, then **Restore**. A full back-up of the current data is always made first. No more detour through the settings screen of Home Assistant.
- Every sensor button now says **Choose**.
- **Clear measurements** asks twice, in red: what will be cleared, whether you made a back-up (with a button to make one), a switch *I know all measurements will be gone*, and only then **Yes, clear everything**.
- **Margin below spec** goes from 0 to 25 % (was 50 %), also in the settings screen of Home Assistant.
- Tab Experiment: "Experiments that are not finished yet."
- Card: once a full discharge has gone down to 15 % or lower, it says **Full discharge reached** and that the measurement is saved as soon as the battery charges again.
- Card: right after an update, before Home Assistant has been restarted, the card no longer gives the advice about the app cache. It now says: **New version installed, restart Home Assistant to finish it.** The cache advice stays for a page that really runs an old card.

## v0.5.5-rc4 — release candidate (pre-release)

**Just installed? Refresh once.**

- Right after adding the first battery, *Battery capacity* is already in the sidebar, but a page that was open before does not have the card yet. Opening it gave *Timeout waiting for strategy element*, and the Home Assistant app kept that page. Now the window after adding the battery says to refresh the page once, and a notification says the same (it goes away when clicked away or at the next restart). No file to add yourself. Thanks to DeBeginner and Driek on Tweakers.
- Guide (EN/NL/DE): new row under Troubleshooting for this message.

## v0.5.5-rc3 — release candidate (pre-release)

**Settings in an own window, behind the gear on the card.**

- The gear ⚙ on a battery card now opens an own settings window instead of the general forms of Home Assistant. Two tabs: **Standard** and **Experiment**. Own fields: −/+ for numbers (tap the number to type it), sliders for the limits, switches, choice buttons, and an ⓘ with the explanation per setting.
- **Sensors**: the state of charge and power sensor with their value now, name and entity id. **Change** shows the pairs Home Assistant has, with their value of this moment, or search yourself by name or entity id. Same checks as before (not twice the same sensor, a warning for an AC-side sensor). **Start measuring over** clears the old measurements; without it they stay.
- All other settings are in the same window: factory data and warranty, red limit and margin, messages, menu item, sensitivities, sign of the power sensor, cell voltage sensors. **Save** stores the changes at once, with the same checks as the form.
- **Experiment**: cell temperature sensors, and a place for trials that are not finished yet (a weak cell, later). Off by default.
- **Clear measurements** in the window itself (asks once more). Restoring a back-up still goes through the settings screen of Home Assistant; the window has a button for it. That screen (Configure) also stays available, as a fallback.
- Only for an administrator; anyone else still goes to the screen of Home Assistant.
- Two columns on a wide screen, one below the other on a phone. Sensor values are rounded as Home Assistant shows them. Cycles step per 1000, the warranty per whole year.
- Back (Esc, the back button, the back gesture on a phone) goes one step back: first an open list or explanation, then the window. It never leaves the dashboard.
- Messages under Repairs and the guide now point to the gear on the card.
- Fix: removing a battery also removes its messages under **Settings → Repairs**, and the made-up sensors of the demo battery.

## v0.5.5-rc2 — release candidate (pre-release)

**Change sensors without starting over.**

- New under **Configure → Change sensors**: pick another state of charge or power sensor for a battery. The scan proposes the pairs it finds, each with its value now (a power sensor that is not at about 0 W while the battery is idle is usually the wrong one); or choose them yourself, with the same checks as when adding a battery (not twice the same sensor, a warning for an AC-side sensor).
- The measurements stay with the battery. A discharge in progress and the automatic plus/minus detection start again, as they belonged to the old sensor. **Start measuring again** deletes the old measurements, for when they were made with a wrong sensor.
- Fix: the messages *Check the power sensor* and *impossible power value*, and the guide, sent you to Configure to choose another sensor, but that choice was not there. They now point to **Configure → Change sensors**. Thanks to dannyro on Tweakers for spotting it.

## v0.5.5-rc1 — release candidate (pre-release)

**Facts, only facts matter.** Everything since v0.5.2 in one version: v0.5.5-dev1 and dev2 below, plus:

**A measurement that cannot be right does not count.**

- Above **130 %** of new, more energy was counted than fits in the battery. That is not the SOC meter (it explains at most about 120 %) but the power sensor: stuck on its last value instead of falling back to 0 W, the wrong sensor, or the wrong scaling factor. A user saw 1,300 % with status *Good*.
- Such a measurement is kept in the history but never counts: not in the measured value, the monthly trend, red or *provisional*. Between 100 and 130 % everything stays as it was (*provisional*).
- When the newest full discharge is one of these, the status is **Check the power sensor** (orange), the card shows *check sensor* with an explanation behind ⓘ, the overview shows ⚠, and a message appears under **Settings → Repairs** with what to check. It disappears by itself at the first credible full discharge.
- The numbers in that message are whole numbers without separators (*1301 %*, *60 kWh*), so they read right in every language, whatever the system language of Home Assistant.
- New attributes on `sensor.marstek_<id>_capacity_pct`: `impossible_count`, `impossible_last_pct`, `impossible_limit_pct`. History entries have `impossible`.
- Demo: new situation *Check the power sensor*.

**After an update: tap to load the new card.**

- The Home Assistant app on a phone keeps a page open for days and, after a restart, only reconnects: the old card keeps running, sometimes with an error. The card now compares its own version with the one installed (new attribute `version` on `sensor.marstek_<id>_monitor_status`). When they differ, a blue bar appears: *New version of the monitor installed — tap here to load the new card*.
- Still the old card after that tap? An orange bar explains the app's own button: Settings → Companion app → Troubleshooting → Reset frontend cache.
- No automatic reload: the page never jumps by itself. Works from this version on; a card from before 0.5.5 cannot show the bar yet.

**Guide.** Troubleshooting (EN/NL/DE): new rows for *far above 100 %* and for the refresh bar.

## v0.5.5-dev2 — test version (pre-release)

**Facts, only facts matter.** The monitor no longer jumps to conclusions on one odd measurement: above 100 %, a sudden drop and red each wait for 5 measurements in a row.

**Red is reported, once it is sure.**

- After 5 full discharges in a row at or below 75 %, one message under **Settings → Repairs** (red) and on the phone: measured value, how many in a row, and the hint to download the Marstek report and attach it in the Marstek app. One odd measurement never gives this message. It disappears by itself when the capacity is above 75 % again; *Ignore* dismisses it for this series.
- New attributes on `sensor.marstek_<id>_capacity_pct`: `red_count`, `red_confirmed`, `red_since`.

**Small things.**

- The report has **← Back to Home Assistant** when opened from Home Assistant (on a phone the report replaces the app view). A downloaded or shared copy has no such button.
- *Let op* and advice are coloured icons on the card and in the overview: an orange triangle and a red wrench, instead of grey emoji that hardly stood out.
- The anonymous report shows what you share in two blocks: green *This is in the file*, grey *This is not in it* (no names, sensor names, address or town).
- After *Reset measurements* the card starts from the state of charge the battery shows now, instead of *now – %* until it moves.
- Demo: new situation *Report to Marstek, confirmed* (red + message).

## v0.5.5-dev1 — test version (not released)

**How sure is the latest value?**

- **Above 100 %:** grey with *provisional 3/5* until 5 measurements in a row are above 100 % and no more than 3 points apart; then green with *above new* (new cells often deliver more than the rating plate, and the plate assumes 51.2 V while the battery works around 52–53 V). The real value is always shown, never cut off at 100 %.
- **Suddenly lower:** a drop of more than 5 points against the 3 measurements before it, that also moves the value shown, is grey with *not confirmed yet* and status *Not confirmed yet* instead of orange or red. Real wear is slow; such a jump is nearly always the battery's SOC meter shifting for a while. After 5 low measurements in a row it counts as real; when it recovers the note goes away. No Repairs or phone message for this.
- **Since monitoring began:** a small line in the Measured box, e.g. *−1.2 % since monitoring began*, against the middle of the first 3 measurements of this monitor (not against new). Appears after 3 full discharges.
- New attributes on `sensor.marstek_<id>_capacity_pct`: `display_state`, `baseline_pct`, `since_start_pct`, `confirm_count`, `confirm_needed`, `drop_ref_pct`.

**Report, back-up and restore.**

- New button **Report** on the battery card: *Full back-up*, *Anonymous to share* or *For Marstek* (in English). The report opens in a new tab, in the same style as the HESC report, behind the login of Home Assistant (a short-lived signed link; nothing in the public `www` folder). **Download report** saves it as one HTML file with the data embedded: what you see is what you share.
- **Restore:** Configure → *Restore back-up* (report or JSON file; merge or replace). A full back-up of the current data is written first to `/config/marstek_capacity_monitor/backup/`.
- One versioned format (`schema`), so a newer monitor always reads an older back-up. When a future version changes how data is stored, a back-up is written automatically before converting.
- **Download diagnostics** (Settings → Devices & services → the monitor → ⋮) now works, with the battery name left out.
- New issue form **Share data** on GitHub, for the anonymous report.

**Demo of every situation.**

- Action `marstek_capacity_monitor.demo` with a situation (normal, above 100 %, sudden drop, below spec, red, check the model, SOC drift, cell calibration, …). It adds a battery *Demo* once and fills it with made-up data; the card, Repairs and phone messages react as for a real battery. Your own batteries are untouched; remove *Demo* like any other battery.

**Guide.**

- New page *07 – How the monitor measures* (EN/NL/DE): why only full discharges count, why measuring while the battery charges in between is not reliable, why a battery can come out above 100 %.
- Troubleshooting (EN/NL/DE): rows rewritten or added for above 100 %, suddenly lower, since monitoring began, measuring in between, report and back-up; the battery scan row mentions German and Dutch names.

## v0.5.2 — 2026-10-25

**Lost in translation... fixed!**

- The search for batteries now also knows German and Dutch names. In a German Home Assistant the sensors are called *SoC Batterie* and *Batterieleistung*, in Dutch *Laadtoestand* and *Batterijvermogen*; until now only English names such as *battery power* were found. Thanks to the simon42 community for the report.
- Phones and tablets with the Home Assistant app are no longer offered as a battery (the app reports a battery level and a battery power too).

**Impossible power values are ignored.**

- A power sensor that reports more than 25 kW is ignored: no home battery charges or discharges that fast. Usually the unit is wrong (kW while the value is in W) or a self-made sensor multiplies mA or mV. Before, such a sensor made the full cycles jump by hundreds in a day.
- A message under **Settings → Repairs** says which sensor, which value, and what to check. It goes away by itself after 24 hours without such values. Already counted too much? *Reset measurements* starts the count again.

## v0.5.1 — 2026-10-24

**Battery capacity in the sidebar by itself.**

- After adding the first battery, **Battery capacity** (NL *Batterijcapaciteit*, DE *Batteriekapazität*) appears in the sidebar, with all your batteries arranged for you (1 to 6). Nothing to set up. It is read-only; for your own layout, make a dashboard from *Marstek battery capacity* under Add dashboard as before.
- Off under **Configure → Menu item in the sidebar**. Off for one battery = no menu item. An existing dashboard of your own at `/marstek-capacity` is left alone.
- The one-click dashboard with `lang: nl` (or `de`, `en`) now also gives that language to the cards, not only to the title.

**Above 100 %: explained instead of a surprise.**

- A measured value above 100 % now reads *provisional* on the card (after 3 measurements: *check*), with the explanation when you point at it. Higher than new is hardly possible; it usually comes from the battery's SOC meter standing still at the top or bottom while energy keeps flowing.
- The monitor now sees that itself: if the first or last 3 SOC points of a discharge cost 2× (or more) the energy per point of the middle (30–80 %), the measurement is shown as an open dot (○ less reliable) with the reason when you point at it. Applies to new measurements.
- Troubleshooting (EN/NL/DE): the row *Percentage above 100 %* is rewritten. The old advice (adjust the internal reserve) was wrong: the reserve only changes the kWh, not the percentage.

- Easier to find: tap or click *provisional ⓘ* (or *check the model ⓘ*) on the card and a small window explains it, also on a phone. A value above 100 % is shown in grey instead of green: not certain yet. The overview has an ⓘ after such a value.

**Venus C.**

- New model: **Venus C** (2.56 kWh, 90 %, more than 6,000 cycles; 80 % after 6,000 assumed, as for the Venus E). Same Modbus registers as the Venus E v1/v2. Picked by itself when its name says Venus C.
- A Venus C can report the same model code as a Venus E v1/v2 (HMG). The model step now says: Venus C? Pick Venus C, also when Venus E v1 / v2 is already selected.
- Safety net: a measurement of about half (40–60 %) is no longer red *report to Marstek* but orange **Check the model**, with a message under Settings → Repairs on how to change it. A Venus C set up as a Venus E measures about 50 %.
- Supported batteries (EN/NL) and Troubleshooting (EN/NL/DE) updated.

**Dashboard in Firefox and on Android.**

- Fix: *Timeout waiting for strategy element ll-strategy-dashboard-marstek-capacity to be registered* in Firefox and in Chrome or Brave on Android (#5). The card file was ready before Home Assistant itself and registered its cards and dashboard in a place Home Assistant no longer looks once it starts. The card now waits until Home Assistant has started.

**Guides and smaller things.**

- Installation (EN/NL/DE): the sidebar item, how to turn it off and how to bring a hidden item back. Venus C in the model lists (README, Installation, Configuration).
- Troubleshooting (EN/NL/DE): no measurement while the battery often runs far down (charging back 3 points ends the swing; thanks to @brauwers1981 for the tip in #1), sidebar item missing, nothing under Resources is correct, and the timeout error in Firefox/Android.
- The card texts about the colours now use your own settings (tolerance and red limit) instead of the fixed 5 points and 75 %.
- Supported batteries: the 88 % tip only changes the kWh, not the percentage.
- New screenshot of the standard cards.
- Gear on the card: the back arrow on the settings page now takes you back to the dashboard you came from, instead of the integrations overview.
- Supported batteries: a Venus C that stops around 11 % gets a reserve of 0.28 kWh (thanks to Flori on simon42).
- README (EN/NL/DE): a *Support this project* section. Find the tool useful? A ⭐ on GitHub helps others find it, and there is a Ko-fi button.

## v0.5.0 — 2026-10-22

**SOC drift and cell calibration: the monitor sees when the SOC meter drifts or the cells get out of balance, and tells you what to do. Plus three new models.**

SOC drift
- New: `sensor.marstek_<id>_soc_health` — `ok` / `letop` (attention) / `advies` (advice). The monitor compares every step of the state of charge with the DC energy that went in or out. A jump the energy does not explain, extra charging while it says 99 %, hanging at 100 % while discharging, or 14 days never completely full: that is an occurrence (5 % or more). Gaps in the data, restarts, a brief 0 % and jumps on two batteries at the same time (the connection) do not count; neither does a battery that is full almost every day.
- Only for a pattern, within **45 days**: 1× is only recorded, 2× is **attention** (discharge once to the discharge limit and charge to full in one go), 3× is **SOC drift detected** (do that twice). The monitor sees when you have done it and the message disappears; also after 45 quiet days.

Cell calibration (with cell voltage sensors)
- New: `sensor.marstek_<id>_cell_health`. Normal is what your own battery did in its first 3 months; an occurrence is a cell spread of 2× that. 2 in a row is **attention** (keep it full for about 4 hours), 3 in 45 days is **cell calibration advised** (8 hours in UPS mode, or in charge mode without UPS mode; if it stays high, report it via the Marstek app). The monitor sees how long the battery stood full and at rest.

Messages
- **Sensitivity** per battery under Configure, separately for SOC drift and cell calibration: Off, Relaxed (8 % / 3×), Normal (5 % / 2×, default) or Strict (3 % / 1.5×).
- **Attention** and advice as a message on your phone (Home Assistant app) and under Settings → Repairs, in English, Dutch or German. On by default; per battery under **Configure → Notifications**.
- **Dismiss** once — on the card, in the phone message, or *Ignore* under Repairs — and it is gone everywhere until a new series. Also as the action `marstek_capacity_monitor.dismiss_advice`, and the event `marstek_capacity_monitor_advice` for your own automations.

Card
- Three small buttons under the status: **Chart · SOC · Cells**. *Chart* opens in place of the capacities, so the card keeps its height; *SOC* and *Cells* open as a window in the middle of the screen. ⚠ or 🔧 on a button means: look inside.
- Calmer and the same height side by side: the monthly row is gone (the chart shows the months), the spec line is one short line (*Margin · cycles · age*, details when you point at it), the next-step line only shows while collecting data or during a full discharge, and the foot line sits at the bottom with the version of the card.
- A cog next to the buttons takes you to the battery's settings.
- SOC panel: *Days completely full* and *SOC meter was right* (✓ or ⚠ with how much it was off) per month; Cells panel: *Cells in balance* (mV, ⚠ at 2× normal). Details when you point at a cell.
- Chart, simpler: ● measured, calibrated · ○ less reliable (not completely full in the 14 days before, or cells below 5 °C) · grey dashed line expected per spec · red dashed line report to Marstek. The *How to read this?* text is gone; details when you point at a dot.
- The cell spread moved from the card into the Cells panel.
- Overview: ⚠ or 🔧 after the battery name.
- The cards follow the light or dark theme of Home Assistant.
- The foot line no longer shows *n=*; the status line already says how many full discharges were measured.
- The button-card templates follow the language of Home Assistant too when `lang` is left out (as the integration's own cards already did).
- After an update the browser loads the new card by itself, also for a test version with the same number.
- Button-card templates and ready-made dashboards updated: paste the new `marstek_capacity_templates.yaml` again if you use them.

Cycles before monitoring and extra sensors
- New: **cycles before monitoring filled in by itself.** If the battery has its own *total discharged* counter (Modbus, ESPHome), the monitor uses it when you add a battery: counter ÷ usable capacity. That counter measures on the AC side, so this is an estimate, less exact than the cycles the monitor counts itself on the DC side; the settings screen and the card (point at the cycles line) say so. A value you entered yourself is never overwritten.
- New: **extra sensors found** under Settings → Repairs, after start-up (so also after this update): cell voltage sensors that are not filled in yet, and the *total discharged* counter while *cycles before monitoring* is still 0. Tick what you want to add and press Submit; what you leave unticked is not asked again.

Models
- New: **Venus E 4.0** (5.024 kWh, 88 %), **Venus E Max** (10.048 kWh, 90 %) and **Venus E Pro** (2.08 kWh per pack, 1–6 packs, 90 %). Marstek lists more than 10,000 cycles without a capacity percentage; the monitor assumes 80 % after 10,000. See [Supported batteries](docs/05-supported-batteries.md).

Upgrade: update in HACS, restart Home Assistant and refresh your browser (Ctrl+F5). Measurements and settings are unchanged. SOC drift is tracked from the update onwards (a newly added battery also looks at the recorder history); cell calibration uses the cell measurements you already have. Older capacity measurements show as a filled dot.

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
