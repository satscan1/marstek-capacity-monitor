# Community data

Anonymous reports that users shared with the **Share data** form (Issues → New issue → Share data). Each file is the anonymous form of the monitor's report: no names, no sensor names, no installation ids; installation date as year and month only. The data is embedded in each file (`<script type="application/json" id="mcm-data">`), in the export format described in `custom_components/marstek_capacity_monitor/export.py` (field `schema` = version of the format).

Used to see what is normal across many batteries: wear per year, cell spread, the difference between versions, the effect of cold.
