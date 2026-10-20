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
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfEnergy
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import MonitorConfigEntry
from .const import CONF_BATTERY_ID, DOMAIN
from .monitor import BatteryMonitor

STATUS_OPTIONS = ["good", "attention", "critical", "no_measurement"]


@dataclass(frozen=True, kw_only=True)
class CapacitySensorDescription(SensorEntityDescription):
    value_fn: Callable[[BatteryMonitor], Any]
    attrs_fn: Callable[[BatteryMonitor], dict[str, Any]] | None = None


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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MonitorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    monitor = entry.runtime_data
    async_add_entities(CapacitySensor(monitor, d) for d in SENSORS)


class CapacitySensor(SensorEntity):
    """One value of one battery."""

    entity_description: CapacitySensorDescription
    _attr_has_entity_name = True
    _attr_should_poll = False
    # Lists are only needed live by the cards; keep them out of the recorder
    # database (lower write load).
    _unrecorded_attributes = frozenset({"trend", "history"})

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
        self.async_on_remove(
            async_dispatcher_connect(self.hass, self._monitor.signal, self._refresh)
        )

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
