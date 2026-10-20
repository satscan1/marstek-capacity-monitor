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

Partial discharges are deliberately ignored, because one percent near the bottom delivers more kWh than one near the top. If the power data has a gap of more than 5 minutes during a swing, for example after a restart, that swing does not count.

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
