# Configuration

*[Nederlands](02-configuration.nl.md)*

All values are set when you add a battery. Change them later under **Settings → Devices & services → Marstek Capacity Monitor → Configure**.

**Need another sensor?** Tap the gear ⚙ on the card of the battery: **Sensors** → **Change** (from 0.5.5). All other settings are there too, in an own window with the tabs **Standard** and **Experiment**. The scan proposes the sensors it finds, with their value now; or choose them yourself. Your measurements stay with the battery. Were they made with a wrong sensor, turn on **Start measuring over**.

| Setting | Default | Meaning |
|---|---|---|
| Rated capacity | 5.12 kWh | Total in the cells per manufacturer |
| Internal reserve | 0.51 kWh | Part the battery never releases; rated capacity × (100 % − depth of discharge). 0.51 = 90 %, 0.61 = 88 % |
| Model | – | Venus E v1/v2, Venus E v3, Venus E 4.0, Venus E Max, Venus E Pro, Venus C, Venus D or other. A Venus C can report itself as a Venus E v1/v2: then pick Venus C yourself. Fills in the factory data when adding; see [Supported batteries](05-supported-batteries.md#factory-data-per-model) |
| Installation date | – | For age and the end of the warranty period |
| Warranty period | 10 years | Shown on the card for information only |
| Rated cycle life | 6,000 | Manufacturer spec |
| Capacity after rated cycle life | 80 % | Manufacturer spec; together with cycle life this is the spec line |
| Cycles before monitoring | 0 | For a battery already in use: total discharged kWh ÷ usable capacity. If the battery has a *total discharged* counter (Modbus, ESPHome), the monitor fills this in itself. That counter measures on the AC side: an estimate, less exact than the cycles the monitor counts itself on the DC side. See [Extra sensors found](#extra-sensors-found) |
| Red threshold | 75 % | At or below this percentage: report via the Marstek app |
| Tolerance below spec | 5 points | While the measurement is at most this far below the spec, the status stays green |
| Sign of the power sensor | Automatic | Only change if automatic detection gets it wrong |
| Highest / lowest cell temperature | empty | Optional, experimental. Stored with every measurement as context (a cold battery gives less). Only cell temperatures, never MOS / board temperatures |
| Highest / lowest cell voltage | empty | Optional, for the cell balance check. Fill in both or neither. Only cell **voltages**: some connections report MOSFET temperatures as "cell temperature" |
| Sensitivity SOC drift / cell calibration | Normal | Off (only on the card), Relaxed (SOC 8 %, cells 3× normal), Normal (5 %, 2×) or Strict (3 %, 1.5×). See [How it works](03-how-it-works.md#messages-and-dismissing-from-05) |
| Notifications | on | Message on your phone and under Repairs for SOC drift or cell calibration, only for a pattern. Off = no messages; the card still shows it. See [How it works](03-how-it-works.md#messages-and-dismissing-from-05) |
| Menu item in the sidebar | on | From 0.5.1: **Battery capacity** in the sidebar, with all your batteries. Applies to the whole menu item: off for one battery = no menu item. See [Installation](01-installation.md#in-the-sidebar-by-itself-from-051) |

## Sensors

| Entity | What |
|---|---|
| `sensor.marstek_mt1_measured_capacity` | Measured capacity (kWh). Attributes: `trend` (per month, newest → oldest) and `history` (last 10 full discharges), both with `temp_c` when cell temperature sensors are set |
| `sensor.marstek_mt1_capacity_pct` | Remaining capacity: measured capacity as % of new |
| `sensor.marstek_mt1_expected_capacity` | Manufacturer spec (%) at the current number of cycles. Attributes: `cycles`, `initial_cycles` (cycles before monitoring), `cycle_counter` (the counter it came from, empty = entered by hand) |
| `sensor.marstek_mt1_margin` | Margin vs spec (kWh) |
| `sensor.marstek_mt1_cycles` | Number of full cycles |
| `sensor.marstek_mt1_warranty_status` | Capacity status: `good` / `attention` / `critical` / `no_measurement` |
| `sensor.marstek_mt1_monitor_status` | Is the measurement itself working: `measuring` / `collecting` / `no_recent_data` / `sensor_missing`. Attributes: `phase` (next step to a measurement), `soc`, `full_discharges`, `power_sign` |
| `sensor.marstek_mt1_cell_spread` | Only with cell sensors: spread between highest and lowest cell after the last full charge (mV). Attributes: `trend` (monthly median, new → old) and `history` |
| `sensor.marstek_mt1_soc_health` | SOC drift: `ok` / `letop` (attention) / `advies` (advice). Attributes: `count` (occurrences in 45 days), `since`, `last_size` (%), `last_calibration` (last time completely full), `dismissed`, `notify`, `trend` (per month: `full_days`, `dev`, `b99`, `jump`, `hang`, `no_full_days`) |
| `sensor.marstek_mt1_cell_health` | Only with cell sensors: cell calibration `ok` / `letop` / `advies`. Attributes: `count`, `since`, `base_mv` (normal, first 3 months), `limit_mv` (2× normal), `last_mv`, `dismissed`, `notify`, `trend` (per month: `spread_mv`, `n`, `rest_h`, `temp_c`) |
| `sensor.marstek_mt1_last_full_discharge` · `_last_full_charge` | Date and time of the last full discharge (≥ 95 % → ≤ 15 %) and full charge (≤ 15 % → ≥ 95 %) |
| `sensor.marstek_mt1_nominal_capacity` · `_usable_capacity` · `_red_threshold` · `_warranty_end` · `_dc_discharged` | Diagnostics. `_dc_discharged` also shows which sensors are used and how the sign was detected |

After every recorded swing, the integration fires the event `marstek_capacity_monitor_session`. You can use it to forward the records yourself, for example to InfluxDB.

When the SOC drift or cell calibration level changes, it fires `marstek_capacity_monitor_advice` (`entry_id`, `name`, `battery`, `kind` = `soc` or `cells`, `level`, `count`, `size`). Use it for your own notification, for example on a speaker.

Write load stays low:

* the `trend` and `history` lists are not written to the recorder database;
* the sensors only change after a measurement or once per hour.

## Extra sensors found

If a battery's device has sensors the monitor does not use yet, it says so under **Settings → Repairs** (*MT1: extra sensors found*). This happens after start-up, so also after an update:

* **Highest and lowest cell voltage**, if not filled in yet. With these the monitor follows the cell balance.
* **Total discharged counter**, if *Cycles before monitoring* is still 0. The monitor works out: (counter − what it already counted itself) ÷ usable capacity. That counter measures on the AC side, so this is an estimate, less exact than the cycles the monitor counts itself on the DC side. A value you entered yourself is never overwritten.

Open the message, tick what you want to add and press **Submit**. Leave something unticked and it will not ask again; you can always add it later under **Configure**. For a new battery this happens right when you add it.

## Dismissing a message

The action `marstek_capacity_monitor.dismiss_advice` with `battery` (e.g. `mt1`) and `kind` (`soc` or `cells`) does the same as **Dismiss** on the card: the message disappears everywhere and only comes back with a new series.

## Resetting measurements

Use the action `marstek_capacity_monitor.reset_measurements` with the battery as target. This cannot be undone.

If you remove a battery from the integration, its measurements stay in `.storage/`. They may be needed as evidence when you report a problem to Marstek.
