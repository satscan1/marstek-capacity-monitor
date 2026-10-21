# Configuration

*[Nederlands](02-configuration.nl.md)*

All values are set when you add a battery. Change them later under **Settings → Devices & services → Marstek Capacity Monitor → Configure**.

| Setting | Default | Meaning |
|---|---|---|
| Rated capacity | 5.12 kWh | Total in the cells per manufacturer |
| Internal reserve | 0.51 kWh | Part the battery never releases; rated capacity × (100 % − depth of discharge). 0.51 = 90 %, 0.61 = 88 % |
| Model | – | Venus E v1/v2, Venus E v3, Venus D or other. Fills in the factory data when adding; see [Supported batteries](05-supported-batteries.md#factory-data-per-model) |
| Installation date | – | For age and the end of the warranty period |
| Warranty period | 10 years | Shown on the card for information only |
| Rated cycle life | 6,000 | Manufacturer spec |
| Capacity after rated cycle life | 80 % | Manufacturer spec; together with cycle life this is the spec line |
| Cycles before monitoring | 0 | Estimate for a battery already in use: total discharged kWh ÷ usable capacity |
| Red threshold | 75 % | At or below this percentage: report via the Marstek app |
| Tolerance below spec | 5 points | While the measurement is at most this far below the spec, the status stays green |
| Sign of the power sensor | Automatic | Only change if automatic detection gets it wrong |
| Highest / lowest cell temperature | empty | Optional, experimental. Stored with every measurement as context (a cold battery gives less). Only cell temperatures, never MOS / board temperatures |
| Highest / lowest cell voltage | empty | Optional, for the cell balance check. Fill in both or neither. Only cell **voltages**: some connections report MOSFET temperatures as "cell temperature" |

## Sensors

| Entity | What |
|---|---|
| `sensor.marstek_mt1_measured_capacity` | Measured capacity (kWh). Attributes: `trend` (per month, newest → oldest) and `history` (last 10 full discharges), both with `temp_c` when cell temperature sensors are set |
| `sensor.marstek_mt1_capacity_pct` | Remaining capacity: measured capacity as % of new |
| `sensor.marstek_mt1_expected_capacity` | Manufacturer spec (%) at the current number of cycles |
| `sensor.marstek_mt1_margin` | Margin vs spec (kWh) |
| `sensor.marstek_mt1_cycles` | Number of full cycles |
| `sensor.marstek_mt1_warranty_status` | Capacity status: `good` / `attention` / `critical` / `no_measurement` |
| `sensor.marstek_mt1_monitor_status` | Is the measurement itself working: `measuring` / `collecting` / `no_recent_data` / `sensor_missing`. Attributes: `phase` (next step to a measurement), `soc`, `full_discharges`, `power_sign` |
| `sensor.marstek_mt1_cell_spread` | Only with cell sensors: spread between highest and lowest cell after the last full charge (mV). Attributes: `trend` (monthly median, new → old) and `history` |
| `sensor.marstek_mt1_last_full_discharge` · `_last_full_charge` | Date and time of the last full discharge (≥ 95 % → ≤ 15 %) and full charge (≤ 15 % → ≥ 95 %) |
| `sensor.marstek_mt1_nominal_capacity` · `_usable_capacity` · `_red_threshold` · `_warranty_end` · `_dc_discharged` | Diagnostics. `_dc_discharged` also shows which sensors are used and how the sign was detected |

After every recorded swing, the integration fires the event `marstek_capacity_monitor_session`. You can use it to forward the records yourself, for example to InfluxDB.

Write load stays low:

* the `trend` and `history` lists are not written to the recorder database;
* the sensors only change after a measurement or once per hour.

## Resetting measurements

Use the action `marstek_capacity_monitor.reset_measurements` with the battery as target. This cannot be undone.

If you remove a battery from the integration, its measurements stay in `.storage/`. They may be needed as evidence when you report a problem to Marstek.
