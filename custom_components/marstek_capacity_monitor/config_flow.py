"""Config flow: one config entry per battery, at most six."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    RESTORE_MODES,
    CONF_BATTERY_ID,
    CONF_CELL_MAX_ENTITY,
    CONF_CELL_MIN_ENTITY,
    CONF_MODEL,
    CONF_TEMP_MAX_ENTITY,
    CONF_TEMP_MIN_ENTITY,
    CONF_CELL_SENSITIVITY,
    CONF_CYCLE_COUNTER,
    HIDDEN_OPTIONS,
    CONF_NOTIFY,
    CONF_SIDEBAR,
    CONF_SOC_SENSITIVITY,
    SENSITIVITIES,
    CONF_PACKS,
    MAX_PACKS,
    MODEL_PRESETS,
    MODEL_OTHER,
    PACK_MODELS,
    MODELS,
    MODEL_E_V12,
    preset_for,
    CONF_CYCLE_EOL,
    CONF_CYCLE_LIFE,
    CONF_INITIAL_CYCLES,
    CONF_NAME,
    CONF_NOMINAL_KWH,
    CONF_POWER_ENTITY,
    CONF_POWER_SIGN,
    CONF_PURCHASE_DATE,
    CONF_RESERVE_KWH,
    CONF_SOC_ENTITY,
    CONF_RED_PCT,
    CONF_TOLERANCE_PCT,
    CONF_WARRANTY_YEARS,
    DEFAULTS,
    DOMAIN,
    MAX_BATTERIES,
    SIGN_MODES,
)
from .discovery import (
    Candidate,
    find_candidates,
    counter_kwh,
    find_cell_sensors,
    find_discharge_counter,
    guess_model,
    looks_like_ac,
)
from .extras import FLOW_NOTE, lang_of, start_cycles

CONF_CANDIDATE = "candidate"
MANUAL = "manual"
MANUAL_LABEL = {
    "en": "✎ Choose sensors manually",
    "nl": "✎ Zelf sensoren kiezen",
    "de": "✎ Sensoren selbst wählen",
}

SLUG_RE = re.compile(r"^[a-z0-9_]{1,20}$")


def _num(min_v: float, max_v: float, step: float, unit: str | None = None):
    cfg = selector.NumberSelectorConfig(
        min=min_v, max=max_v, step=step, mode=selector.NumberSelectorMode.BOX
    )
    if unit:
        cfg["unit_of_measurement"] = unit
    return selector.NumberSelector(cfg)


def _spec_schema(values: dict[str, Any]) -> vol.Schema:
    def d(key: str) -> Any:
        return values.get(key, DEFAULTS.get(key))

    purchase = values.get(CONF_PURCHASE_DATE)
    purchase_key = (
        vol.Required(CONF_PURCHASE_DATE, default=purchase)
        if purchase
        else vol.Required(CONF_PURCHASE_DATE)
    )
    return vol.Schema(
        {
            vol.Required(CONF_NOMINAL_KWH, default=d(CONF_NOMINAL_KWH)): _num(
                0.1, 100, 0.01, "kWh"
            ),
            vol.Required(CONF_RESERVE_KWH, default=d(CONF_RESERVE_KWH)): _num(
                0, 50, 0.01, "kWh"
            ),
            purchase_key: selector.DateSelector(),
            vol.Required(CONF_WARRANTY_YEARS, default=d(CONF_WARRANTY_YEARS)): _num(
                1, 30, 0.5, "y"
            ),
            vol.Required(CONF_CYCLE_LIFE, default=d(CONF_CYCLE_LIFE)): _num(
                100, 20000, 100
            ),
            vol.Required(CONF_CYCLE_EOL, default=d(CONF_CYCLE_EOL)): _num(
                1, 100, 1, "%"
            ),
            vol.Required(CONF_INITIAL_CYCLES, default=d(CONF_INITIAL_CYCLES)): _num(
                0, 20000, 0.1
            ),
            vol.Required(CONF_RED_PCT, default=d(CONF_RED_PCT)): _num(1, 100, 1, "%"),
            vol.Required(CONF_TOLERANCE_PCT, default=d(CONF_TOLERANCE_PCT)): _num(
                0, 50, 0.5, "%"
            ),
        }
    )


def _volt_selector() -> selector.EntitySelector:
    return selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor", device_class="voltage")
    )


def _temp_selector() -> selector.EntitySelector:
    return selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
    )


OPTIONAL_SENSORS = (
    (CONF_CELL_MAX_ENTITY, _volt_selector),
    (CONF_CELL_MIN_ENTITY, _volt_selector),
    (CONF_TEMP_MAX_ENTITY, _temp_selector),
    (CONF_TEMP_MIN_ENTITY, _temp_selector),
)


def _cell_fields(values: dict[str, Any]) -> dict[Any, Any]:
    """Optional cell voltage (cell balance) and cell temperature sensors."""
    fields: dict[Any, Any] = {}
    for key, make in OPTIONAL_SENSORS:
        current = values.get(key)
        marker = (
            vol.Optional(key, description={"suggested_value": current})
            if current
            else vol.Optional(key)
        )
        fields[marker] = make()
    return fields


def _validate_cells(data: dict[str, Any]) -> dict[str, str]:
    has_max = bool(data.get(CONF_CELL_MAX_ENTITY))
    has_min = bool(data.get(CONF_CELL_MIN_ENTITY))
    if has_max != has_min:
        return {CONF_CELL_MAX_ENTITY if not has_max else CONF_CELL_MIN_ENTITY: "cells_both"}
    if has_max and data[CONF_CELL_MAX_ENTITY] == data[CONF_CELL_MIN_ENTITY]:
        return {CONF_CELL_MIN_ENTITY: "same_entity"}
    return {}


def _validate_spec(data: dict[str, Any]) -> dict[str, str]:
    errors: dict[str, str] = {}
    if data[CONF_RESERVE_KWH] >= data[CONF_NOMINAL_KWH]:
        errors[CONF_RESERVE_KWH] = "reserve_too_large"
    return errors


class MarstekCapacityConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add a battery."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._candidates: list[Candidate] = []
        self._proposal: dict[str, Any] = {}
        self._ac_confirmed: str | None = None

    def _default_id(self) -> str:
        used = {e.unique_id for e in self._async_current_entries()}
        return next(
            (f"mt{i}" for i in range(1, MAX_BATTERIES + 1) if f"mt{i}" not in used),
            "mt1",
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: propose batteries found in Home Assistant."""
        existing = self._async_current_entries()
        if len(existing) >= MAX_BATTERIES:
            return self.async_abort(reason="max_batteries")

        if user_input is None:
            configured = {e.data.get(CONF_SOC_ENTITY) for e in existing}
            self._candidates = find_candidates(self.hass, exclude_soc=configured)
            if not self._candidates:
                return await self.async_step_details()
        else:
            choice = user_input[CONF_CANDIDATE]
            if choice != MANUAL:
                cand = self._candidates[int(choice)]
                self._proposal = {
                    CONF_NAME: cand.name,
                    CONF_SOC_ENTITY: cand.soc_entity,
                    CONF_POWER_ENTITY: cand.power_entity,
                }
            return await self.async_step_details()

        options = [
            selector.SelectOptionDict(
                value=str(i), label=f"{c.name}  ({c.soc_entity} + {c.power_entity})"
            )
            for i, c in enumerate(self._candidates)
        ]
        manual = MANUAL_LABEL.get(
            (self.hass.config.language or "en")[:2], MANUAL_LABEL["en"]
        )
        options.append(selector.SelectOptionDict(value=MANUAL, label=manual))
        schema = vol.Schema(
            {
                vol.Required(CONF_CANDIDATE, default="0"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options, mode=selector.SelectSelectorMode.LIST
                    )
                )
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            description_placeholders={
                "count": str(len(self._candidates)),
                "max": str(MAX_BATTERIES),
            },
        )

    async def async_step_details(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2: id, name and the two sensors (pre-filled when found)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            battery_id = user_input[CONF_BATTERY_ID].strip().lower()
            power = user_input[CONF_POWER_ENTITY]
            if not SLUG_RE.match(battery_id):
                errors[CONF_BATTERY_ID] = "invalid_id"
            elif user_input[CONF_SOC_ENTITY] == power:
                errors[CONF_POWER_ENTITY] = "same_entity"
            elif cell_errors := _validate_cells(user_input):
                errors.update(cell_errors)
            elif looks_like_ac(self.hass, power) and self._ac_confirmed != power:
                # Warn once; submitting again with the same sensor accepts it.
                self._ac_confirmed = power
                errors[CONF_POWER_ENTITY] = "looks_like_ac"
            else:
                # raise_on_progress=False: an earlier, abandoned attempt with the
                # same id must not block a new one.
                await self.async_set_unique_id(battery_id, raise_on_progress=False)
                self._abort_if_unique_id_configured()
                self._data = {**user_input, CONF_BATTERY_ID: battery_id}
                return await self.async_step_model()

        default_id = self._default_id()
        cells: dict[str, Any] = {}
        if soc := self._proposal.get(CONF_SOC_ENTITY):
            found = find_cell_sensors(self.hass, soc)
            if "max" in found and "min" in found:
                cells = {
                    CONF_CELL_MAX_ENTITY: found["max"],
                    CONF_CELL_MIN_ENTITY: found["min"],
                }
            if "temp_max" in found:
                cells[CONF_TEMP_MAX_ENTITY] = found["temp_max"]
            if "temp_min" in found:
                cells[CONF_TEMP_MIN_ENTITY] = found["temp_min"]
        suggested = {
            CONF_BATTERY_ID: default_id,
            CONF_NAME: default_id.upper(),
            **self._proposal,
            **cells,
            **(user_input or {}),
        }
        schema = vol.Schema(
            {
                vol.Required(CONF_BATTERY_ID): str,
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_SOC_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(CONF_POWER_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="power")
                ),
                **{vol.Optional(key): make() for key, make in OPTIONAL_SENSORS},
            }
        )
        return self.async_show_form(
            step_id="details",
            data_schema=self.add_suggested_values_to_schema(schema, suggested),
            errors=errors,
        )

    async def async_step_model(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 3: which Marstek, installed when. Factory data follow from
        the model, so for a known model this is the last step."""
        if user_input is not None:
            model = user_input[CONF_MODEL]
            self._data[CONF_MODEL] = model
            self._data[CONF_PURCHASE_DATE] = user_input[CONF_PURCHASE_DATE]
            if model in PACK_MODELS:
                return await self.async_step_packs()
            if model == MODEL_OTHER:
                return await self.async_step_specs()
            return self._create(preset_for(model))

        guess = guess_model(self.hass, self._data[CONF_SOC_ENTITY]) or MODEL_E_V12
        schema = vol.Schema(
            {
                vol.Required(CONF_MODEL, default=guess): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=MODELS,
                        translation_key="model",
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
                vol.Required(CONF_PURCHASE_DATE): selector.DateSelector(),
            }
        )
        counter = find_discharge_counter(self.hass, self._data[CONF_SOC_ENTITY])
        kwh = counter_kwh(self.hass, counter)
        note = ""
        if counter and kwh:
            lang = lang_of(self.hass.config.language)
            shown = f"{kwh:,.1f}"
            if lang in ("nl", "de"):
                shown = shown.replace(",", "_").replace(".", ",").replace("_", ".")
            note = "\n\n" + FLOW_NOTE[lang].format(entity=counter, kwh=shown)
        return self.async_show_form(
            step_id="model",
            data_schema=schema,
            description_placeholders={"name": self._data[CONF_NAME], "counter": note},
        )

    async def async_step_packs(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Venus D / Venus E Pro: capacity depends on the number of packs."""
        model = self._data[CONF_MODEL]
        if user_input is not None:
            packs = int(user_input[CONF_PACKS])
            self._data[CONF_PACKS] = packs
            return self._create(preset_for(model, packs))
        schema = vol.Schema(
            {vol.Required(CONF_PACKS, default=1): _num(1, MAX_PACKS, 1)}
        )
        per_pack = MODEL_PRESETS[model][CONF_NOMINAL_KWH]
        lang = (self.hass.config.language or "en")[:2]
        kwh = f"{per_pack:.2f}".replace(".", "," if lang in ("nl", "de") else ".")
        return self.async_show_form(
            step_id="packs",
            data_schema=schema,
            description_placeholders={
                "model": "Venus D" if model == "venus_d" else "Venus E Pro",
                "kwh": kwh,
            },
        )

    def _with_counter(self, data: dict[str, Any]) -> dict[str, Any]:
        """Cycles before the monitor from the battery's own discharge counter
        (AC side, an estimate), unless a start value was entered."""
        if float(data.get(CONF_INITIAL_CYCLES) or 0):
            return data
        counter = find_discharge_counter(self.hass, data[CONF_SOC_ENTITY])
        kwh = counter_kwh(self.hass, counter)
        if counter and kwh:
            usable = float(data[CONF_NOMINAL_KWH]) - float(data[CONF_RESERVE_KWH])
            data = {
                **data,
                CONF_INITIAL_CYCLES: start_cycles(kwh, usable),
                CONF_CYCLE_COUNTER: counter,
            }
        return data

    def _create(self, preset: dict[str, Any]) -> ConfigFlowResult:
        data = {
            **{k: v for k, v in DEFAULTS.items() if k != CONF_POWER_SIGN},
            **preset,
            **self._data,
        }
        return self.async_create_entry(
            title=self._data[CONF_NAME], data=self._with_counter(data)
        )

    async def async_step_specs(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Other model: enter the factory data yourself."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_spec(user_input)
            if not errors:
                return self.async_create_entry(
                    title=self._data[CONF_NAME],
                    data=self._with_counter({**self._data, **user_input}),
                )
        values = {CONF_PURCHASE_DATE: self._data.get(CONF_PURCHASE_DATE), **(user_input or {})}
        return self.async_show_form(
            step_id="specs",
            data_schema=_spec_schema(values),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return MarstekCapacityOptionsFlow()


def _sensitivity_selector() -> selector.SelectSelector:
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=SENSITIVITIES,
            translation_key="sensitivity",
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


class MarstekCapacityOptionsFlow(OptionsFlow):
    """Change factory data / warranty terms later, or restore a back-up."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return self.async_show_menu(step_id="init", menu_options=["settings", "restore"])

    async def async_step_restore(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Restore a back-up (0.5.5): the report file (or JSON) of the
        monitor. Merge keeps everything from both; replace makes the file win.
        A full back-up of the current data is always written first."""
        errors: dict[str, str] = {}
        if user_input is not None:
            from homeassistant.components.file_upload import process_uploaded_file

            from .export import ExportError

            def _read() -> str:
                with process_uploaded_file(self.hass, user_input["file"]) as path:
                    return path.read_text(encoding="utf-8")

            monitor = getattr(self.config_entry, "runtime_data", None)
            try:
                text = await self.hass.async_add_executor_job(_read)
                if monitor is None:
                    raise ExportError("not running")
                done = await monitor.async_restore(text, user_input["mode"])
            except ExportError:
                errors["base"] = "restore_invalid"
            except (OSError, UnicodeDecodeError, ValueError):
                errors["base"] = "restore_unreadable"
            else:
                return self.async_abort(
                    reason="restored",
                    description_placeholders={"records": str(done["records"]), "full": str(done["full"])},
                )
        schema = vol.Schema(
            {
                vol.Required("file"): selector.FileSelector(
                    selector.FileSelectorConfig(accept=".html,.htm,.json")
                ),
                vol.Required("mode", default="merge"): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=RESTORE_MODES, translation_key="restore_mode")
                ),
            }
        )
        return self.async_show_form(step_id="restore", data_schema=schema, errors=errors)

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        current = {**self.config_entry.data, **self.config_entry.options}
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_spec(user_input) or _validate_cells(user_input)
            if not errors:
                # Clearing an optional field must clear it, not keep the old one
                for key, _make in OPTIONAL_SENSORS:
                    user_input.setdefault(key, "")
                # Keep what the form does not show (counter, declined extras)
                kept = {
                    k: v for k, v in self.config_entry.options.items() if k in HIDDEN_OPTIONS
                }
                # A changed start value is the user's own, no longer the counter's
                if float(user_input[CONF_INITIAL_CYCLES]) != float(
                    current.get(CONF_INITIAL_CYCLES) or 0
                ):
                    kept[CONF_CYCLE_COUNTER] = ""
                return self.async_create_entry(data={**kept, **user_input})
            current.update(user_input)
        schema = _spec_schema(current).extend(_cell_fields(current)).extend(
            {
                vol.Required(
                    CONF_POWER_SIGN,
                    default=current.get(CONF_POWER_SIGN, DEFAULTS[CONF_POWER_SIGN]),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=SIGN_MODES, translation_key="power_sign"
                    )
                ),
                vol.Required(
                    CONF_NOTIFY,
                    default=bool(current.get(CONF_NOTIFY, DEFAULTS[CONF_NOTIFY])),
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_SIDEBAR,
                    default=bool(current.get(CONF_SIDEBAR, DEFAULTS[CONF_SIDEBAR])),
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_SOC_SENSITIVITY,
                    default=current.get(CONF_SOC_SENSITIVITY, DEFAULTS[CONF_SOC_SENSITIVITY]),
                ): _sensitivity_selector(),
                vol.Required(
                    CONF_CELL_SENSITIVITY,
                    default=current.get(CONF_CELL_SENSITIVITY, DEFAULTS[CONF_CELL_SENSITIVITY]),
                ): _sensitivity_selector(),
            }
        )
        return self.async_show_form(step_id="settings", data_schema=schema, errors=errors)
