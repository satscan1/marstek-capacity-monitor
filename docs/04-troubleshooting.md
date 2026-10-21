# Troubleshooting

*[Nederlands](04-troubleshooting.nl.md)*

| What you see | Why | What to do |
|---|---|---|
| **"Collecting data"** | The battery has not gone from 95 % or higher down to 15 % or lower since monitoring started. In autumn and winter that can take a while. | Nothing is wrong. For a quick first measurement, let the battery charge fully once and then run down completely. |
| **The scan finds no battery** | The scan looks for a state-of-charge sensor (%) and a power sensor with "battery power" in its name, on the same device or with the same name prefix. Some integrations use other names. | Choose **Choose sensors manually** and pick the two sensors yourself. |
| **Status "No recent data"** | The battery was charging or discharging (more than 50 W), but the state of charge and the power reported no new value for an hour. | Check the battery connection (ESPHome device, Modbus bridge, MQTT). The status returns by itself once data comes in. |
| **Status "Sensor unavailable"** | The state of charge or power sensor is unavailable; the card names it. | Check that integration and the entity. If the entity was renamed, pick it again under **Configure** or add the battery again. |
| **Cell spread stays empty** | A sample needs a full charge (≥ 95 %) and 5 minutes at rest. The next sample needs the battery to drop below 90 % first. | Nothing; it follows after the next full charge. Check that both cell sensors show a voltage (V or mV). |
| **Warning: "looks like the AC / grid side"** | The chosen power sensor has "ac", "grid", "net", "p1" or "meter" in its name. AC values include conversion losses and give a wrong capacity. | Pick the battery (DC) power sensor. Only if you are sure it is the DC side: submit again to use it anyway. |
| **Notification: "plus and minus reversed automatically"** | Your power sensor shows charging as a negative value. The monitor noticed this on the first full charge or discharge and corrected it. | Nothing. If detection got it wrong, set the sign manually under **Configure**. |
| **A measurement seems missing after a restart** | A Home Assistant restart during a discharge is bridged when it takes at most 10 minutes. If it takes longer, or there was no power value just before the restart, that swing is not used. | Nothing; the next full discharge counts again. |
| **Percentage above 100 %** | The internal reserve does not match your battery: the usable band is set too small. | Check down to which percentage your battery goes on a full discharge and adjust the reserve. See [Supported batteries](05-supported-batteries.md#depth-of-discharge-per-model). |
| **Statistics graph on the standard card is empty** | Home Assistant builds long-term statistics per hour; monthly averages appear after the first measurements. | Wait a few days; the overview card shows values right away. |
| **A card shows a red "sensor.marstek_… ?" or "Sensor not found"** | The battery code in the card does not match the code you chose (e.g. `mt1`). | Use the same code in the card as when adding the battery, or leave `battery:` out to take the first battery. |
| **"Custom element doesn't exist: marstek-capacity-card" or the dashboard choice is missing** | The cards are loaded by the integration. That only happens after a restart, with at least one battery added. | Add a battery, restart Home Assistant and refresh the browser (Ctrl+F5). The one-click dashboard needs Home Assistant 2026.5 or newer. |

Removing a battery from the integration keeps its measurements in `.storage/`, so they can still support a report to Marstek. To start over on purpose, use the action `marstek_capacity_monitor.reset_measurements`.
