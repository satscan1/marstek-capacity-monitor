# 06 – Dashboard: layout, card and gallery

*[Nederlands](06-dashboard-gallery.nl.md) · [Deutsch](06-dashboard-gallery.de.md)*

This page shows how the cards look with 1 to 6 batteries, what each part of the battery card means and how to arrange the cards.

> All images on this page use **demo data**: six made-up batteries of different ages and conditions. They show how the cards look, not how a real battery ages. The gallery screenshots are in Dutch; the numbered card below is shown in English.

## Layout

The battery card is made for **one third of the width**: three batteries side by side.

| Number of batteries | Layout |
|---|---|
| 1 or 2 | The batteries, with the overview to the right (one row of three) |
| 3 | Overview two thirds wide, then 3 batteries |
| 4 | Overview two thirds wide, then 2 × 2 |
| 5 | Overview two thirds wide, then 3 + 2 |
| 6 | Overview two thirds wide, then 3 + 3 |

From 3 batteries on, one third next to the overview is free for a card of your own. If you leave it empty, Home Assistant moves the first battery up next to the overview; to start the batteries on a new row, put a card there (the one-click dashboard and the ready-made dashboards use a text card "Free spot"; the gallery shows the Dutch "Vrije plek").

The [one-click dashboard](01-installation.md#quickest-way-dashboard-in-one-click) uses this layout by itself. For button-card there are [ready-made dashboards](01-installation.md#ready-made-dashboard-with-button-card), one per number of batteries.

Arranging it yourself? Use Home Assistant's standard **Sections** layout. An example is in [`dashboard/button-card/layout-sections.yaml`](../dashboard/button-card/layout-sections.yaml). Give each card a width with `grid_options`: in a section three columns wide, `columns: 12` is one third and `columns: 24` is two thirds. With 4 batteries use `columns: 18` per battery.

## The battery card

![Battery card with numbers](../screenshots/gallery/card-numbered-en.png)

1. **Status**: *Good*, *Below spec*, *Report to Marstek (app)* or *Collecting data*. The colour follows the latest measurement.
2. **Is the monitor working?** Green: working, with the number of full discharges measured. Blue: still collecting data. Orange or red: no new data, or a sensor is missing. The line below tells the next step (for example *charge fully to 95 %*).
3. **Chart · SOC · Cells** (from 0.5 three small buttons under the monitor line): press one to open its panel, press it again to close it. A ⚠ (attention) or 🔧 (advice) on *SOC* or *Cells* means: look inside. The rest of the card does nothing when clicked. The SOC panel answers *Is my SOC meter still right?* with *Days completely full* and *SOC meter was right* per month; the Cells panel answers *Are my cells still in balance?*. With attention or advice you get a box with what to do and a **Dismiss** button. See [How it works](03-how-it-works.md#soc-drift-from-05).
4. **Period**: *recent 3 years of warranty*: the chart shows the most recent 3 years since installation.
5. **Chart**: each dot is one month, with the percentage of the usable capacity that was left. The grey dashed line is what the manufacturer expects at that age, the red line is 75 %. Hover over a dot for the exact value and the cell temperature that month (if you linked temperature sensors). An open dot ○ means *less reliable*: the battery was not completely full in the 14 days before, or the cells were colder than 5 °C.
6. **Three capacities**: *Rated* (on the type plate), *Usable* (rated minus the reserve the battery keeps) and *Measured* (what really comes out now, and what percentage of usable that is).
7. **Bar**: the measured capacity, with a white mark for the manufacturer spec and a red mark at 75 %.
8. **Manufacturer spec** at the current cycle count and age, and the margin: how far above (+) or below (−) you are.
9. **Monthly trend**: first the direction (▲ ▬ ▼), then the months from new to old. Large number = measured, small number = spec for that month, plus the cell temperature if available.
10. **Last full discharge and full charge**, and the number of measurements.

If you linked sensors for the highest and lowest cell voltage, the **cell spread after full charge** is in the **Cells** panel (until 0.4 it was below the trend).

## The overview

The overview lists all batteries (up to 6):

- **Battery**: with ✓ (monitor working), ⏳ (collecting data) or ⚠ (check the connection). From 0.5 also ⚠ (attention) or 🔧 (advice) for SOC drift or cell calibration; point at it for which one, and open the card of that battery.
- **Trend**: ▲ rising, ▬ stable, ▼ falling over the months shown.
- **Now**: the latest measurement.
- **Months**, new to old: large number = measured, small number = spec for that month.
- **Spec**: what the manufacturer expects now.

Green: within 5 points of the spec. Orange: below that. Red: 75 % or lower, report via the Marstek app.

## Gallery

Each of the six demo batteries shows a different situation:

| Battery | Situation |
|---|---|
| Demo 1 | 4 years old, good; outside, so open dots in winter; SOC meter clearly off twice: ⚠ attention on SOC |
| Demo 2 | 1.6 years old, good, with cell spread: 🔧 cell calibration advised |
| Demo 3 | Just installed: collecting data for the first measurement |
| Demo 4 | 6.5 years old, below spec (orange) |
| Demo 5 | 9 years old, just below 75 %: report to Marstek (red), cells in balance |
| Demo 6 | 2.8 years old, good, but no new data for a while (⚠) |

### 1 battery

![1 battery](../screenshots/gallery/1-battery.png)
![1 battery with chart](../screenshots/gallery/1-battery-chart.png)

### 2 batteries

![2 batteries](../screenshots/gallery/2-batteries.png)
![2 batteries with charts](../screenshots/gallery/2-batteries-chart.png)

### 3 batteries

![3 batteries](../screenshots/gallery/3-batteries.png)
![3 batteries with charts](../screenshots/gallery/3-batteries-chart.png)

### 4 batteries

![4 batteries](../screenshots/gallery/4-batteries.png)
![4 batteries with charts](../screenshots/gallery/4-batteries-chart.png)

### 5 batteries

![5 batteries](../screenshots/gallery/5-batteries.png)
![5 batteries with charts](../screenshots/gallery/5-batteries-chart.png)

### 6 batteries

![6 batteries](../screenshots/gallery/6-batteries.png)
![6 batteries with charts](../screenshots/gallery/6-batteries-chart.png)

## Trying a demo yourself

The cards accept fake data with the `demo` option (for button-card: the `demo` variable); the gallery above was made with it. That data lives only in the dashboard configuration: no sensors are created and nothing goes into your history. You do not need this for normal use.
