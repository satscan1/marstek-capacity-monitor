# 07 – How the monitor measures

*[Nederlands](07-measuring-method.nl.md) · [Deutsch](07-measuring-method.de.md)*

## What is 100 %?

**100 % is what the manufacturer says is usable: the capacity on the rating plate minus the fixed reserve (depth of discharge).**

Example with a Venus E of 5.12 kWh and a reserve of 11 %:

| | kWh | % |
|---|---|---|
| Rating plate | 5.12 | |
| Fixed reserve (11 %) | − 0.56 | |
| **Usable according to spec** | **4.56** | **100 %** |
| Measured by the monitor | 4.87 | 106.7 % |

### How the monitor gets that number
The monitor measures a full discharge: start at 95 % or higher, end at 15 % or lower. So it does not need to go from exactly 100 to 0. It scales the measured energy to the whole usable part and puts that next to the spec. In the example that came to 4.87 kWh: a bit more than promised.

### Why the Marstek app shows a different number
The app shows for example 5.59 kWh for a charge from 11 to 100 %. That is measured on the **AC side**: what goes into the battery, including the losses of inverter and charging. The monitor measures on the **DC side**: what really comes out of the battery. The app number is therefore always higher. You cannot compare the two.

### Why recharging makes a measurement invalid
A measurement is one discharge in one go, from 95 % or higher to 15 % or lower. If the battery recharges 3 percentage points or more on the way (sun, an automation or EMS), that measurement stops and does not count. Charging costs more energy per percent than discharging delivers. If you mix the two, you cannot determine cleanly how much really came out of the battery. More on this below.

## Can capacity be measured when the battery charges in between?

The monitor only measures during a full discharge (from 95 % or more down to 15 % or less). Couldn't it be smarter, by separating charging and discharging in between? To find out, almost a year of data from two Venus E batteries was analysed (December 2025 – October 2026). Conclusion: technically it is possible, but you don't get a reliable capacity measurement that way. The limitation lies in the battery's own state-of-charge (SOC) meter.

### AC or DC doesn't matter here
The monitor measures on the battery side (DC). As a check: in every full discharge, AC out divided by DC out was consistently 0.84–0.87. So the DC measurement is correct.

### What the data shows
- **Adding up charging and discharging (net) is inaccurate.** In the middle range, charging takes about 54 Wh per percent, while discharging delivers about 50 Wh. Mix the two and the error is as large as the wear you are looking for (about 3 % in a year and a half for the test batteries).
- **Counting only the discharge segments is too noisy.** Even in quiet months, the middle range varies from week to week between 46 and 53 Wh per percent. That is ± 5 %, while wear is 1.5–2 % per year.
- **The battery always reports 5.12 kWh as its total capacity**, even a unit that is more than two years old. So one percent is whatever the battery itself calls one percent, not a fixed amount of energy from the cells.
- **The SOC meter can shift for weeks.** From late March to late April, one battery delivered 15–30 % less energy per percent. This applied both in the middle range and over a full discharge (3.1–3.9 kWh instead of about 4.2). The AC measurement confirmed it. Afterwards it was back to normal.

### Why there is no good solution (yet)
A clean measurement needs two real reference points: truly full and truly empty. Full works, because the battery corrects its own counter there. Empty doesn't: the battery stops at the discharge limit set in the app, which is a SOC percentage, not a voltage. And in the middle range, the LiFePO4 voltage curve is too flat to serve as a reference point.

### What the monitor does instead
It only measures full discharges and shows the median of the last three. A measurement gets an open dot (less reliable) when there was no recent reference point, when the cells were cold, or when the edges behave unusually. It remains a tool, not proof, but it is the best that can be done with the battery's SOC.

## Why a battery can come out above 100 %

Marstek rates the capacity on the rating plate at 3.2 V per cell: 16 cells × 3.2 V × 100 Ah = 5.12 kWh. In reality the voltage during a discharge is around 52–53 V. So about 2 % more energy comes out per percent than the rating plate says. That is a convention of the calculation, not a hidden reserve: you already get that energy. It is the same for everyone and stays the same, so it makes no difference for the drop over time. That is why the monitor deliberately does not correct for it. On top of that, new cells often deliver a little more than the rating plate.

The real reserve is the depth of discharge: the battery uses about 90 % of its cells (some units 88 %). The bottom part stays unused.

## How sure is the value on the card?

- **Above 100 %:** grey with "provisional" until **5 measurements in a row** are above 100 %, no more than 3 points apart. Then green with "above new".
- **Suddenly more than 5 points lower:** grey with "not confirmed yet". Real wear is slow; a jump like this is nearly always an SOC meter that shifted for a while (see above). If the lower value holds for 5 measurements in a row, it counts as real. If it recovers, the note goes away by itself.
- **Since monitoring began:** the change against the middle of the first 3 measurements of this monitor. So it does not matter whether a battery started at 96 % or at 105 %.
