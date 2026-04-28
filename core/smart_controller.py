"""
SmartController - demand-adaptive traffic light controller for 3-intersection network.

Each intersection (int_A, int_B, int_C) is controlled independently with its own
FSM, normalized pressure scoring, and emergency override.

Pressure formula (normalized per node):
    pressure = (vehicle_count / max_seen_count) + (waiting_time / max_seen_wait)
    where max_seen values are tracked dynamically and updated every step.
    Normalization keeps scores in [0, 2] regardless of absolute traffic volume.

Switch condition (from any green state):
    elapsed >= MIN_GREEN
    AND competing_pressure / current_pressure >= SWITCH_RATIO (1.5)
    OR  elapsed >= effective_max_green (60s normal, 90s under congestion relief)
    OR  emergency extension exhausted (EMERGENCY_HOLD)

Green-wave coordination:
    When int_A enters EW_GREEN, after WAVE_TRIGGER_DELAY (10s) int_B is pushed
    toward EW_GREEN if it is still in NS_GREEN and has served MIN_GREEN.
    When int_B enters EW_GREEN, soft EW-bias hints propagate to int_A and int_C.

Congestion relief:
    If total waiting_time across an intersection exceeds CONGESTION_THRESHOLD (500s),
    effective MAX_GREEN is raised to CONGESTION_MAX_GREEN (90s) for that node only.

Emergency detection:
    Scans per-lane LaneData objects directly for each node's approaches.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from core.traffic_env import TrafficEnv, NetworkState


# ---------------------------------------------------------------------------
# Tuneable constants
# ---------------------------------------------------------------------------

MIN_GREEN              = 8.0    # s  minimum green before a switch is considered
MAX_GREEN              = 60.0   # s  normal force-switch ceiling
YELLOW_DURATION        = 3.0    # s
EMERGENCY_HOLD         = 60.0   # s  max hold duration on emergency-extended green

SWITCH_RATIO           = 1.5    # competing axis must have >= this ratio of pressure

CONGESTION_THRESHOLD   = 500.0  # s  total node waiting_time that triggers relief mode
CONGESTION_MAX_GREEN   = 90.0   # s  extended ceiling under congestion relief

# Green-wave: upstream EW_GREEN triggers a downstream forced bias after this delay
WAVE_TRIGGER_DELAY     = 10.0   # s  delay after int_A EW_GREEN before int_B is pushed

# Soft EW bias bonus (normalized units) added when a wave hint is active
WAVE_BONUS             = 0.4    # added to EW normalized pressure (scale 0-2)
WAVE_WINDOW            = 12.0   # s  window around ETA in which hint is active
TRAVEL_TIME            = 29.0   # s  400 m / 13.9 m/s


# ---------------------------------------------------------------------------
# Phase index constants (must match SUMO TL program)
# ---------------------------------------------------------------------------

PHASE_NS_GREEN  = 0
PHASE_NS_YELLOW = 1
PHASE_EW_GREEN  = 2
PHASE_EW_YELLOW = 3


# ---------------------------------------------------------------------------
# Per-intersection approach axis mapping
# ---------------------------------------------------------------------------

_AXES: dict[str, dict[str, list[str]]] = {
    "int_A": {
        "NS": ["north_in", "south_in"],
        "EW": ["west_in"],
    },
    "int_B": {
        "NS": ["north_in", "south_in"],
        "EW": ["east_in", "west_in"],
    },
    "int_C": {
        "NS": ["north_in", "south_in"],
        "EW": ["east_in"],
    },
}


# ---------------------------------------------------------------------------
# Internal FSM types
# ---------------------------------------------------------------------------

class _State(enum.Enum):
    NS_GREEN  = "NS_GREEN"
    NS_YELLOW = "NS_YELLOW"
    EW_GREEN  = "EW_GREEN"
    EW_YELLOW = "EW_YELLOW"


_STATE_PHASE: dict[_State, int] = {
    _State.NS_GREEN:  PHASE_NS_GREEN,
    _State.NS_YELLOW: PHASE_NS_YELLOW,
    _State.EW_GREEN:  PHASE_EW_GREEN,
    _State.EW_YELLOW: PHASE_EW_YELLOW,
}

_NEXT_STATE: dict[_State, _State] = {
    _State.NS_GREEN:  _State.NS_YELLOW,
    _State.NS_YELLOW: _State.EW_GREEN,
    _State.EW_GREEN:  _State.EW_YELLOW,
    _State.EW_YELLOW: _State.NS_GREEN,
}


@dataclass
class _EmergencyInfo:
    active: bool = False
    hold_elapsed: float = 0.0


@dataclass
class _WaveHint:
    """Soft EW-bias hint placed by a neighbouring node."""
    eta: float        # sim_time when platoon is expected
    placed_at: float  # sim_time when hint was placed


@dataclass
class _NodeState:
    tl_id: str
    state: _State = _State.NS_GREEN
    state_elapsed: float = 0.0
    phase_changes: int = 0
    emergency: _EmergencyInfo = field(default_factory=_EmergencyInfo)
    wave_hint: Optional[_WaveHint] = None
    # Hard EW bias: sim_time after which a forced EW switch is allowed
    ew_bias_after: float = 0.0   # 0.0 = no pending bias


# ---------------------------------------------------------------------------
# Per-node running max trackers (for normalization)
# ---------------------------------------------------------------------------

@dataclass
class _MaxTracker:
    """Tracks the running maximum vehicle_count and waiting_time seen per axis."""
    max_count: float = 1.0   # floored at 1 to avoid division by zero
    max_wait:  float = 1.0


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------

class SmartController:
    """
    Demand-adaptive controller for int_A, int_B, int_C with normalized pressure,
    green-wave coordination, and congestion relief.

    Usage
    -----
    ctrl = SmartController(env)
    ctrl.reset()
    while not env.is_done:
        state = env.step()
        action = ctrl.update(state)
    """

    def __init__(self, env: "TrafficEnv"):
        self.env   = env
        self._nodes: dict[str, _NodeState] = {}
        self._maxes: dict[str, dict[str, _MaxTracker]] = {}  # tl_id -> axis -> tracker
        self._total_steps = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def reset(self) -> None:
        self._nodes = {
            tl_id: _NodeState(tl_id=tl_id)
            for tl_id in ["int_A", "int_B", "int_C"]
        }
        self._maxes = {
            tl_id: {"NS": _MaxTracker(), "EW": _MaxTracker()}
            for tl_id in ["int_A", "int_B", "int_C"]
        }
        self._total_steps = 0
        for ns in self._nodes.values():
            self._apply_phase(ns)

    def update(self, state: "NetworkState") -> dict:
        """
        Advance all three node FSMs one step and return an action dict.
        Returns int_B data at top level for backward compatibility.
        Also includes "all_intersections" sub-dict with per-node details.
        """
        dt       = self.env.step_length
        sim_time = state.sim_time
        self._total_steps += 1

        # Update running max values before computing pressure
        for tl_id, ns in self._nodes.items():
            idata = state.intersections[tl_id]
            self._update_maxes(tl_id, idata)

        all_actions: dict[str, dict] = {}
        for tl_id, ns in self._nodes.items():
            idata       = state.intersections[tl_id]
            node_action = self._step_node(ns, idata, dt, sim_time)
            all_actions[tl_id] = node_action

        primary = dict(all_actions["int_B"])
        primary["all_intersections"] = all_actions
        primary["intA_phase"] = state.intersections["int_A"].phase_index
        primary["intB_phase"] = state.intersections["int_B"].phase_index
        primary["intC_phase"] = state.intersections["int_C"].phase_index
        return primary

    # ------------------------------------------------------------------
    # Properties / diagnostics
    # ------------------------------------------------------------------

    @property
    def current_phase(self) -> int:
        return _STATE_PHASE[self._nodes["int_B"].state]

    def reset_trackers(self) -> None:
        """Reset running-max normalisation trackers without resetting the FSM state."""
        self._maxes = {
            tl_id: {"NS": _MaxTracker(), "EW": _MaxTracker()}
            for tl_id in ["int_A", "int_B", "int_C"]
        }

    def summary(self) -> dict:
        return {
            "total_steps": self._total_steps,
            "nodes": {
                tl_id: {
                    "state":          ns.state.value,
                    "elapsed":        round(ns.state_elapsed, 1),
                    "phase_changes":  ns.phase_changes,
                    "emergency":      ns.emergency.active,
                    "ew_bias_after":  round(ns.ew_bias_after, 1) if ns.ew_bias_after else None,
                    "wave_hint_eta":  round(ns.wave_hint.eta, 1) if ns.wave_hint else None,
                }
                for tl_id, ns in self._nodes.items()
            },
        }

    # ------------------------------------------------------------------
    # Running max update
    # ------------------------------------------------------------------

    def _update_maxes(self, tl_id: str, idata) -> None:
        for axis, ap_names in _AXES[tl_id].items():
            tracker = self._maxes[tl_id][axis]
            total_count = 0.0
            total_wait  = 0.0
            for ap_name in ap_names:
                ap = idata.approaches.get(ap_name)
                if ap is not None:
                    total_count += ap["vehicle_count"]
                    total_wait  += ap["waiting_time"]
            if total_count > tracker.max_count:
                tracker.max_count = total_count
            if total_wait > tracker.max_wait:
                tracker.max_wait = total_wait

    # ------------------------------------------------------------------
    # Per-node FSM step
    # ------------------------------------------------------------------

    def _step_node(
        self,
        ns: _NodeState,
        idata,
        dt: float,
        sim_time: float,
    ) -> dict:
        ns.state_elapsed += dt
        self._update_emergency(ns, idata)

        ns_pressure = self._axis_pressure_norm(ns.tl_id, "NS", idata)
        ew_pressure = self._axis_pressure_norm(ns.tl_id, "EW", idata)

        # Soft EW hint bonus
        wave_active = self._wave_active(ns, sim_time)
        ew_eff = ew_pressure + (WAVE_BONUS if wave_active else 0.0)

        # Congestion relief: raise the MAX_GREEN ceiling for this node if needed
        total_node_wait = sum(ap["waiting_time"] for ap in idata.approaches.values())
        effective_max = CONGESTION_MAX_GREEN if total_node_wait > CONGESTION_THRESHOLD else MAX_GREEN

        action = {
            "tl_id":          ns.tl_id,
            "state":          ns.state.value,
            "phase":          ns.state.value,
            "switched":       False,
            "reason":         "hold",
            "ns_pressure":    round(ns_pressure, 3),
            "ew_pressure":    round(ew_eff, 3),
            "wave_active":    wave_active,
            "congestion":     total_node_wait > CONGESTION_THRESHOLD,
            "effective_max":  effective_max,
        }

        if self._should_advance(ns, ns_pressure, ew_eff, sim_time, effective_max):
            old_state = ns.state
            elapsed   = ns.state_elapsed   # capture before _advance() resets it to 0
            self._advance(ns, dt)
            self._apply_phase(ns)
            action["switched"]  = True
            action["new_phase"] = ns.state.value
            action["state"]     = ns.state.value
            action["reason"]    = self._advance_reason(old_state, ns_pressure, ew_eff, effective_max, elapsed)
            self._emit_coordination(ns, sim_time)

        return action

    # ------------------------------------------------------------------
    # FSM advance logic
    # ------------------------------------------------------------------

    def _should_advance(
        self,
        ns: _NodeState,
        ns_pressure: float,
        ew_pressure: float,
        sim_time: float,
        effective_max: float,
    ) -> bool:
        state   = ns.state
        elapsed = ns.state_elapsed

        # Yellow always advances after fixed duration
        if state in (_State.NS_YELLOW, _State.EW_YELLOW):
            return elapsed >= YELLOW_DURATION

        if elapsed < MIN_GREEN:
            return False

        # Emergency: hold current green until hold budget is used
        if ns.emergency.active and ns.emergency.hold_elapsed < EMERGENCY_HOLD:
            return False

        # Force-switch at effective ceiling
        if elapsed >= effective_max:
            return True

        # Hard EW bias triggered by upstream (int_A → int_B green wave)
        if (
            state == _State.NS_GREEN
            and ns.ew_bias_after > 0.0
            and sim_time >= ns.ew_bias_after
        ):
            ns.ew_bias_after = 0.0   # consume the trigger
            return True

        # Pressure-based switch (normalized ratio only, no absolute diff needed)
        if state == _State.NS_GREEN:
            competing, current_p = ew_pressure, ns_pressure
        else:
            competing, current_p = ns_pressure, ew_pressure

        ratio = (competing / current_p) if current_p > 0.0 else float("inf")
        return ratio >= SWITCH_RATIO

    def _advance(self, ns: _NodeState, dt: float) -> None:
        ns.state         = _NEXT_STATE[ns.state]
        ns.state_elapsed = 0.0
        ns.phase_changes += 1
        if ns.emergency.active:
            ns.emergency.hold_elapsed += dt

    def _advance_reason(
        self,
        old_state: _State,
        ns_p: float,
        ew_p: float,
        effective_max: float,
        elapsed: float,
    ) -> str:
        if old_state in (_State.NS_YELLOW, _State.EW_YELLOW):
            return "yellow_end"
        if elapsed >= effective_max:
            return "congestion_max" if effective_max > MAX_GREEN else "max_green"
        if old_state == _State.NS_GREEN:
            return "wave_bias" if ew_p >= SWITCH_RATIO else "pressure_ew"
        if old_state == _State.EW_GREEN:
            return "pressure_ns"
        return "smart_cycle"

    # ------------------------------------------------------------------
    # Normalized pressure computation
    # ------------------------------------------------------------------

    def _axis_pressure_norm(self, tl_id: str, axis: str, idata) -> float:
        """
        Normalized pressure in [0, 2]:
            (total_vehicle_count / max_seen_count) + (total_waiting_time / max_seen_wait)
        """
        tracker     = self._maxes[tl_id][axis]
        total_count = 0.0
        total_wait  = 0.0
        for ap_name in _AXES[tl_id].get(axis, []):
            ap = idata.approaches.get(ap_name)
            if ap is not None:
                total_count += ap["vehicle_count"]
                total_wait  += ap["waiting_time"]
        return (total_count / tracker.max_count) + (total_wait / tracker.max_wait)

    # ------------------------------------------------------------------
    # Emergency detection — scans per-lane LaneData directly
    # ------------------------------------------------------------------

    def _update_emergency(self, ns: _NodeState, idata) -> None:
        """
        Check every lane in every approach of this intersection for an emergency
        vehicle by reading the per-lane LaneData objects directly.
        """
        found = False
        for ap_name in _AXES[ns.tl_id].get("NS", []) + _AXES[ns.tl_id].get("EW", []):
            ap = idata.approaches.get(ap_name)
            if ap is None:
                continue
            for lane_data in ap["lanes"].values():
                if lane_data.has_emergency:
                    found = True
                    break
            if found:
                break

        if found:
            if not ns.emergency.active:
                ns.emergency.active       = True
                ns.emergency.hold_elapsed = 0.0
        else:
            ns.emergency.active       = False
            ns.emergency.hold_elapsed = 0.0

    # ------------------------------------------------------------------
    # Green-wave / coordination
    # ------------------------------------------------------------------

    def _wave_active(self, ns: _NodeState, sim_time: float) -> bool:
        if ns.wave_hint is None:
            return False
        time_to_arrival = ns.wave_hint.eta - sim_time
        return -WAVE_WINDOW / 2.0 <= time_to_arrival <= WAVE_WINDOW

    def _emit_coordination(self, ns: _NodeState, sim_time: float) -> None:
        """
        Coordination rules
        ------------------
        int_A enters EW_GREEN  -> hard bias int_B toward EW_GREEN after WAVE_TRIGGER_DELAY
        int_B enters EW_GREEN  -> soft EW hint to int_A and int_C (platoon arriving in TRAVEL_TIME)
        int_A/C enter NS_GREEN -> soft EW hint to int_B (clearing EW, platoon en route)
        """
        state = ns.state
        tl_id = ns.tl_id

        if state == _State.EW_GREEN:
            if tl_id == "int_A":
                # Hard trigger: push int_B to EW_GREEN after WAVE_TRIGGER_DELAY seconds
                self._nodes["int_B"].ew_bias_after = sim_time + WAVE_TRIGGER_DELAY

            elif tl_id == "int_B":
                # Soft hints to the terminal nodes
                eta = sim_time + TRAVEL_TIME
                self._nodes["int_A"].wave_hint = _WaveHint(eta=eta, placed_at=sim_time)
                self._nodes["int_C"].wave_hint = _WaveHint(eta=eta, placed_at=sim_time)

        elif state == _State.NS_GREEN:
            if tl_id in ("int_A", "int_C"):
                # EW traffic was just stopped; platoon already moving toward int_B
                eta = sim_time + TRAVEL_TIME
                self._nodes["int_B"].wave_hint = _WaveHint(eta=eta, placed_at=sim_time)

    # ------------------------------------------------------------------
    # SUMO phase application
    # ------------------------------------------------------------------

    def _apply_phase(self, ns: _NodeState) -> None:
        phase_idx = _STATE_PHASE[ns.state]
        try:
            self.env.set_phase_at(ns.tl_id, phase_idx)
        except Exception:
            try:
                self.env.set_phase_at(ns.tl_id, phase_idx % 2)
            except Exception:
                pass
