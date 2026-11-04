
**Repair release.** No change to how the monitor measures.

- **Back in the sidebar.** The download of v1.0.1 was packed one folder too deep, so Home Assistant did not find the monitor and *Battery capacity* disappeared from the sidebar. Your measurements were not lost. Update to 1.0.2 and restart Home Assistant. Thanks to dannyro for the report.
- **Model in the settings window.** Batteries added before the monitor asked for the model showed an empty model in the report. Under the gear ⚙ on the card, section Battery, you can now choose the model. It only changes the name and the advice (such as UPS mode); your factory data and measurements stay as they are. The report says where to set it when it is empty, and shows *Other model* instead of a dash.
- **Clearer name for a counter.** *Days completely full* is now *Days charged to 100 %*: such a day calibrates the SOC meter, it is not a capacity measurement. The SOC window says so under the table. Thanks to 3DWim for the question.
- Guide (EN/NL/DE): two new rows in *Troubleshooting*.

