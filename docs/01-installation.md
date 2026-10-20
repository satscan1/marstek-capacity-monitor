# Installation

*[Nederlands](01-installation.nl.md)*

## What you need

Two sensors per battery, which you almost certainly already have:

* the **state of charge** (SOC, %);
* the **DC battery power** (W or kW), measured on the battery side, not the AC / grid side.

You do **not need to create any sensors**. When you add a battery, the integration scans Home Assistant and proposes the matching sensors for each battery.

Which models and integrations work: see [Supported batteries](05-supported-batteries.md).

**You don't have to set plus or minus.** Some integrations report charging as positive, others as negative. On the first full charge or discharge the monitor detects this and reverses the sign if needed. You are notified when that happens. You can also set the sign manually.

## Install the integration

**Via HACS (custom repository)**

1. In HACS, open the three dots → *Custom repositories*. Enter the URL of this repo, type *Integration*.
2. Install **Marstek Capacity Monitor** and restart Home Assistant.

**Manually**

Copy `custom_components/marstek_capacity_monitor` to `/config/custom_components/` and restart.

**Adding a battery**

Go to **Settings → Devices & services → Add integration → Marstek Capacity Monitor**.

1. Pick a battery that was found, or choose the sensors yourself.
2. Check the short id (`mt1` … `mt6`), the name and the two sensors.
3. Enter the factory data: nominal capacity, reserve, purchase date, warranty period and cycles. The defaults come from the Venus E datasheet.

## Add the cards

| Folder | Requires | Content |
|---|---|---|
| `dashboard/button-card/` | [button-card](https://github.com/custom-cards/button-card) (HACS) | Overview of up to 6 batteries: per month, trend column first, newest → oldest. Plus a detail card per battery. Set the language with `lang: en` or `nl`. |
| `dashboard/standard/` | nothing | Entities card and statistics graph (remaining capacity vs spec per month) |
