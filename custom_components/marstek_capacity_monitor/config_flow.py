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
    CONF_BATTERY_ID,
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
from .discovery import Candidate, find_candidates, looks_like_ac

CONF_CANDIDATE = "candidate"
MANUAL = "manual"

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
        manual = (
            "✎ Zelf sensoren kiezen"
            if (self.hass.config.language or "").startswith("nl")
            else "✎ Choose sensors manually"
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
                return await self.async_step_specs()

        default_id = self._default_id()
        suggested = {
            CONF_BATTERY_ID: default_id,
            CONF_NAME: default_id.upper(),
            **self._proposal,
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
            }
        )
        return self.async_show_form(
            step_id="details",
            data_schema=self.add_suggested_values_to_schema(schema, suggested),
            errors=errors,
        )

    async def async_step_specs(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_spec(user_input)
            if not errors:
                return self.async_create_entry(
                    title=self._data[CONF_NAME], data={**self._data, **user_input}
                )
        return self.async_show_form(
            step_id="specs",
            data_schema=_spec_schema(user_input or {}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return MarstekCapacityOptionsFlow()


class MarstekCapacityOptionsFlow(OptionsFlow):
    """Change factory data / warranty terms later."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        current = {**self.config_entry.data, **self.config_entry.options}
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_spec(user_input)
            if not errors:
                return self.async_create_entry(data=user_input)
            current.update(user_input)
        schema = _spec_schema(current).extend(
            {
                vol.Required(
                    CONF_POWER_SIGN,
                    default=current.get(CONF_POWER_SIGN, DEFAULTS[CONF_POWER_SIGN]),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=SIGN_MODES, translation_key="power_sign"
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
