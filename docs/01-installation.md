# Installation

*[Nederlands](01-installation.nl.md) · [Deutsch](01-installation.de.md)*

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
2. Check the short id (`mt1` … `mt6`), the name and the two sensors. Optional: the highest and lowest cell voltage, for the [cell balance check](03-how-it-works.md#cell-balance). These are filled in when the scan finds them.
3. Choose the model and fill in the installation date. For a known model (Venus E v1/v2, v3, 4.0, Max or Pro, Venus C or Venus D) the factory data are filled in for you (Venus D and Venus E Pro: also the number of packs). For another model you enter the factory data yourself.
   A **Venus C** can report the same code as a Venus E v1/v2. Then pick **Venus C** yourself, also when Venus E v1 / v2 is already selected.

You can change all factory data later under **Configure**.

When you add a battery, the tool looks in the Home Assistant history (usually the last 10 days) for a full discharge that already happened. If there is one, you get a first measurement right away. Otherwise the battery shows **collecting data** until its first full discharge (≥ 95 % → ≤ 15 %). The status line on the card tells you the next step.

## Add the cards

From version 0.4.0 the integration has its own cards. You do not need to install anything else: no button-card and no templates. Add at least one battery first. Then restart Home Assistant and refresh the page in your browser (Ctrl+F5, on a Mac Cmd+Shift+R); do the same after every update.

### In the sidebar by itself (from 0.5.1)

After adding the first battery and a restart, **Battery capacity** appears in the sidebar by itself, with all your batteries in it (1 to 6, in the [layout](06-dashboard-gallery.md#layout) of the gallery). Nothing to set up. You cannot change this dashboard; for a layout of your own, make a dashboard yourself as described below.

- **Turn it off:** Settings → Devices & services → Marstek Capacity Monitor → **Configure** → **Menu item in the sidebar**. Off for one battery means the whole menu item disappears.
- **Hidden or in the wrong place?** Long-press **Home Assistant** at the top of the sidebar (or go to your profile → change the sidebar). There you bring items back, hide them or move them. This is per device: set it separately on your phone.
- If you already have a dashboard of your own at `/marstek-capacity`, the monitor leaves it alone.

### Quickest way: dashboard in one click

1. Go to **Settings → Dashboards → Add dashboard**.
2. At the bottom, under **Community dashboards**, pick **Marstek battery capacity**.
3. Give it a name (for example *Battery capacity*) and click **Create**.

The dashboard puts your batteries in the [layout](06-dashboard-gallery.md#layout) of the gallery by itself, for 1 to 6 batteries. If you add a battery later, it appears by itself too.

This choice is in Home Assistant 2026.5 and newer. With an older version: make a **New dashboard from scratch**, open it, click the **pencil**, then the **three dots → Raw configuration editor**, replace everything with these two lines and save:

```yaml
strategy:
  type: custom:marstek-capacity
```

### Single cards in your own dashboard

Open your dashboard, click the **pencil** and then **Add card**. Search for **Marstek**:

- **Marstek capacity (battery)**: one battery, with the chart. Without settings it takes your first battery.
- **Marstek capacity (overview)**: all your batteries per month.

The cards find your batteries, their names and the Home Assistant language by themselves. To change something, use the card's code editor:

```yaml
type: custom:marstek-capacity-card
battery: mt2        # the battery code (see the sensor names, e.g. sensor.marstek_mt2_capacity_pct)
name: Garage        # other name on the card
months: 6           # number of months in the trend
lang: en            # en, nl or de; default is the Home Assistant language
```

For the overview you can choose which batteries it shows: `batteries: [mt1, mt2]`.

How to arrange the cards and what everything on the card means: [06 – Dashboard and gallery](06-dashboard-gallery.md).

### With button-card (as before 0.4.0)

If you already use the button-card cards, they keep working. There is no need to switch, but you can: the new cards look the same.

These cards use [button-card](https://github.com/custom-cards/button-card). Install it first: in HACS search for **button-card** → **Download**, then refresh the page in your browser (Ctrl+F5).

#### Ready-made dashboard with button-card

[`dashboard/ready-made/en/`](../dashboard/ready-made/en/) has a complete dashboard per number of batteries: `1-battery.yaml` up to `6-batteries.yaml`. Everything is in it, in the [layout](06-dashboard-gallery.md#layout) of the gallery.

1. Go to **Settings → Dashboards → Add dashboard → New dashboard from scratch**. Give it a name, for example *Battery capacity*, and open it.
2. Click the **pencil** at the top right, then the **three dots → Raw configuration editor**.
3. Open the file for your number of batteries on GitHub, copy everything (button *Copy raw file*) and paste it over what is in the editor (Ctrl+A, then Ctrl+V).
4. Did you keep the suggested codes `mt1`, `mt2`, … when adding the batteries? Then you do not need to change anything. Otherwise replace them with your own codes; you see them in the sensor names, for example `sensor.marstek_mt1_capacity_pct`. Change the names on the cards at `name:`.
5. Click **Save** and close the editor.

#### In an existing dashboard

1. **Templates (once per dashboard):** open the dashboard, click the **pencil**, then the **three dots → Raw configuration editor**. Copy everything from [`marstek_capacity_templates.yaml`](../dashboard/button-card/marstek_capacity_templates.yaml) and paste it at the very top, above the line `views:`. Is there already a line `button_card_templates:` (from other cards)? Then paste only what is below it, under your existing templates. Save and close the editor.
2. **Cards:** still in edit mode: **Add card** → at the bottom **Manual**. [`examples.yaml`](../dashboard/button-card/examples.yaml) has two examples, separated by a line `---`: first the overview of all your batteries, then the card for one battery. Paste one example at a time, not the whole file. Replace `mt1` everywhere with your own code and save. The text follows the language of Home Assistant; for a fixed language add `lang: en`, `lang: nl` or `lang: de` under `variables`. Repeat this per battery and for the overview.

How to arrange the cards and what everything on the card means: [06 – Dashboard and gallery](06-dashboard-gallery.md).

#### Only Home Assistant standard cards

[`dashboard/standard/`](../dashboard/standard/) has an entities card and a statistics graph (remaining capacity vs spec per month) that work with Home Assistant's standard cards. Add them as in step 2 of *In an existing dashboard*.
