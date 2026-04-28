"""
FixedController — time-based traffic light controller for 3-intersection network.

All three nodes (int_A, int_B, int_C) are driven on the same rigid schedule:
  Phase 0 — North/South GREEN   (30 s)
  Phase 1 — North/South YELLOW  ( 3 s)   ← matches SUMO net.xml and SmartController
  Phase 2 — East/West   GREEN   (30 s)
  Phase 3 — East/West   YELLOW  ( 3 s)   ← matches SUMO net.xml and SmartController

env.set_phase() broadcasts the same phase index to all three TL nodes
simultaneously, so no per-node logic is needed here.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.traffic_env import TrafficEnv, NetworkState


# ---------------------------------------------------------------------------
# Phase schedule
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Phase:
    index: int
    name: str
    duration: float   # seconds


PHASES: list[Phase] = [
    Phase(index=0, name="NS_GREEN",  duration=30.0),
    Phase(index=1, name="NS_YELLOW", duration=3.0),   # matches SUMO net.xml and SmartController
    Phase(index=2, name="EW_GREEN",  duration=30.0),
    Phase(index=3, name="EW_YELLOW", duration=3.0),   # matches SUMO net.xml and SmartController
]

CYCLE_LENGTH: float = sum(p.duration for p in PHASES)   # 70 s


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------

class FixedController:
    """
    Drives all three traffic light nodes on a fixed 30 s green / 5 s yellow
    cycle.  All nodes receive the same phase command every step.

    Usage
    -----
    ctrl = FixedController(env)
    ctrl.reset()
    while not env.is_done:
        state = env.step()        # NetworkState (all 3 intersections)
        action = ctrl.update(state)
    """

    def __init__(self, env: "TrafficEnv"):
        self.env = env
        self._phase_idx: int = 0
        self._phase_elapsed: float = 0.0
        self._total_steps: int = 0
        self._phase_changes: int = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset to phase 0 and broadcast to all three TL nodes."""
        self._phase_idx = 0
        self._phase_elapsed = 0.0
        self._total_steps = 0
        self._phase_changes = 0
        self.env.set_phase(PHASES[0].index)

    def update(self, state: "NetworkState") -> dict:
        """
        Advance the internal clock and switch phase when scheduled.
        Broadcasts phase changes to all three nodes via env.set_phase().
        Returns a dict describing the step action.
        """
        dt = self.env.step_length
        self._phase_elapsed += dt
        self._total_steps += 1

        current = PHASES[self._phase_idx]
        action = {
            "state":   current.name,
            "phase":   current.name,
            "switched": False,
            "reason":  "hold",
        }

        if self._phase_elapsed >= current.duration:
            self._advance_phase()
            action["switched"]  = True
            action["new_phase"] = PHASES[self._phase_idx].name
            action["state"]     = PHASES[self._phase_idx].name
            action["reason"]    = "fixed_cycle"

        # Per-intersection phases from live state (informational only)
        action["intA_phase"] = state.intersections["int_A"].phase_index
        action["intB_phase"] = state.intersections["int_B"].phase_index
        action["intC_phase"] = state.intersections["int_C"].phase_index

        return action

    # ------------------------------------------------------------------
    # Properties / diagnostics
    # ------------------------------------------------------------------

    @property
    def current_phase(self) -> Phase:
        return PHASES[self._phase_idx]

    @property
    def time_in_phase(self) -> float:
        return self._phase_elapsed

    @property
    def time_remaining(self) -> float:
        return max(0.0, self.current_phase.duration - self._phase_elapsed)

    def summary(self) -> dict:
        return {
            "total_steps":    self._total_steps,
            "phase_changes":  self._phase_changes,
            "current_phase":  self.current_phase.name,
            "time_in_phase":  round(self._phase_elapsed, 1),
            "time_remaining": round(self.time_remaining, 1),
            "cycle_length_s": CYCLE_LENGTH,
            "nodes_controlled": "int_A, int_B, int_C (synchronized)",
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _advance_phase(self) -> None:
        self._phase_idx = (self._phase_idx + 1) % len(PHASES)
        self._phase_elapsed = 0.0
        self._phase_changes += 1
        self.env.set_phase(PHASES[self._phase_idx].index)
