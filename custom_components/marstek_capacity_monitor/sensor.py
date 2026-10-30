"""Sensors for Marstek Capacity Monitor."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricPotential,
    UnitOfEnergy,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import MonitorConfigEntry
from .const import CONF_BATTERY_ID, DOMAIN, KIND_CELLS, KIND_SOC, MONITOR_STATUSES
from .health import LEVELS
from .monitor import BatteryMonitor

STATUS_OPTIONS = ["good", "attention", "critical", "no_measurement", "check_model", "unconfirmed", "check_power"]


@dataclass(frozen=True, kw_only=True)
class CapacitySensorDescription(SensorEntityDescription):
    value_fn: Callable[[BatteryMonitor], Any]
    attrs_fn: Callable[[BatteryMonitor], dict[str, Any]] | None = None
    status_only: bool = False  # refreshed on status changes, not on recalcs


def _r(m: BatteryMonitor, key: str) -> Any:
    return m.result.get(key)


SENSORS: tuple[CapacitySensorDescription, ...] = (
    CapacitySensorDescription(
        key="measured_capacity",
        translation_key="measured_capacity",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda m: _r(m, "measured_kwh"),
        attrs_fn=lambda m: {
            k: m.result.get(k)
            for k in (
                "measurement_count",
                "last_measurement",
                "loss_kwh",
                "nominal_kwh",
                "reserve_kwh",
                "usable_kwh",
                "usable_band_pct",
                "trend",
                "history",
            )
        },
    ),
    CapacitySensorDescription(
        key="capacity_pct",
        translation_key="capacity_pct",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:battery-heart-variant",
        value_fn=lambda m: _r(m, "measured_pct"),
        attrs_fn=lambda m: {
            "status": m.result.get("status"),
            "expected_pct": m.result.get("expected_pct"),
            "red_pct": m.result.get("red_pct"),
            "tolerance_pct": m.result.get("tolerance_pct"),
        } | {
            k: m.result.get(k)
            for k in (
                "display_state",
                "baseline_pct",
                "since_start_pct",
                "confirm_count",
                "confirm_needed",
                "drop_ref_pct",
                "spread_pts",
                "impossible_count",
                "impossible_last_pct",
                "impossible_limit_pct",
            )
        },
    ),
    CapacitySensorDescription(
        key="expected_capacity",
        translation_key="expected_capacity",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:chart-line-variant",
        value_fn=lambda m: _r(m, "expected_pct"),
        attrs_fn=lambda m: {
            "cycle_life": m.spec.cycle_life,
            "cycle_eol_pct": m.spec.cycle_eol_pct,
            # Cycles before the monitor; from the battery's own counter (AC
            # side, an estimate) when cycle_counter is set, else entered by hand
            "initial_cycles": m.spec.initial_cycles,
            "cycle_counter": m.cycle_counter,
        } | {
            k: m.result.get(k)
            for k in (
                "expected_kwh",
                "age_years",
                "cycles",
            )
        },
    ),
    CapacitySensorDescription(
        key="margin",
        translation_key="margin",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:plus-minus-variant",
        value_fn=lambda m: _r(m, "margin_kwh"),
    ),
    CapacitySensorDescription(
        key="cycles",
        translation_key="cycles",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        icon="mdi:battery-sync",
        value_fn=lambda m: _r(m, "cycles"),
    ),
    CapacitySensorDescription(
        key="warranty_status",
        translation_key="warranty_status",
        device_class=SensorDeviceClass.ENUM,
        options=STATUS_OPTIONS,
        icon="mdi:shield-check",
        value_fn=lambda m: _r(m, "status"),
        attrs_fn=lambda m: {
            "in_warranty": m.result.get("in_warranty"),
            "warranty_end": m.result.get("warranty_end"),
        },
    ),
    CapacitySensorDescription(
        key="last_full_discharge",
        translation_key="last_full_discharge",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:battery-arrow-down",
        value_fn=lambda m: _r(m, "last_full_discharge"),
    ),
    CapacitySensorDescription(
        key="last_full_charge",
        translation_key="last_full_charge",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:battery-arrow-up",
        value_fn=lambda m: _r(m, "last_full_charge"),
    ),
    CapacitySensorDescription(
        key="nominal_capacity",
        translation_key="nominal_capacity",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=2,
        value_fn=lambda m: _r(m, "nominal_kwh"),
    ),
    CapacitySensorDescription(
        key="usable_capacity",
        translation_key="usable_capacity",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=2,
        value_fn=lambda m: _r(m, "usable_kwh"),
    ),
    CapacitySensorDescription(
        key="red_threshold",
        translation_key="red_threshold",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=2,
        value_fn=lambda m: _r(m, "red_kwh"),
    ),
    CapacitySensorDescription(
        key="warranty_end",
        translation_key="warranty_end",
        device_class=SensorDeviceClass.DATE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda m: _r(m, "warranty_end"),
    ),
    CapacitySensorDescription(
        key="dc_discharged",
        translation_key="dc_discharged",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=1,
        value_fn=lambda m: round(m.tracker.cumulative_discharge_kwh, 3),
        attrs_fn=lambda m: {
            "power_entity": m.power_entity,
            "soc_entity": m.soc_entity,
            "power_sign": m.power_sign_state,
        },
    ),
)


STATUS_SENSOR = CapacitySensorDescription(
    key="monitor_status",
    translation_key="monitor_status",
    device_class=SensorDeviceClass.ENUM,
    options=MONITOR_STATUSES,
    icon="mdi:heart-pulse",
    status_only=True,
    value_fn=lambda m: m.status.get("state"),
    attrs_fn=lambda m: {k: v for k, v in m.status.items() if k != "state"}
    | {"version": m.hass.data.get(f"{DOMAIN}_version")},
)

CELL_SENSOR = CapacitySensorDescription(
    key="cell_spread",
    translation_key="cell_spread",
    native_unit_of_measurement=UnitOfElectricPotential.MILLIVOLT,
    device_class=SensorDeviceClass.VOLTAGE,
    state_class=SensorStateClass.MEASUREMENT,
    suggested_display_precision=0,
    icon="mdi:battery-sync-outline",
    value_fn=lambda m: m.cell_result.get("spread_mv"),
    attrs_fn=lambda m: {
        "last_sample": m.cell_result.get("last_sample"),
        "sample_count": m.cell_result.get("sample_count"),
        "trend": m.cell_result.get("trend"),
        "history": m.cell_result.get("history"),
        "cell_max_entity": m.cell_max_entity,
        "cell_min_entity": m.cell_min_entity,
    },
)


def _dt(ts: float | None) -> Any:
    return dt_util.utc_from_timestamp(ts) if ts else None


def _soc_attrs(m: BatteryMonitor) -> dict[str, Any]:
    r = m.soc_result
    return {
        "since": _dt(r.get("since")),
        "count": r.get("count"),
        "last_size": r.get("last_size"),
        "last_calibration": _dt(r.get("last_top")),
        "last_deviation": r.get("last_deviation"),
        "limit_pct": r.get("limit_pct"),
        "sensitivity": r.get("sensitivity", "normal"),
        "dismissed": m.is_dismissed(KIND_SOC),
        "notify": m.notify,
        "trend": r.get("trend", []),
    }


def _cell_attrs(m: BatteryMonitor) -> dict[str, Any]:
    r = m.cell_health
    rest = {t["month"]: t["rest_h"] for t in r.get("rest_trend", [])}
    temp = {t["month"]: t.get("temp_c") for t in m.result.get("trend", [])}
    trend = [
        {**t, "rest_h": rest.get(t["month"]), "temp_c": temp.get(t["month"])}
        for t in m.cell_result.get("trend", [])
    ]
    return {
        "since": _dt(r.get("since")),
        "count": r.get("count"),
        "last_size": r.get("last_size"),
        "base_mv": r.get("base_mv"),
        "limit_mv": r.get("limit_mv"),
        "last_mv": m.cell_result.get("spread_mv"),
        "sensitivity": r.get("sensitivity", "normal"),
        "dismissed": m.is_dismissed(KIND_CELLS),
        "notify": m.notify,
        "trend": trend,
    }


SOC_HEALTH_SENSOR = CapacitySensorDescription(
    key="soc_health",
    translation_key="soc_health",
    device_class=SensorDeviceClass.ENUM,
    options=list(LEVELS),
    icon="mdi:battery-check",
    value_fn=lambda m: m.soc_result.get("level", "ok"),
    attrs_fn=_soc_attrs,
)

CELL_HEALTH_SENSOR = CapacitySensorDescription(
    key="cell_health",
    translation_key="cell_health",
    device_class=SensorDeviceClass.ENUM,
    options=list(LEVELS),
    icon="mdi:scale-balance",
    value_fn=lambda m: m.cell_health.get("level", "ok"),
    attrs_fn=_cell_attrs,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MonitorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    monitor = entry.runtime_data
    descriptions = [*SENSORS, STATUS_SENSOR, SOC_HEALTH_SENSOR]
    if monitor.has_cells:
        descriptions += [CELL_SENSOR, CELL_HEALTH_SENSOR]
    async_add_entities(CapacitySensor(monitor, d) for d in descriptions)


class CapacitySensor(SensorEntity):
    """One value of one battery."""

    entity_description: CapacitySensorDescription
    _attr_has_entity_name = True
    _attr_should_poll = False
    # Lists are only needed live by the cards; keep them out of the recorder
    # database (lower write load).
    _unrecorded_attributes = frozenset({"trend", "history", "last_data_minutes"})

    def __init__(
        self, monitor: BatteryMonitor, description: CapacitySensorDescription
    ) -> None:
        self.entity_description = description
        self._monitor = monitor
        entry = monitor.entry
        battery_id = entry.data[CONF_BATTERY_ID]
        self._attr_unique_id = f"{battery_id}_{description.key}"
        self.entity_id = f"sensor.marstek_{battery_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Marstek Capacity Monitor",
            model="DC capacity monitor",
        )

    async def async_added_to_hass(self) -> None:
        signal = (
            self._monitor.status_signal
            if self.entity_description.status_only
            else self._monitor.signal
        )
        self.async_on_remove(async_dispatcher_connect(self.hass, signal, self._refresh))

    @callback
    def _refresh(self) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self._monitor)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        fn = self.entity_description.attrs_fn
        return fn(self._monitor) if fn else None
