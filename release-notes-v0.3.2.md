*[Nederlands](https://github.com/satscan1/marstek-capacity-monitor/blob/main/README.nl.md)*

## What's new in 0.3.2

**Measurements survive a restart, ready-made dashboards, and no false "no recent data" at night.**

- **Fix:** a Home Assistant restart in the middle of a full discharge no longer throws the measurement away. A restart of up to 10 minutes is bridged: the energy in that gap is estimated from the power just before and just after (usually less than 0.5 % difference).
- **Fix:** a battery standing still (empty or full, around 0 W) no longer shows *No new data · check the battery connection*. Its state of charge and power simply do not change for hours. The status now only appears when the battery was charging or discharging (more than 50 W) and no new value came in for an hour.
- **Fix:** *Reset measurements* gave an error and did nothing.
- **Ready-made dashboards** for 1 to 6 batteries, in English and Dutch: [`dashboard/ready-made/`](https://github.com/satscan1/marstek-capacity-monitor/tree/main/dashboard/ready-made). Make a new dashboard, paste the file into the raw configuration editor and you are done.
- **Installation guide:** step by step how to add the cards, in a new or an existing dashboard: [01 – Installation](https://github.com/satscan1/marstek-capacity-monitor/blob/main/docs/01-installation.md#add-the-cards).

Upgrading: update in HACS and restart Home Assistant. Measurements, settings and cards are unchanged. Full list: [CHANGELOG](https://github.com/satscan1/marstek-capacity-monitor/blob/main/CHANGELOG.md).

## Documentation

| Document | Contents |
|---|---|
| [01 – Installation](https://github.com/satscan1/marstek-capacity-monitor/blob/main/docs/01-installation.md) | What you need, HACS, adding a battery, cards |
| [02 – Configuration](https://github.com/satscan1/marstek-capacity-monitor/blob/main/docs/02-configuration.md) | Settings, sensors, resetting measurements |
| [03 – How it works](https://github.com/satscan1/marstek-capacity-monitor/blob/main/docs/03-how-it-works.md) | Measuring, monitor status, cell balance, spec and colours |
| [04 – Troubleshooting](https://github.com/satscan1/marstek-capacity-monitor/blob/main/docs/04-troubleshooting.md) | Common messages and what to do |
| [05 – Supported batteries](https://github.com/satscan1/marstek-capacity-monitor/blob/main/docs/05-supported-batteries.md) | Connections, factory data per model, **sources for the manufacturer specs** |
| [06 – Dashboard and gallery](https://github.com/satscan1/marstek-capacity-monitor/blob/main/docs/06-dashboard-gallery.md) | Layout for 1 to 6 batteries, the card explained with numbers, screenshots |

## License

[GPL-3.0](https://github.com/satscan1/marstek-capacity-monitor/blob/main/LICENSE)
