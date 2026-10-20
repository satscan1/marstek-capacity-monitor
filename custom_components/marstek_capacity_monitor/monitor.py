"""Per-battery runtime: listens to the sensors, keeps state, stores records."""

from __future__ import annotations

from datetime import date, datetime, timedelta
import logging
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, UnitOfPower
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, State, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .calc import MAX_RECORDS, BatterySpec, SwingTracker, evaluate
from .const import (
    CONF_CYCLE_EOL,
    CONF_CYCLE_LIFE,
    CONF_INITIAL_CYCLES,
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
    EVENT_SESSION,
    RECALC_SECONDS,
    SAVE_DELAY_SECONDS,
    SIGNAL_UPDATE,
    SIGN_AUTO,
    SIGN_NEGATIVE,
    STORAGE_VERSION,
    TICK_SECONDS,
)

_LOGGER = logging.getLogger(__name__)

BAD_STATES = (STATE_UNAVAILABLE, STATE_UNKNOWN, "none", "")


def entry_setting(entry: ConfigEntry, key: str) -> Any:
    """Options override data, data overrides defaults."""
    if key in entry.options:
        return entry.options[key]
    if key in entry.data:
        return entry.data[key]
    return DEFAULTS.get(key)


def spec_from_entry(entry: ConfigEntry) -> BatterySpec:
    raw_date = entry_setting(entry, CONF_PURCHASE_DATE)
    purchase = None
    if raw_date:
        try:
            purchase = date.fromisoformat(str(raw_date)[:10])
        except ValueError:
            _LOGGER.warning("Invalid purchase date %s", raw_date)
    return BatterySpec(
        nominal_kwh=float(entry_setting(entry, CONF_NOMINAL_KWH)),
        reserve_kwh=float(entry_setting(entry, CONF_RESERVE_KWH)),
        purchase_date=purchase,
        warranty_years=float(entry_setting(entry, CONF_WARRANTY_YEARS)),
        red_pct=float(entry_setting(entry, CONF_RED_PCT)),
        tolerance_pct=float(entry_setting(entry, CONF_TOLERANCE_PCT)),
        cycle_life=float(entry_setting(entry, CONF_CYCLE_LIFE)),
        cycle_eol_pct=float(entry_setting(entry, CONF_CYCLE_EOL)),
        initial_cycles=float(entry_setting(entry, CONF_INITIAL_CYCLES)),
    )


class BatteryMonitor:
    """Runtime object for one configured battery."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.spec = spec_from_entry(entry)
        self.soc_entity: str = entry.data[CONF_SOC_ENTITY]
        self.power_entity: str = entry.data[CONF_POWER_ENTITY]
        self.sign_mode: str = entry_setting(entry, CONF_POWER_SIGN) or SIGN_AUTO
        self._store: Store = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}"
        )
        self.tracker = self._new_tracker()
        self.records: list[dict[str, Any]] = []
        self.result: dict[str, Any] = {}
        self.last_session: dict[str, Any] | None = None
        self._unsubs: list = []

    @property
    def signal(self) -> str:
        return SIGNAL_UPDATE.format(self.entry.entry_id)

    async def async_start(self) -> None:
        data = await self._store.async_load()
        if data:
            self.tracker = self._new_tracker(data.get("tracker"))
            self.records = data.get("records", [])
            # Any time spent while HA was down is a gap: never integrate it.
            self.tracker.s["power_w"] = None
            self.tracker.s["power_ts"] = None
            self.tracker._invalidate_swing("restart")  # noqa: SLF001
        self._recalculate()

        self._unsubs.append(
            async_track_state_change_event(
                self.hass, [self.power_entity], self._on_power
            )
        )
        self._unsubs.append(
            async_track_state_change_event(self.hass, [self.soc_entity], self._on_soc)
        )
        self._unsubs.append(
            async_track_time_interval(
                self.hass, self._on_tick, timedelta(seconds=TICK_SECONDS)
            )
        )
        self._unsubs.append(
            async_track_time_interval(
                self.hass, self._on_recalc, timedelta(seconds=RECALC_SECONDS)
            )
        )
        # Seed with current values
        self._handle_power(self.hass.states.get(self.power_entity))
        self._handle_soc(self.hass.states.get(self.soc_entity))

    async def async_stop(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        await self._store.async_save(self._data())

    async def async_reset(self) -> None:
        """Forget all measurements of this battery (service call)."""
        self.records = []
        self.tracker = self._new_tracker()
        await self._store.async_save(self._data())
        self._recalculate()

    # -- helpers ------------------------------------------------------------

    def _new_tracker(self, state: dict[str, Any] | None = None) -> SwingTracker:
        auto = self.sign_mode == SIGN_AUTO
        tracker = SwingTracker(state, auto_sign=auto)
        if not auto:
            # The user fixed the sign: forget anything learned automatically.
            tracker.s["sign"] = 1
            tracker.s["sign_flipped"] = False
        return tracker

    @property
    def power_sign_state(self) -> str:
        """Human-readable state of the sign detection (diagnostics)."""
        if self.sign_mode != SIGN_AUTO:
            return self.sign_mode
        if not self.tracker.s.get("sign_confirmed"):
            return "auto_pending"
        return "auto_reversed" if self.tracker.s.get("sign_flipped") else "auto_normal"

    def _data(self) -> dict[str, Any]:
        return {"tracker": self.tracker.s, "records": self.records}

    @staticmethod
    def _now_ts() -> float:
        return dt_util.utcnow().timestamp()

    def _power_w(self, state: State | None) -> float | None:
        if state is None or state.state in BAD_STATES:
            return None
        try:
            value = float(state.state)
        except ValueError:
            return None
        unit = state.attributes.get("unit_of_measurement")
        if unit == UnitOfPower.KILO_WATT:
            value *= 1000
        elif unit == UnitOfPower.MEGA_WATT:
            value *= 1_000_000
        return -value if self.sign_mode == SIGN_NEGATIVE else value

    @staticmethod
    def _soc(state: State | None) -> float | None:
        if state is None or state.state in BAD_STATES:
            return None
        try:
            value = float(state.state)
        except ValueError:
            return None
        return value if 0 <= value <= 100 else None

    def _recalculate(self) -> None:
        self.result = evaluate(
            self.spec,
            self.records,
            self.tracker.cumulative_discharge_kwh,
            dt_util.now().replace(tzinfo=None),
        )
        async_dispatcher_send(self.hass, self.signal)

    # -- event handlers -----------------------------------------------------

    def _handle_power(self, state: State | None) -> None:
        self.tracker.update_power(self._power_w(state), self._now_ts())
        self._store.async_delay_save(self._data, SAVE_DELAY_SECONDS)

    def _handle_soc(self, state: State | None) -> None:
        soc = self._soc(state)
        if soc is None:
            return
        record = self.tracker.update_soc(soc, self._now_ts())
        if record is None:
            self._store.async_delay_save(self._data, SAVE_DELAY_SECONDS)
            return
        self.records.append(record)
        del self.records[:-MAX_RECORDS]
        self.last_session = record
        self.hass.async_create_task(self._store.async_save(self._data()))
        self.hass.bus.async_fire(
            EVENT_SESSION,
            {"entry_id": self.entry.entry_id, "name": self.entry.title, **record},
        )
        _LOGGER.debug("%s: session recorded %s", self.entry.title, record)
        if record.get("sign_corrected"):
            _LOGGER.warning(
                "%s: %s reports charging as negative; the sign was reversed "
                "automatically",
                self.entry.title,
                self.power_entity,
            )
            persistent_notification.async_create(
                self.hass,
                f"**{self.entry.title}**: `{self.power_entity}` shows charging as a "
                "negative value. Marstek Capacity Monitor has reversed the sign "
                "automatically, no action needed.\n\n"
                f"**{self.entry.title}**: `{self.power_entity}` toont laden als "
                "negatief getal. Marstek Capacity Monitor heeft plus en min "
                "automatisch omgedraaid, je hoeft niets te doen.",
                title="Marstek Capacity Monitor",
                notification_id=f"{DOMAIN}_sign_{self.entry.entry_id}",
            )
        self._recalculate()

    @callback
    def _on_power(self, event: Event[EventStateChangedData]) -> None:
        self._handle_power(event.data["new_state"])

    @callback
    def _on_soc(self, event: Event[EventStateChangedData]) -> None:
        self._handle_soc(event.data["new_state"])

    @callback
    def _on_tick(self, _now: datetime) -> None:
        self.tracker.tick(self._now_ts())

    @callback
    def _on_recalc(self, _now: datetime) -> None:
        self._recalculate()
