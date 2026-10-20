# Troubleshooting

*[Nederlands](04-troubleshooting.nl.md)*

| What you see | Why | What to do |
|---|---|---|
| **"No full discharge measured yet"** | The battery has not gone from 95 % or higher down to 15 % or lower since monitoring started. In autumn and winter that can take a while. | Nothing is wrong. For a quick first measurement, let the battery charge fully once and then run down completely. |
| **The scan finds no battery** | The scan looks for a state-of-charge sensor (%) and a power sensor with "battery power" in its name, on the same device or with the same name prefix. Some integrations use other names. | Choose **Choose sensors manually** and pick the two sensors yourself. |
| **Warning: "looks like the AC / grid side"** | The chosen power sensor has "ac", "grid", "net", "p1" or "meter" in its name. AC values include conversion losses and give a wrong capacity. | Pick the battery (DC) power sensor. Only if you are sure it is the DC side: submit again to use it anyway. |
| **Notification: "plus and minus reversed automatically"** | Your power sensor shows charging as a negative value. The monitor noticed this on the first full charge or discharge and corrected it. | Nothing. If detection got it wrong, set the sign manually under **Configure**. |
| **A measurement seems missing after a restart** | If the power data has a gap of more than 5 minutes during a charge or discharge (for example a Home Assistant restart), that swing is not used. | Nothing; the next full discharge counts again. |
| **Percentage above 100 %** | The internal reserve does not match your battery: the usable band is set too small. | Check down to which percentage your battery goes on a full discharge and adjust the reserve. See [Supported batteries](05-supported-batteries.md#depth-of-discharge-per-model). |
| **Statistics graph on the standard card is empty** | Home Assistant builds long-term statistics per hour; monthly averages appear after the first measurements. | Wait a few days; the overview card shows values right away. |
| **button-card shows a red "sensor.marstek_… ?"** | The battery id in the card does not match the id you chose (e.g. `mt1`). | Use the same id in the card as when adding the battery. |

Removing a battery from the integration keeps its measurements in `.storage/`, so they can still support a report to Marstek. To start over on purpose, use the action `marstek_capacity_monitor.reset_measurements`.
