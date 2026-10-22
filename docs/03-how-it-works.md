# How it works

*[Nederlands](03-how-it-works.nl.md)*

## Three capacities, kept strictly apart

| | Meaning | Venus E 5.12 kWh |
|---|---|---|
| **Rated capacity** | Total capacity of the cells, as specified by the manufacturer | 5.12 kWh |
| **Usable capacity** | Rated capacity × depth of discharge (DoD). This is **100 % of new**. | 90 % DoD → 4.61 kWh |
| **Measured capacity** | What actually came out of the cells during a **full discharge**, scaled to the usable band | e.g. 4.46 kWh = 97 % |

## How it measures

1. **Event**: every change of state of charge or DC power.
2. **Context**: the monitor integrates DC power into energy (like a Riemann helper, max. 1 minute per step) and detects charge and discharge swings. A swing closes once the state of charge moves back 3 points from its extreme. Only swings of 20 points or more are recorded.
3. **Result**: one record per swing, stored in Home Assistant itself (`.storage`). No InfluxDB needed.

Only **full discharges** count towards capacity: they must start at 95 % or higher and end at 15 % or lower. The calculation:

```
measured kWh = DC energy out of the cells ÷ drop in state of charge × usable band
```

### Conversion to 100 % of new

The battery's state of charge (SOC) runs from 0 to 100 % of the **rated capacity**. Only the part within the depth of discharge is usable: at 90 % that is 90 SOC points. The monitor measures how many kWh come out of the cells per SOC point and scales that to the full usable band. That result is what the battery delivers now, and it is compared with the usable capacity of a new battery (= 100 %).

Example (rated 5.12 kWh, reserve 0.61 kWh, so 88 % usable = 4.51 kWh):

| Step | Value |
|---|---|
| Measured full discharge | 100 % → 11 % = 89 SOC points, 4.42 kWh DC |
| Per SOC point | 4.42 ÷ 89 = 0.0497 kWh |
| Scaled to the usable band | 0.0497 × 88 = 4.37 kWh |
| Remaining | 4.37 ÷ 4.51 = **97 %** |

The usable band differs per model; see [Supported batteries](05-supported-batteries.md#depth-of-discharge-per-model).

The value shown is the **median of the last 3** full discharges in the past year.

Partial discharges are deliberately ignored, because one percent near the bottom delivers more kWh than one near the top. A Home Assistant restart of up to 10 minutes is bridged: the energy in those minutes is estimated from the power just before and just after (usually less than 0.5 % difference). If the power sensor is briefly unavailable (for example a flaky Modbus connection), that is bridged the same way, up to 5 minutes. If the restart or the outage takes longer, that swing does not count.

## Manufacturer spec and colours

The line the measurement is compared with is the **manufacturer's spec per cycle**: 80 % capacity after 6,000 full cycles, i.e. 0.0033 points per cycle. Full cycles = DC discharged kWh ÷ usable capacity, plus any cycles done before monitoring started. The "spec" figure on the card is that line at the current number of cycles (e.g. 98.8 % at 369 cycles).

This is a **specification, not a warranty**. Marstek gives no capacity guarantee in years, so there is no time line.

| Colour | Meaning |
|---|---|
| 🟢 Green | Within spec, or at most 5 points below |
| 🟠 Orange | Below spec, but above 75 % |
| 🔴 Red | **75 % or lower**: report it to Marstek **via the Marstek app** |

The margin shows how many kWh the battery is above or below the spec. All thresholds can be adjusted.

The measurements **support a report**; they are not proof. They show how capacity develops over months.

The sources for these figures are listed in [Supported batteries](05-supported-batteries.md#sources-for-the-manufacturer-specs).

## Monitor status

Next to the capacity status, every battery has a **monitor status** that tells you whether the measurement itself works:

| Status | Meaning |
|---|---|
| Measuring | Sensors deliver data and at least one full discharge has been measured |
| Collecting data | Sensors deliver data; waiting for the first full discharge |
| No recent data | The battery was charging or discharging (more than 50 W), but the state of charge and the power reported no new value for an hour; check the battery connection. A battery standing still (empty or full, around 0 W) often sends the same values for hours; that does not count |
| Sensor unavailable | The state of charge or power sensor is unavailable |

The card shows the next step on the way to a measurement: charge to 95 % or more, then discharge to 15 % or lower. A discharge that was interrupted (gap in the data) does not count; the card says so.

## Cell balance

Optional, when your connection provides the highest and lowest cell voltage.

* **Event:** the end of a full charge (state of charge ≥ 95 %).
* **Context:** the battery rests (power within ±50 W) for 5 minutes, so load does not distort the voltages. LFP cells hardly differ in the middle of the band; differences only show near full.
* **Result:** the spread between the highest and lowest cell, in mV. One sample per full charge; the next sample needs the battery to drop below 90 % first. The card shows the monthly median, trend column first, new → old.

Marstek publishes no normal value for the spread. From 0.5 the monitor therefore compares with what is normal for **your** battery (the first 3 months): a ⚠ at twice that. See Cell calibration below.

## SOC drift (from 0.5)

**What is it?** The battery does not know exactly how full it is; the state of charge (SOC) is an estimate it keeps by counting current. Small errors add up. Only when the battery is completely full (charging stops by itself) does it put the counter right again. If that does not happen for a long time, the SOC meter drifts further off: **SOC drift**. You notice it as jumps (e.g. from 57 % to 91 % in a minute), as "99 %" while a lot still goes in, or as a battery that stays at 100 % for a long time while discharging.

**Why does it matter?** With a skewed SOC meter the battery stops too early or too late, and a capacity measurement becomes less certain. That is why a measurement gets an **open dot** in the chart when the battery was not completely full in the 14 days before (or when the cells were colder than 5 °C).

**How does the monitor measure it?**
* **Event:** the state of charge changes.
* **Context:** the counted DC power. If the SOC moves more than 3 % faster than the energy explains, that is a correction. Gaps in the data, a restart, a brief 0 % and jumps that happen at the same time on another battery (then it is the connection) do not count.
* **Result:** an **occurrence** is a deviation of 5 % or more, or 14 days not completely full (while Home Assistant was running). An occurrence only counts when the battery was completely full on fewer than 7 of the 14 days before; a battery that is full almost every day already corrects itself.

**The ladder** (period 45 days):

| Occurrences in 45 days | What you see | What to do |
|---|---|---|
| 1 | nothing, only recorded | – |
| 2 | ⚠ **Attention** | discharge the battery **once** down to the discharge limit, then charge it to full in one go, until charging really stops |
| 3 | 🔧 **SOC drift detected** | do that **twice** |

The monitor sees by itself when you have done this (a discharge to 20 % or lower, then completely full); the message then disappears. After 45 days without a new occurrence it also disappears by itself.

## Cell calibration (from 0.5)

**What is it?** The cells in a battery slowly drift apart: one cell is full before the other. The battery brings them back in line (balancing), but only when it stays **full and at rest** for a while. If it is never full for long, the cell spread grows and the battery can store less.

**How does the monitor measure it?** With the highest and lowest cell voltage (optional, see Cell balance above). What is normal differs per battery, so the monitor takes the middle of the **first 3 months** as normal. An **occurrence** is a cell spread of **2× normal** or more.

| When | What you see | What to do |
|---|---|---|
| 2 occurrences in a row | ⚠ **Attention** | charge the battery to full and keep it full for about **4 hours** (if your model has UPS mode: switch it on in the Marstek app for 4 hours, then back to your own mode) |
| 3 occurrences in 45 days | 🔧 **Cell calibration advised** | charge to full and switch on **UPS mode for 8 hours** (no UPS mode: leave it in charge mode for 8 hours), then back to your own mode. Calibrating takes a long time. If the spread stays high after that, report it via the Marstek app |

The monitor sees by itself how long the battery stayed full and at rest (4 hours for attention, 8 hours for advice); the message then disappears.

## Messages and dismissing (from 0.5)

* **Where:** on the card (buttons **SOC** and **Cells** with ⚠ or 🔧), as a message on your phone (Home Assistant app) and under **Settings → Repairs**.
* **Dismiss:** one click is enough: **Dismiss** on the card, in the message on your phone, or **Ignore** under Repairs. It applies everywhere. The message only comes back with a new series of occurrences.
* **Completely off:** per battery under **Configure → Notifications** (on by default). The card keeps showing the state; you just get no more messages.
* **Sensitivity:** per battery under **Configure**, separately for SOC drift and cell calibration: *Off* (only on the card, never attention or advice), *Relaxed* (SOC 8 %, cells 3× normal), *Normal* (5 %, 2×, default) or *Strict* (3 %, 1.5×).
* For automations: the sensors `sensor.marstek_<id>_soc_health` and `sensor.marstek_<id>_cell_health` (ok / letop / advies), the event `marstek_capacity_monitor_advice` and the service `marstek_capacity_monitor.dismiss_advice`.

## Cell temperature (experimental)

Optional. When you set the highest and/or lowest cell temperature, the monitor stores the average cell temperature during every full discharge with that measurement. The card shows it per month under the capacity (e.g. *spec 98 · 16 °C*) and in the chart.

Why: a cold battery gives less. A lower measurement in winter is then explained by the temperature instead of being mistaken for wear. The temperature is context only; it does not change the measured capacity or the colours.

Only **cell** temperatures belong here. Some connections report MOSFET (switching transistor) temperatures as "cell temperature"; the scan never proposes sensors with *mos*, *internal* or *board* in the name.

## Chart

Under the status there are three small buttons: **Chart · SOC · Cells**, and a cog on the right for the settings. *Chart* replaces the capacities (press again to go back), so the card keeps its height; *SOC* and *Cells* open as a window in the middle of the screen. The chart (old → new, left to right) shows the most recent 3 years and nothing more than:

* **●** measured, calibrated
* **○** less reliable: not completely full in the 14 days before the measurement, or cells colder than 5 °C
* **grey dashed line**: expected per spec
* **red dashed line**: report to Marstek (75 %)

Hover over a dot for the value, the cell temperature and why it is less reliable. The **SOC** window shows per month *Days completely full* and *SOC meter was right* (✓ or ⚠ with how much it was off); **Cells** shows *Cells in balance* (cell spread in mV, ⚠ from the limit set by the sensitivity). There too, point at a cell for the details. See [06 – Dashboard and gallery](06-dashboard-gallery.md) for the card explained with numbers.
