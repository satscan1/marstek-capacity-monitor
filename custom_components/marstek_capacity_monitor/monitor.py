"""Per-battery runtime: listens to the sensors, keeps state, stores records."""

from __future__ import annotations

from collections import deque
from datetime import date, datetime, timedelta
import json
import logging
from pathlib import Path
from typing import Any
import uuid

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EVENT_HOMEASSISTANT_STOP,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfPower,
)
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, State, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from . import advice, export as mcm_export
from .extras import find_extras
from .health import (
    SocHealthTracker,
    add_events,
    evaluate_cell_health,
    evaluate_soc,
    note_day,
)
from .calc import (
    HISTORY_DAYS,
    MAX_CELL_RECORDS,
    BatterySpec,
    CellBalanceTracker,
    SwingTracker,
    evaluate,
    evaluate_cells,
    is_full_charge,
    is_full_discharge,
    prune_records,
    measurement_phase,
    replay_history,
    to_mv,
)
from .const import (
    CONF_BATTERY_ID,
    CONF_CYCLE_COUNTER,
    CONF_EXTRAS_DECLINED,
    EXTRAS_RECHECK_S,
    CONF_CELL_MAX_ENTITY,
    CONF_CELL_MIN_ENTITY,
    CONF_MODEL,
    CELL_FACTORS,
    CONF_CELL_SENSITIVITY,
    CONF_NOTIFY,
    CONF_SOC_SENSITIVITY,
    EVENT_ADVICE,
    SOC_EVENT_PCT,
    KIND_CELLS,
    KIND_SOC,
    NOTIFY_ACTION_PREFIX,
    CONF_TEMP_MAX_ENTITY,
    CONF_TEMP_MIN_ENTITY,
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
    SIGNAL_STATUS,
    SIGNAL_UPDATE,
    SIGN_AUTO,
    IDLE_POWER_W,
    IMPLAUSIBLE_CLEAR_S,
    MAX_PLAUSIBLE_POWER_W,
    STALE_SECONDS,
    STATUS_COLLECTING,
    STATUS_MEASURING,
    STATUS_NO_RECENT_DATA,
    STATUS_SENSOR_MISSING,
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


BACKUP_DIR = DOMAIN + "/backup"


class MonitorStore(Store):
    """The monitor's own file in .storage, with a safety net.

    When a new version changes how the data is stored (STORAGE_VERSION), the
    old data is first written as a full back-up to
    /config/marstek_capacity_monitor/backup/, then converted. Nothing is lost:
    the back-up can always be restored."""

    monitor: "BatteryMonitor | None" = None

    async def _async_migrate_func(
        self, old_major_version: int, old_minor_version: int, old_data: dict
    ) -> dict:
        if self.monitor is not None:
            try:
                await self.monitor.async_write_backup(
                    old_data, f"before-update-v{old_major_version}.{old_minor_version}"
                )
            except Exception:  # noqa: BLE001 - a failed back-up must never stop the start
                _LOGGER.exception("Back-up before converting the stored data failed")
        return migrate_stored(old_major_version, old_minor_version, old_data)


def migrate_stored(major: int, minor: int, data: dict) -> dict:
    """Convert stored data from an older layout. Version 1 is the first
    layout; add a step here whenever STORAGE_VERSION goes up."""
    return data


class BatteryMonitor:
    """Runtime object for one configured battery."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.spec = spec_from_entry(entry)
        self.soc_entity: str = entry.data[CONF_SOC_ENTITY]
        self.power_entity: str = entry.data[CONF_POWER_ENTITY]
        self.sign_mode: str = entry_setting(entry, CONF_POWER_SIGN) or SIGN_AUTO
        self.model: str | None = entry_setting(entry, CONF_MODEL)
        self.cycle_counter: str | None = entry_setting(entry, CONF_CYCLE_COUNTER) or None
        self.cell_max_entity: str | None = entry_setting(entry, CONF_CELL_MAX_ENTITY) or None
        self.cell_min_entity: str | None = entry_setting(entry, CONF_CELL_MIN_ENTITY) or None
        self.temp_max_entity: str | None = entry_setting(entry, CONF_TEMP_MAX_ENTITY) or None
        self.temp_min_entity: str | None = entry_setting(entry, CONF_TEMP_MIN_ENTITY) or None
        # (ts, lowest, highest) once a minute; 2 days is enough for any swing
        self._temps: deque[tuple[float, float | None, float | None]] = deque(maxlen=2880)
        self.cells = CellBalanceTracker()
        self.cell_records: list[dict[str, Any]] = []
        self.cell_result: dict[str, Any] = evaluate_cells([])
        self.status: dict[str, Any] = {}
        self._history_until: float | None = None
        self._seed_task = None
        self._store: Store = MonitorStore(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}"
        )
        self._store.monitor = self
        # Random, fixed code for the anonymous export (0.5.5): the same battery
        # keeps the same code, without pointing to a person or installation.
        self.share_id: str = uuid.uuid4().hex[:10]
        self.app_version: str = "?"
        self.tracker = self._new_tracker()
        self.records: list[dict[str, Any]] = []
        self.result: dict[str, Any] = {}
        self.last_session: dict[str, Any] | None = None
        self._unsubs: list = []
        # SOC drift and cell calibration (0.5)
        self.notify: bool = bool(entry_setting(entry, CONF_NOTIFY))
        self.health = self._new_health()
        self.soc_events: list[dict[str, Any]] = []
        self.full_days: list[str] = []
        self.alive_days: list[str] = []
        self.soc_since: float | None = None
        self.dismissed: dict[str, float | None] = {}
        self.notified: dict[str, list | None] = {}
        self.soc_result: dict[str, Any] = {"level": "ok", "trend": []}
        self.cell_health: dict[str, Any] = {"level": "ok"}
        self._issues: dict[str, str] = {}
        self._implausible_ts: float | None = None

    @property
    def signal(self) -> str:
        return SIGNAL_UPDATE.format(self.entry.entry_id)

    @property
    def status_signal(self) -> str:
        return SIGNAL_STATUS.format(self.entry.entry_id)

    @property
    def has_cells(self) -> bool:
        return bool(self.cell_max_entity and self.cell_min_entity)

    @property
    def has_temps(self) -> bool:
        return bool(self.temp_max_entity or self.temp_min_entity)

    def _temp_c(self, entity_id: str | None) -> float | None:
        state = self.hass.states.get(entity_id) if entity_id else None
        if state is None or state.state in BAD_STATES:
            return None
        try:
            value = float(state.state)
        except ValueError:
            return None
        if state.attributes.get("unit_of_measurement") == "°F":
            value = (value - 32) * 5 / 9
        return value if -40 <= value <= 100 else None

    def _sample_temps(self) -> None:
        if not self.has_temps:
            return
        lo, hi = self._temp_c(self.temp_min_entity), self._temp_c(self.temp_max_entity)
        if lo is None and hi is None:
            return
        self._temps.append((self._now_ts(), lo, hi))

    def _temps_between(self, start: float, end: float) -> dict[str, float]:
        """Average, lowest and highest cell temperature during a swing."""
        rows = [t for t in self._temps if start <= t[0] <= end]
        if not rows:
            return {}
        mids = [
            (lo + hi) / 2 if lo is not None and hi is not None else (lo if lo is not None else hi)
            for _, lo, hi in rows
        ]
        los = [lo for _, lo, _ in rows if lo is not None] or mids
        his = [hi for _, _, hi in rows if hi is not None] or mids
        return {
            "temp_c": round(sum(mids) / len(mids), 1),
            "temp_min_c": round(min(los), 1),
            "temp_max_c": round(max(his), 1),
        }

    def _apply(self, data: dict[str, Any]) -> None:
        """Take over stored data (start, or a restored back-up)."""
        self.tracker = self._new_tracker(data.get("tracker"))
        self.records = data.get("records", [])
        self.cells = CellBalanceTracker(data.get("cells"))
        self.cell_records = data.get("cell_records", [])
        self.cell_result = evaluate_cells(self.cell_records)
        self.health = self._new_health(data.get("health"))
        self.soc_events = data.get("soc_events", [])
        self.full_days = data.get("full_days", [])
        self.alive_days = data.get("alive_days", [])
        self.soc_since = data.get("soc_since")
        self.dismissed = data.get("dismissed", {})
        self.notified = data.get("notified", {})
        self.share_id = data.get("share_id") or self.share_id

    async def async_start(self) -> None:
        data = await self._store.async_load()
        if data:
            self._apply(data)
            self.health.after_restart()
            # HA was down: a short gap (<= 10 min) is bridged with the average
            # of the power before and after; a longer one invalidates the swing.
            self.tracker.start_after_restart(self._now_ts())
            # Batteries from before 0.4.0 have no flag: never replay for them
            # (their own measurements already cover that period).
            self._history_until = data.get("history_until")
        else:
            # Newly added battery: look in the recorder history for full
            # discharges that happened before now.
            self._history_until = self._now_ts()
        if self._history_until is not None:
            # Tied to the config entry: cancelled on unload or reload; the
            # flag stays in the store, so it runs again on the next start.
            self._seed_task = self.entry.async_create_background_task(
                self.hass,
                self._async_seed_from_history(self._history_until),
                f"{DOMAIN} history {self.entry.entry_id}",
            )
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
        self._unsubs.append(
            self.hass.bus.async_listen(EVENT_HOMEASSISTANT_STOP, self._on_ha_stop)
        )
        self._unsubs.append(
            self.hass.bus.async_listen(
                ir.EVENT_REPAIRS_ISSUE_REGISTRY_UPDATED, self._on_issue_update
            )
        )
        # Sensors on the device that are not used yet (cells, discharge
        # counter): offered under Repairs once HA has started, and again a
        # bit later for integrations that come up slowly.
        self._unsubs.append(async_at_started(self.hass, self._check_extras))
        self._unsubs.append(
            async_call_later(self.hass, EXTRAS_RECHECK_S, self._check_extras)
        )
        if self.has_cells:
            self._unsubs.append(
                async_track_state_change_event(
                    self.hass,
                    [self.cell_max_entity, self.cell_min_entity],
                    self._on_cell,
                )
            )
        # Seed with current values
        self._handle_power(self.hass.states.get(self.power_entity))
        self._handle_soc(self.hass.states.get(self.soc_entity))
        self._sample_temps()
        self._update_status()

    async def _async_seed_from_history(self, until: float) -> None:
        """Replay the recorded SOC and power once, day by day (new battery only).

        Only swings that ended before `until` (the moment the battery was
        added) are used, so they never overlap with live measurements.
        """
        found: list[dict[str, Any]] = []
        replay = self._new_tracker()
        replay_health = self._new_health()
        h_out: dict[str, list] = {"events": [], "full_days": [], "alive_days": []}
        if "recorder" in self.hass.config.components:
            from homeassistant.components.recorder import get_instance, history  # noqa: PLC0415

            end = dt_util.utc_from_timestamp(until)
            day = end - timedelta(days=HISTORY_DAYS)

            def _load(entity_id: str, start, stop, first: bool) -> list[State]:
                return history.state_changes_during_period(
                    self.hass, start, stop, entity_id, include_start_time_state=first
                ).get(entity_id, [])

            try:
                rec = get_instance(self.hass)
                first = True
                while day < end:
                    stop = min(day + timedelta(days=1), end)
                    pow_states = await rec.async_add_executor_job(
                        _load, self.power_entity, day, stop, first
                    )
                    soc_states = await rec.async_add_executor_job(
                        _load, self.soc_entity, day, stop, first
                    )
                    events = [
                        (st.last_updated.timestamp(), "p", self._plausible_w(self._power_w(st)))
                        for st in pow_states
                    ] + [
                        (st.last_updated.timestamp(), "s", self._soc(st))
                        for st in soc_states
                    ]
                    found += replay_history(replay, events, replay_health, h_out)
                    first = False
                    day = stop
            except Exception:  # noqa: BLE001 - history is a bonus, never fatal
                _LOGGER.debug("%s: no history available", self.entry.title, exc_info=True)
                found = []
                h_out = {"events": [], "full_days": [], "alive_days": []}
        # SOC drift events from the history (only before the battery was added)
        old_ev = [e for e in h_out["events"] if e["ts"] < until]
        if old_ev or h_out["alive_days"]:
            self.soc_events = sorted(old_ev + self.soc_events, key=lambda e: e["ts"])
            self.full_days = sorted(set(h_out["full_days"]) | set(self.full_days))
            self.alive_days = sorted(set(h_out["alive_days"]) | set(self.alive_days))
            since = replay_health.s.get("since")
            if since is not None and (self.soc_since is None or since < self.soc_since):
                self.soc_since = since
        found = [
            r
            for r in found
            if r["ts"] < until and (is_full_discharge(r) or is_full_charge(r))
        ]
        if found:
            self.records = prune_records(sorted(found + self.records, key=lambda r: r["ts"]))
            _LOGGER.info(
                "%s: %s full discharge(s) found in the history",
                self.entry.title,
                sum(1 for r in found if is_full_discharge(r)),
            )
        if self.tracker.adopt_sign(replay):
            self._swap_health_energy()
            _LOGGER.info("%s: power sign taken over from the history", self.entry.title)
        self._history_until = None
        await self._store.async_save(self._data())
        self._recalculate()
        self._update_status(force=True)

    async def async_stop(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        await self._store.async_save(self._data())

    async def async_reset(self) -> None:
        """Forget all measurements of this battery (service call)."""
        if self._seed_task is not None and not self._seed_task.done():
            self._seed_task.cancel()
        self._history_until = None
        self.records = []
        self.tracker = self._new_tracker()
        self.cell_records = []
        self._temps.clear()
        self.cells = CellBalanceTracker()
        self.cell_result = evaluate_cells([])
        self.health = self._new_health()
        self.soc_events, self.full_days, self.alive_days = [], [], []
        self.soc_since = None
        self.dismissed, self.notified = {}, {}
        # start from the SOC the battery shows now, so the card does not
        # read "now – %" until the SOC moves (0.5.5)
        self._handle_soc(self.hass.states.get(self.soc_entity))
        await self._store.async_save(self._data())
        self._recalculate()
        self._update_status(force=True)

    # -- back-up, export, report (0.5.5) -----------------------------------

    def _battery_info(self) -> dict[str, Any]:
        from homeassistant.helpers import entity_registry as er

        ent = er.async_get(self.hass).async_get(self.soc_entity)
        return {
            "name": self.entry.title,
            "battery_id": self.entry.data.get(CONF_BATTERY_ID),
            "share_id": self.share_id,
            "model": self.model,
            "nominal_kwh": self.spec.nominal_kwh,
            "reserve_kwh": self.spec.reserve_kwh,
            "usable_kwh": round(self.spec.usable_kwh, 3),
            "purchase_date": self.spec.purchase_date.isoformat() if self.spec.purchase_date else None,
            "warranty_years": self.spec.warranty_years,
            "cycle_life": self.spec.cycle_life,
            "cycle_eol_pct": self.spec.cycle_eol_pct,
            "red_pct": self.spec.red_pct,
            "tolerance_pct": self.spec.tolerance_pct,
            "initial_cycles": self.spec.initial_cycles,
            "initial_cycles_from_counter": bool(self.cycle_counter),
            "power_sign": self.power_sign_state,
            "connection": ent.platform if ent else None,
            "has_cells": self.has_cells,
            "has_temps": self.has_temps,
            "soc_sensitivity": entry_setting(self.entry, CONF_SOC_SENSITIVITY),
            "cell_sensitivity": entry_setting(self.entry, CONF_CELL_SENSITIVITY),
            "notify": self.notify,
            "soc_entity": self.soc_entity,
            "power_entity": self.power_entity,
            "cell_max_entity": self.cell_max_entity,
            "cell_min_entity": self.cell_min_entity,
            "temp_max_entity": self.temp_max_entity,
            "temp_min_entity": self.temp_min_entity,
        }

    def export(self, variant: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        """One export of this battery (full / anonymous / marstek)."""
        from homeassistant.const import __version__ as ha_version

        summary = {
            **self.result,
            "soc": self.soc_result,
            "cells": {**self.cell_result, **self.cell_health},
            "monitor": {k: self.status.get(k) for k in ("state", "phase", "soc", "full_discharges")},
        }
        meta = {
            "created": dt_util.now().isoformat(timespec="seconds"),
            "app_version": self.app_version,
            "ha_version": ha_version,
            "language": (self.hass.config.language or "en")[:2],
        }
        return mcm_export.build(
            variant, self._battery_info(), data if data is not None else self._data(), summary, meta
        )

    def report_html(self, variant: str) -> str:
        return mcm_export.render_html(self.export(variant))

    async def async_write_backup(self, data: dict[str, Any] | None, label: str) -> Path:
        """Write a full back-up (report with the data in it) under
        /config/marstek_capacity_monitor/backup/."""
        html = mcm_export.render_html(self.export("full", data))
        stamp = dt_util.now().strftime("%Y%m%d-%H%M")
        bid = self.entry.data.get(CONF_BATTERY_ID) or self.entry.entry_id
        path = Path(self.hass.config.path(BACKUP_DIR)) / f"{bid}-{label}-{stamp}.html"

        def _write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(html, encoding="utf-8")

        await self.hass.async_add_executor_job(_write)
        return path

    async def async_restore(self, text: str, mode: str) -> dict[str, Any]:
        """Restore from a report or JSON export. mode: merge | replace.
        A full back-up of the current data is always written first."""
        incoming = mcm_export.parse(text)
        await self.async_write_backup(None, "before-restore")
        new_data = mcm_export.merge(self._data(), incoming.get("data") or {}, mode)
        if self._seed_task is not None and not self._seed_task.done():
            self._seed_task.cancel()
        self._apply(new_data)
        self._history_until = new_data.get("history_until")
        await self._store.async_save(self._data())
        self._recalculate()
        self._update_status(force=True)
        full = [r for r in (incoming.get("data") or {}).get("records", []) if is_full_discharge(r)]
        return {"variant": incoming.get("variant"), "records": len((incoming.get("data") or {}).get("records", [])), "full": len(full)}

    async def async_demo(self, scenario: str) -> None:
        """Fill the demo battery with one made-up situation (0.5.5)."""
        from . import demo

        await self.async_reset()
        data = demo.build(scenario, self._now_ts(), self.spec.usable_kwh, self.spec.nominal_kwh)
        self._apply({**self._data(), **data})
        self._history_until = None
        for kind in (KIND_SOC, KIND_CELLS):
            self._clear_issue(kind)
        self.notified.pop("critical", None)
        await self._store.async_save(self._data())
        self._recalculate()
        self._update_status(force=True)

    # -- helpers ------------------------------------------------------------

    def _new_tracker(self, state: dict[str, Any] | None = None) -> SwingTracker:
        auto = self.sign_mode == SIGN_AUTO
        tracker = SwingTracker(state, auto_sign=auto)
        if not auto:
            # The user fixed the sign: forget anything learned automatically.
            tracker.s["sign"] = 1
            tracker.s["sign_flipped"] = False
        return tracker

    def _new_health(self, state: dict[str, Any] | None = None) -> SocHealthTracker:
        return SocHealthTracker(state, unit_kwh=self.spec.nominal_kwh / 100)

    def _swap_health_energy(self) -> None:
        """The power sign was reversed: the counted energy changed buckets."""
        h = self.health.s
        h["e_c"], h["e_d"] = h.get("e_d"), h.get("e_c")

    @property
    def power_sign_state(self) -> str:
        """Human-readable state of the sign detection (diagnostics)."""
        if self.sign_mode != SIGN_AUTO:
            return self.sign_mode
        if not self.tracker.s.get("sign_confirmed"):
            return "auto_pending"
        return "auto_reversed" if self.tracker.s.get("sign_flipped") else "auto_normal"

    def _data(self) -> dict[str, Any]:
        return {
            "tracker": self.tracker.s,
            "records": self.records,
            "cells": self.cells.s,
            "cell_records": self.cell_records,
            # set while the one-time history check has not finished yet
            "history_until": self._history_until,
            "health": self.health.s,
            "soc_events": self.soc_events,
            "full_days": self.full_days,
            "alive_days": self.alive_days,
            "soc_since": self.soc_since,
            "dismissed": self.dismissed,
            "notified": self.notified,
            "share_id": self.share_id,
        }

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

    def _tops(self) -> list[float]:
        return [e["ts"] for e in self.soc_events if e["type"] == "top"]

    def _other_jumps(self) -> list[float]:
        """Jumps of the other batteries: at the same time = data, not battery."""
        out: list[float] = []
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            other = getattr(entry, "runtime_data", None)
            if entry.entry_id == self.entry.entry_id or not isinstance(other, BatteryMonitor):
                continue
            out += [e["ts"] for e in other.soc_events if e["type"] == "jump"]
        return out

    def _evaluate_health(self) -> None:
        now = self._now_ts()
        soc_level = entry_setting(self.entry, CONF_SOC_SENSITIVITY)
        cell_level = entry_setting(self.entry, CONF_CELL_SENSITIVITY)
        self.soc_result = evaluate_soc(
            self.soc_events,
            self.full_days,
            self.alive_days,
            now,
            self._other_jumps(),
            event_pct=SOC_EVENT_PCT.get(soc_level, SOC_EVENT_PCT["normal"]),
            enabled=soc_level != "off",
        )
        self.soc_result["sensitivity"] = soc_level
        if self.has_cells:
            self.cell_health = evaluate_cell_health(
                self.cell_records,
                [e for e in self.soc_events if e["type"] == "rest"],
                now,
                self.health.rest_hours_now(now),
                factor=CELL_FACTORS.get(cell_level, CELL_FACTORS["normal"]),
                enabled=cell_level != "off",
            )
            self.cell_health["sensitivity"] = cell_level
        else:
            self.cell_health = {"level": "ok"}
        self._update_advice()

    def _recalculate(self) -> None:
        self.result = evaluate(
            self.spec,
            self.records,
            self.tracker.cumulative_discharge_kwh,
            dt_util.now().replace(tzinfo=None),
            self._tops(),
            self.soc_since,
        )
        self._check_model_issue()
        self._check_power_issue()
        self._critical_issue()
        self._evaluate_health()
        async_dispatcher_send(self.hass, self.signal)

    @property
    def check_model_issue_id(self) -> str:
        return f"check_model_{self.entry.entry_id}"

    def _check_model_issue(self) -> None:
        """About half of the set capacity measured: ask whether the model is
        right (a Venus C set up as a Venus E), under Settings -> Repairs."""
        if self.result.get("status") != "check_model":
            ir.async_delete_issue(self.hass, DOMAIN, self.check_model_issue_id)
            return
        lang = (self.hass.config.language or "en")[:2]
        dec = "," if lang in ("nl", "de") else "."
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            self.check_model_issue_id,
            is_fixable=False,
            is_persistent=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="check_model",
            translation_placeholders={
                "name": self.entry.title,
                "pct": f"{self.result.get('measured_pct') or 0:.1f}".replace(".", dec),
                "kwh": f"{self.spec.nominal_kwh:.2f}".replace(".", dec),
            },
        )

    @property
    def check_power_issue_id(self) -> str:
        return f"check_power_{self.entry.entry_id}"

    def _check_power_issue(self) -> None:
        """The newest full discharge came out far above new (more energy
        counted than fits in the battery): ask to check the power sensor,
        under Settings -> Repairs. Gone again after a credible measurement."""
        if self.result.get("status") != "check_power":
            ir.async_delete_issue(self.hass, DOMAIN, self.check_power_issue_id)
            return
        lang = (self.hass.config.language or "en")[:2]
        dec = "," if lang in ("nl", "de") else "."
        r = self.result
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            self.check_power_issue_id,
            is_fixable=False,
            is_persistent=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="check_power",
            translation_placeholders={
                "name": self.entry.title,
                "pct": f"{r.get('impossible_last_pct') or 0:.0f}",
                "kwh": f"{r.get('impossible_last_kwh') or 0:.0f}",
                "limit": f"{r.get('impossible_limit_pct') or 130:.0f}",
                "count": str(r.get("impossible_count") or 0),
            },
        )

    @property
    def critical_issue_id(self) -> str:
        since = int(self.result.get("red_since") or 0)
        return f"critical_{self.entry.entry_id}_{since}"

    def _critical_issue(self) -> None:
        """Red, confirmed by CONFIRM_N measurements in a row (0.5.5): one
        message under Settings -> Repairs and on the phone, with a pointer to
        the Marstek report. Then it is up to Marstek to look into it."""
        old = self.notified.get("critical")
        if not self.result.get("red_confirmed") or not self.notify:
            for domain, issue_id in list(ir.async_get(self.hass).issues):
                if domain == DOMAIN and issue_id.startswith(f"critical_{self.entry.entry_id}_"):
                    ir.async_delete_issue(self.hass, DOMAIN, issue_id)
            if old is not None and not self.result.get("red_confirmed"):
                self.notified["critical"] = None
                self._phone("critical", None)
                self._store.async_delay_save(self._data, 5)
            return
        lang = advice.lang_of(self.hass.config.language)
        dec = "," if lang in ("nl", "de") else "."
        pct = f"{self.result.get('measured_pct') or 0:.1f}".replace(".", dec)
        red = f"{self.spec.red_pct:.0f}"
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            self.critical_issue_id,
            is_fixable=False,
            is_persistent=False,
            severity=ir.IssueSeverity.ERROR,
            translation_key="critical",
            translation_placeholders={
                "name": self.entry.title,
                "pct": pct,
                "red": red,
                "count": str(self.result.get("red_count") or 0),
            },
        )
        since = self.result.get("red_since")
        if old == since:
            return
        self.notified["critical"] = since
        self._store.async_delay_save(self._data, 5)
        text = {
            "nl": f"{self.entry.title}: capaciteit {pct} %, {self.result.get('red_count')} metingen op rij onder de rode lijn van {red} %. Download het Marstek-rapport (knop Rapport op de kaart) en meld het via de Marstek-app.",
            "en": f"{self.entry.title}: capacity {pct} %, {self.result.get('red_count')} measurements in a row below the red line of {red} %. Download the Marstek report (Report button on the card) and report it via the Marstek app.",
            "de": f"{self.entry.title}: Kapazität {pct} %, {self.result.get('red_count')} Messungen in Folge unter der roten Linie von {red} %. Laden Sie den Marstek-Bericht herunter (Taste Bericht auf der Karte) und melden Sie es über die Marstek-App.",
        }[lang]
        for name in self._phones():
            self.hass.async_create_task(
                self.hass.services.async_call(
                    "notify", name,
                    {"title": advice.TITLE, "message": text, "data": {"tag": self._tag("critical")}},
                    blocking=False,
                )
            )

    # -- advice: "let op" and advice messages -------------------------------

    def health_of(self, kind: str) -> dict[str, Any]:
        return self.cell_health if kind == KIND_CELLS else self.soc_result

    def is_dismissed(self, kind: str) -> bool:
        res = self.health_of(kind)
        return res.get("level", "ok") != "ok" and self.dismissed.get(kind) == res.get("since")

    def _issue_id(self, kind: str, since: float) -> str:
        return f"{kind}_{self.entry.entry_id}_{int(since)}"

    def _clear_issue(self, kind: str) -> None:
        issue = self._issues.pop(kind, None)
        if issue:
            ir.async_delete_issue(self.hass, DOMAIN, issue)

    def _phones(self) -> list[str]:
        return sorted(
            name
            for name in self.hass.services.async_services().get("notify", {})
            if name.startswith("mobile_app_")
        )

    def _tag(self, kind: str) -> str:
        return f"{DOMAIN}_{self.entry.entry_id}_{kind}"

    def _phone(self, kind: str, text: str | None, since: float | None = None) -> None:
        """Send (text) or remove (None) the message on every phone with the app."""
        lang = advice.lang_of(self.hass.config.language)
        for name in self._phones():
            if text is None:
                data = {"message": "clear_notification", "data": {"tag": self._tag(kind)}}
            else:
                data = {
                    "title": advice.TITLE,
                    "message": text,
                    "data": {
                        "tag": self._tag(kind),
                        "actions": [
                            {
                                "action": f"{NOTIFY_ACTION_PREFIX}|{self.entry.entry_id}|{kind}|{int(since or 0)}",
                                "title": advice.DISMISS[lang],
                            }
                        ],
                    },
                }
            self.hass.async_create_task(
                self.hass.services.async_call("notify", name, data, blocking=False)
            )

    def _update_advice(self) -> None:
        """Fire an event and send a message when the level of a subject changes."""
        for kind in (KIND_SOC, KIND_CELLS):
            res = self.health_of(kind)
            level, since = res.get("level", "ok"), res.get("since")
            key = [level, since] if level != "ok" else None
            old = self.notified.get(kind)
            if key == old:
                # Repairs are not kept over a restart: put it back when needed
                if key and self.notify and not self.is_dismissed(kind):
                    self._ensure_issue(kind, level, since, res)
                elif key:
                    self._clear_issue(kind)
                continue
            self.notified[kind] = key
            self.hass.bus.async_fire(
                EVENT_ADVICE,
                {
                    "entry_id": self.entry.entry_id,
                    "name": self.entry.title,
                    "battery": self.entry.data.get("battery_id"),
                    "kind": kind,
                    "level": level,
                    "count": res.get("count"),
                    "size": res.get("last_size"),
                },
            )
            self._store.async_delay_save(self._data, 5)
            self._clear_issue(kind)
            if level == "ok":
                if old:
                    self._phone(kind, None)
                continue
            if not self.notify or self.is_dismissed(kind):
                continue
            text = self._ensure_issue(kind, level, since, res)
            self._phone(kind, text, since)

    def _ensure_issue(self, kind: str, level: str, since: float, res: dict[str, Any]) -> str:
        """Create (or keep) the message under Settings -> Repairs; returns its text."""
        text = advice.message(
            kind, level, self.entry.title, res, self.model, self.hass.config.language
        )
        issue = self._issue_id(kind, since)
        if self._issues.get(kind) not in (None, issue):
            self._clear_issue(kind)
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            issue,
            is_fixable=False,
            is_persistent=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=f"{kind}_{level}",
            translation_placeholders={"name": self.entry.title, "message": text},
        )
        self._issues[kind] = issue
        return text

    async def async_dismiss(self, kind: str, since: float | None = None) -> bool:
        """Dismiss the current "let op" or advice once (card, phone or Repairs).
        It comes back only with a new series of occurrences."""
        res = self.health_of(kind)
        if res.get("level", "ok") == "ok":
            return False
        if since is not None and int(since) != int(res.get("since") or 0):
            return False  # an old message: a newer series is running
        self.dismissed[kind] = res.get("since")
        self._clear_issue(kind)
        self._phone(kind, None)
        await self._store.async_save(self._data())
        async_dispatcher_send(self.hass, self.signal)
        return True

    @property
    def extras_issue_id(self) -> str:
        return f"extras_{self.entry.entry_id}"

    @callback
    def _check_extras(self, _now: Any = None) -> None:
        """Offer sensors found on the device under Settings -> Repairs."""
        found = find_extras(
            self.hass,
            self.entry,
            self.tracker.cumulative_discharge_kwh,
            declined=self.extras_declined,
        )
        if not found:
            ir.async_delete_issue(self.hass, DOMAIN, self.extras_issue_id)
            return
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            self.extras_issue_id,
            is_fixable=True,
            is_persistent=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="extras_found",
            translation_placeholders={"name": self.entry.title},
            data={"entry_id": self.entry.entry_id},
        )

    @property
    def extras_declined(self) -> list[str]:
        return list(self.entry.options.get(CONF_EXTRAS_DECLINED, []))

    @callback
    def _on_issue_update(self, event: Event) -> None:
        """Ignored under Settings -> Repairs: same as dismissing on the card."""
        data = event.data
        if data.get("domain") != DOMAIN or data.get("action") != "update":
            return
        for kind, issue_id in list(self._issues.items()):
            if issue_id != data.get("issue_id"):
                continue
            issue = ir.async_get(self.hass).async_get_issue(DOMAIN, issue_id)
            if issue is not None and issue.dismissed_version is not None:
                self.hass.async_create_task(self.async_dismiss(kind))

    def _cell_mv(self, entity_id: str | None) -> float | None:
        state = self.hass.states.get(entity_id) if entity_id else None
        if state is None or state.state in BAD_STATES:
            return None
        try:
            value = float(state.state)
        except ValueError:
            return None
        return to_mv(value, state.attributes.get("unit_of_measurement"))

    def _check_cells(self) -> None:
        if not self.has_cells:
            return
        record = self.cells.update(
            self.tracker.s.get("soc"),
            self.tracker.s.get("power_w"),
            self._cell_mv(self.cell_max_entity),
            self._cell_mv(self.cell_min_entity),
            self._now_ts(),
        )
        if record is None:
            return
        self.cell_records.append(record)
        del self.cell_records[:-MAX_CELL_RECORDS]
        self.cell_result = evaluate_cells(self.cell_records)
        self._evaluate_health()
        self.hass.async_create_task(self._store.async_save(self._data()))
        _LOGGER.debug("%s: cell spread recorded %s", self.entry.title, record)
        async_dispatcher_send(self.hass, self.signal)

    @staticmethod
    def _age_s(state: State | None, now: datetime) -> float | None:
        if state is None:
            return None
        seen = getattr(state, "last_reported", None) or state.last_updated
        return (now - seen).total_seconds()

    @staticmethod
    def _idle(pow_s: State | None) -> bool:
        """The battery stands still (empty or full): last power close to 0 W.

        Then SOC and power can stay the same for hours (ESPHome, for one, only
        sends a value when it changes); that is not a broken connection.
        """
        if pow_s is None or pow_s.state in BAD_STATES:
            return False
        try:
            value = abs(float(pow_s.state))
        except ValueError:
            return False
        unit = pow_s.attributes.get("unit_of_measurement")
        if unit == UnitOfPower.KILO_WATT:
            value *= 1000
        elif unit == UnitOfPower.MEGA_WATT:
            value *= 1_000_000
        return value <= IDLE_POWER_W

    def _compute_status(self) -> dict[str, Any]:
        now = dt_util.utcnow()
        soc_s = self.hass.states.get(self.soc_entity)
        pow_s = self.hass.states.get(self.power_entity)
        missing = [
            e
            for e, st in ((self.soc_entity, soc_s), (self.power_entity, pow_s))
            if st is None or st.state in BAD_STATES
        ]
        ages = [a for a in (self._age_s(soc_s, now), self._age_s(pow_s, now)) if a is not None]
        full = sum(1 for r in self.records if is_full_discharge(r))
        if missing:
            state = STATUS_SENSOR_MISSING
        elif (
            ages
            and min(ages) > STALE_SECONDS
            and not self._idle(pow_s)
        ):
            state = STATUS_NO_RECENT_DATA
        elif full:
            state = STATUS_MEASURING
        else:
            state = STATUS_COLLECTING
        phase = measurement_phase(self.tracker.s)
        soc = phase.get("soc")
        return {
            "state": state,
            "phase": phase["phase"],
            "soc": round(soc) if soc is not None else None,
            "from_soc": phase.get("from_soc"),
            "interrupted": phase.get("interrupted"),
            "full_discharges": full,
            "power_sign": self.power_sign_state,
            "missing": missing,
            "last_data_minutes": round(min(ages) / 60) if ages else None,
            "model": self.model,
            "cell_check": self.has_cells,
            "temperature_check": self.has_temps,
        }

    def _update_status(self, force: bool = False) -> None:
        """Recompute the status; only notify when something visible changed,
        to keep the recorder write load low."""
        new = self._compute_status()

        def key_of(st: dict[str, Any]) -> dict[str, Any]:
            key = {k: v for k, v in st.items() if k != "last_data_minutes"}
            if st.get("state") == STATUS_NO_RECENT_DATA:
                # update the shown time once an hour, not every minute
                key["hours"] = (st.get("last_data_minutes") or 0) // 60
            return key

        key, old = key_of(new), key_of(self.status)
        self.status = new
        if force or key != old:
            async_dispatcher_send(self.hass, self.status_signal)

    # -- event handlers -----------------------------------------------------

    def _health_events(self, new: list[dict[str, Any]]) -> None:
        if not new:
            return
        add_events(self.soc_events, new)
        self._evaluate_health()
        async_dispatcher_send(self.hass, self.signal)

    @property
    def _bridging(self) -> bool:
        return bool(self.tracker.s.get("bridge"))

    @staticmethod
    def _plausible_w(watts: float | None) -> float | None:
        """None for a value no home battery can reach (wrong unit)."""
        if watts is not None and abs(watts) > MAX_PLAUSIBLE_POWER_W:
            return None
        return watts

    @property
    def implausible_issue_id(self) -> str:
        return f"implausible_power_{self.entry.entry_id}"

    def _implausible_power(self, state: State, watts: float) -> None:
        """Report a power value that cannot be right, under Settings -> Repairs.
        The value itself is ignored (counts as a gap in the data)."""
        first = self._implausible_ts is None
        self._implausible_ts = self._now_ts()
        if not first:
            return
        _LOGGER.warning(
            "%s: %s reports %s %s (%.0f W); ignored, check the unit of the sensor",
            self.entry.title,
            self.power_entity,
            state.state,
            state.attributes.get("unit_of_measurement", ""),
            watts,
        )
        lang = (self.hass.config.language or "en")[:2]
        sep = "." if lang in ("nl", "de") else ","
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            self.implausible_issue_id,
            is_fixable=False,
            is_persistent=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="implausible_power",
            translation_placeholders={
                "name": self.entry.title,
                "entity": self.power_entity,
                "value": f"{state.state} {state.attributes.get('unit_of_measurement', '')}".strip(),
                "watts": f"{abs(watts):,.0f}".replace(",", sep),
            },
        )

    def _check_implausible_clear(self, ts: float) -> None:
        if self._implausible_ts is not None and ts - self._implausible_ts > IMPLAUSIBLE_CLEAR_S:
            self._implausible_ts = None
            ir.async_delete_issue(self.hass, DOMAIN, self.implausible_issue_id)

    def _handle_power(self, state: State | None) -> None:
        ts = self._now_ts()
        watts = self._power_w(state)
        if state is not None and watts is not None and self._plausible_w(watts) is None:
            self._implausible_power(state, watts)
            watts = None
        record = self.tracker.update_power(watts, ts)
        self._health_events(
            self.health.on_power(self.tracker.s.get("power_w"), ts, gap=self._bridging)
        )
        self._check_cells()
        if record is not None:
            self._process_record(record)
        self._store.async_delay_save(self._data, SAVE_DELAY_SECONDS)

    def _handle_soc(self, state: State | None) -> None:
        soc = self._soc(state)
        if soc is None:
            return
        ts = self._now_ts()
        record = self.tracker.update_soc(soc, ts)
        if self.soc_since is None:
            self.soc_since = ts
        note_day(self.full_days, self.alive_days, soc, ts)
        self._health_events(
            self.health.on_soc(
                soc,
                self.tracker.s["e_charge_kwh"],
                self.tracker.s["e_discharge_kwh"],
                ts,
                gap=self._bridging,
            )
        )
        self._check_cells()
        self._update_status()
        if record is None:
            self._store.async_delay_save(self._data, SAVE_DELAY_SECONDS)
            return
        self._process_record(record)

    def _process_record(self, record: dict[str, Any]) -> None:
        """A charge or discharge swing has completed: store and publish it."""
        if self.has_temps:
            self._sample_temps()
            record.update(self._temps_between(record["start_ts"], record["ts"]))
        self.records.append(record)
        self.records = prune_records(self.records)
        self.last_session = record
        self.hass.async_create_task(self._store.async_save(self._data()))
        self.hass.bus.async_fire(
            EVENT_SESSION,
            {"entry_id": self.entry.entry_id, "name": self.entry.title, **record},
        )
        _LOGGER.debug("%s: session recorded %s", self.entry.title, record)
        if record.get("sign_corrected"):
            self._swap_health_energy()
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
        self._update_status()

    @callback
    def _on_power(self, event: Event[EventStateChangedData]) -> None:
        self._handle_power(event.data["new_state"])

    @callback
    def _on_soc(self, event: Event[EventStateChangedData]) -> None:
        self._handle_soc(event.data["new_state"])

    @callback
    def _on_cell(self, _event: Event[EventStateChangedData]) -> None:
        self._check_cells()

    @callback
    def _on_tick(self, _now: datetime) -> None:
        ts = self._now_ts()
        record = self.tracker.tick(ts)
        self._check_implausible_clear(ts)
        self._health_events(self.health.tick(ts, gap=self._bridging))
        note_day(self.full_days, self.alive_days, self.tracker.s.get("soc"), ts)
        self._sample_temps()
        self._check_cells()
        if record is not None:
            self._process_record(record)
        self._update_status()
        # Keep a save pending, so Home Assistant writes the current state when
        # it stops (final write); at most one write per SAVE_DELAY_SECONDS.
        self._store.async_delay_save(self._data, SAVE_DELAY_SECONDS)

    @callback
    def _on_ha_stop(self, _event: Event) -> None:
        """HA is stopping: integrate up to now, so the saved power timestamp is
        exact and a short restart can be bridged (written at the final write)."""
        record = self.tracker.tick(self._now_ts())
        if record is not None:
            self._process_record(record)
        self._store.async_delay_save(self._data, SAVE_DELAY_SECONDS)

    @callback
    def _on_recalc(self, _now: datetime) -> None:
        self._recalculate()
