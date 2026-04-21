"""
VisionBridgeController - SmartController augmented with simulated camera vision.

The bridge sits between the simulation loop and SmartController.  Each step it:

  1. Runs CameraDetector.get_camera_report() for every intersection.
  2. Gates emergency overrides through three filters before acting:
       a. Cooldown guard  — 300 s must have elapsed since the last override at
                            the same intersection.
       b. Confirmation    — emergency must appear in 3 consecutive camera frames
                            before an override is triggered.
       c. Night-mode path — in low-traffic / night conditions a full override is
                            replaced by a 15-second green extension on the
                            emergency vehicle's axis.
  3. While an override is active, re-enforces the target green phase every step
     so SmartController cannot cycle it away.
  4. Automatically cancels any override that has been running for more than
     EMG_MAX_DURATION_S (60 s) and starts the 300 s cooldown.
  5. Attaches full camera reports to the returned action dict.

Usage
-----
  env  = TrafficEnv(...)
  ctrl = VisionBridgeController(env)
  ctrl.reset()

  env.start()
  ctrl.connect_traci(traci)   # call once after env.start()

  while not env.is_done:
      state  = env.step()
      action = ctrl.update(state)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.camera_detector import CameraDetector, CameraReport
from core.smart_controller import SmartController, SWITCH_RATIO

if TYPE_CHECKING:
    from core.traffic_env import TrafficEnv, NetworkState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tuning constants
# ---------------------------------------------------------------------------

EMG_COOLDOWN_S       = 300.0  # s  minimum gap between overrides at one intersection
EMG_CONFIRM_FRAMES   = 3      # consecutive camera frames required before triggering
EMG_MAX_DURATION_S   = 60.0   # s  maximum time the bridge holds an override active
NIGHT_GREEN_EXTEND_S = 15.0   # s  phase-duration extension used in night mode

# When night mode is active the pressure ratio threshold is lowered so
# SmartController switches more freely (informational; logged in summary).
NIGHT_SWITCH_RATIO = 1.2   # vs normal SWITCH_RATIO

# Phase index constants (must match SUMO TL programme / smart_controller.py)
_PHASE_NS_GREEN  = 0
_PHASE_NS_YELLOW = 1
_PHASE_EW_GREEN  = 2
_PHASE_EW_YELLOW = 3
_GREEN_PHASES    = {_PHASE_NS_GREEN, _PHASE_EW_GREEN}

_TL_IDS = ["int_A", "int_B", "int_C"]

# Lane-ID prefix sets used to identify which axis an emergency vehicle is on
_NS_LANE_PREFIXES = ("nA_", "sA_", "nB_", "sB_", "nC_", "sC_")
_EW_LANE_PREFIXES = ("AB_", "BC_")


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------

class VisionBridgeController:
    """
    Camera-aware wrapper around SmartController.

    Parameters
    ----------
    env : TrafficEnv
    smart : SmartController | None
        Optional pre-built SmartController.  If None, one is created internally.
    """

    def __init__(self, env: "TrafficEnv", smart: SmartController | None = None):
        self.env     = env
        self._smart  = smart if smart is not None else SmartController(env)
        self._camera = CameraDetector()
        self._traci  = None

        # Per-intersection override state — initialised properly in reset()
        self._emg_consecutive:    dict[str, int]   = {}
        self._emg_cooldown_until: dict[str, float] = {}
        self._override_active:    dict[str, bool]  = {}
        self._override_started:   dict[str, float] = {}
        self._override_axis:      dict[str, str | None] = {}

        # Session-level diagnostics
        self._emg_overrides_triggered: dict[str, int] = {}
        self._night_extensions:        dict[str, int] = {}
        self._night_steps:  int = 0
        self._total_steps:  int = 0

        self._init_per_tl_dicts()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset internal state and the wrapped SmartController."""
        self._smart.reset()
        self._init_per_tl_dicts()
        self._night_steps = 0
        self._total_steps = 0
        # Keep session diagnostics across resets so summary stays meaningful.

    def _init_per_tl_dicts(self) -> None:
        for tl in _TL_IDS:
            self._emg_consecutive[tl]    = 0
            self._emg_cooldown_until[tl] = 0.0
            self._override_active[tl]    = False
            self._override_started[tl]   = 0.0
            self._override_axis[tl]      = None
            self._emg_overrides_triggered.setdefault(tl, 0)
            self._night_extensions.setdefault(tl, 0)

    def connect_traci(self, traci_module) -> None:
        """Pass a live TraCI module so CameraDetector and phase-duration calls work."""
        self._traci = traci_module
        self._camera.set_traci(traci_module)
        logger.debug("VisionBridgeController: TraCI connected.")

    # ------------------------------------------------------------------
    # Main update
    # ------------------------------------------------------------------

    def update(self, net_state: "NetworkState") -> dict:
        """
        One control step.  Returns the same dict as SmartController.update(),
        plus a 'camera_reports' key with per-intersection camera data.
        """
        sim_time = net_state.sim_time
        self._total_steps += 1

        # 1. Run camera analysis for every intersection
        camera_reports: dict[str, CameraReport] = {
            tl_id: self._camera.get_camera_report(
                tl_id, net_state.intersections[tl_id], sim_time
            )
            for tl_id in _TL_IDS
        }

        # 2. Process new override triggers (gated by cooldown + confirmation)
        self._process_triggers(camera_reports, net_state, sim_time)

        # 3. Run SmartController's normal pressure logic
        action = self._smart.update(net_state)

        # 4. Re-enforce any active overrides (overrides SmartController phase changes)
        self._enforce_active_overrides(net_state, sim_time)

        # 5. Night-mode logging
        any_night = any(r.night_mode for r in camera_reports.values())
        if any_night:
            self._night_steps += 1
            action["night_mode_active"] = True

        # 6. Attach camera summary to action dict
        action["camera_reports"] = {
            tl_id: {
                "total_detected":       r.total_detected,
                "type_breakdown":       r.type_breakdown,
                "emergency_detected":   r.emergency_detected,
                "emergency_confidence": r.emergency_confidence,
                "night_mode":           r.night_mode,
                "avg_density":          r.avg_density,
                "total_waiting":        r.total_waiting,
                "recommended_action":   r.recommended_action,
            }
            for tl_id, r in camera_reports.items()
        }

        # Surface override status in the top-level reason field
        active_overrides = [tl for tl in _TL_IDS if self._override_active[tl]]
        if active_overrides:
            action["reason"] = f"camera_emg_hold({','.join(active_overrides)})"

        return action

    # ------------------------------------------------------------------
    # Standard controller interface
    # ------------------------------------------------------------------

    @property
    def current_phase(self) -> int:
        return self._smart.current_phase

    def summary(self) -> dict:
        smart_s  = self._smart.summary()
        camera_s = self._camera.session_stats()
        cooldowns = {
            tl: round(self._emg_cooldown_until[tl], 1)
            for tl in _TL_IDS
            if self._emg_cooldown_until[tl] > 0
        }
        return {
            **smart_s,
            "vision_total_steps":       self._total_steps,
            "vision_night_steps":       self._night_steps,
            "vision_emg_overrides":     dict(self._emg_overrides_triggered),
            "vision_night_extensions":  dict(self._night_extensions),
            "vision_active_overrides":  {tl: self._override_active[tl] for tl in _TL_IDS},
            "vision_cooldowns_until":   cooldowns,
            "camera_session":           camera_s,
        }

    # ------------------------------------------------------------------
    # Step 2 — Trigger processing (with all guards)
    # ------------------------------------------------------------------

    def _process_triggers(
        self,
        reports: dict[str, CameraReport],
        net_state: "NetworkState",
        sim_time: float,
    ) -> None:
        """
        For each intersection evaluate the camera report and decide whether to
        start an override or a night-mode extension.

        Guards applied in order:
          1. Skip if an override is already active for this node (handled in
             _enforce_active_overrides instead).
          2. Skip if still within the post-override cooldown window.
          3. Require EMG_CONFIRM_FRAMES consecutive detections.
          4. Night-mode path: extend green 15 s instead of full override.
          5. Normal path: trigger full override.
        """
        for tl_id in _TL_IDS:
            report = reports[tl_id]

            # Guard 1: already in an active override — leave it to enforcer
            if self._override_active[tl_id]:
                continue

            # Guard 2: cooldown — reset streak and skip
            if sim_time < self._emg_cooldown_until[tl_id]:
                self._emg_consecutive[tl_id] = 0
                continue

            # Update consecutive counter
            is_candidate = (
                report.recommended_action == "EMERGENCY_OVERRIDE"
                and report.emergency_confidence >= 0.97
            )
            if is_candidate:
                self._emg_consecutive[tl_id] += 1
            else:
                self._emg_consecutive[tl_id] = 0

            # Guard 3: not yet confirmed
            if self._emg_consecutive[tl_id] < EMG_CONFIRM_FRAMES:
                continue

            # Confirmed — identify the axis
            emg_axis = self._locate_emergency_axis(tl_id, report)
            if emg_axis is None:
                continue

            # Reset streak either way (night extension or full override)
            self._emg_consecutive[tl_id] = 0

            # Guard 4 / night-mode path
            if report.night_mode:
                self._apply_night_extension(tl_id, emg_axis, net_state, sim_time)
            else:
                self._start_override(tl_id, emg_axis, net_state, sim_time)

    # ------------------------------------------------------------------
    # Step 4 — Enforce active overrides each step
    # ------------------------------------------------------------------

    def _enforce_active_overrides(
        self,
        net_state: "NetworkState",
        sim_time: float,
    ) -> None:
        """
        For every intersection that has an active override:
          - If the override has exceeded EMG_MAX_DURATION_S (60 s): cancel it
            and start the EMG_COOLDOWN_S (300 s) cooldown.
          - Otherwise: lock the phase to target green so SmartController cannot
            cycle it away.
        """
        for tl_id in _TL_IDS:
            if not self._override_active[tl_id]:
                continue

            elapsed = sim_time - self._override_started[tl_id]

            # --- Max-duration expiry ---
            if elapsed >= EMG_MAX_DURATION_S:
                self._override_active[tl_id]    = False
                self._override_axis[tl_id]      = None
                self._emg_cooldown_until[tl_id] = sim_time + EMG_COOLDOWN_S
                logger.info(
                    "CameraOverride [%s] t=%.0f: expired after %.0f s -> "
                    "cooldown until t=%.0f",
                    tl_id, sim_time, elapsed,
                    self._emg_cooldown_until[tl_id],
                )
                continue

            # --- Hold target green ---
            axis         = self._override_axis[tl_id]
            target_green = _PHASE_NS_GREEN if axis == "NS" else _PHASE_EW_GREEN

            try:
                self.env.set_phase_at(tl_id, target_green)
            except Exception as exc:
                logger.debug(
                    "Override hold failed for %s (phase %d): %s",
                    tl_id, target_green, exc,
                )

    # ------------------------------------------------------------------
    # Override helpers
    # ------------------------------------------------------------------

    def _start_override(
        self,
        tl_id: str,
        emg_axis: str,
        net_state: "NetworkState",
        sim_time: float,
    ) -> None:
        """
        Trigger a full emergency override: immediately apply the target green
        phase and record the override as active.

        If the intersection is currently on the *wrong* green, a direct jump
        to the target green is applied; SUMO accepts mid-cycle phase changes.
        Yellow transitions are bypassed intentionally — emergency clearance takes
        priority over the normal inter-green gap.
        """
        target_green = _PHASE_NS_GREEN if emg_axis == "NS" else _PHASE_EW_GREEN
        try:
            self.env.set_phase_at(tl_id, target_green)
        except Exception as exc:
            logger.warning("Override phase set failed for %s: %s", tl_id, exc)
            return   # don't mark override active if the set failed

        self._override_active[tl_id]  = True
        self._override_started[tl_id] = sim_time
        self._override_axis[tl_id]    = emg_axis
        self._emg_overrides_triggered[tl_id] += 1

        logger.info(
            "CameraOverride [%s] t=%.0f: STARTED (%s green, conf confirmed x%d)",
            tl_id, sim_time, emg_axis, EMG_CONFIRM_FRAMES,
        )

    def _apply_night_extension(
        self,
        tl_id: str,
        emg_axis: str,
        net_state: "NetworkState",
        sim_time: float,
    ) -> None:
        """
        Night-mode alternative to a full override: extend the current green
        phase on the emergency vehicle's axis by NIGHT_GREEN_EXTEND_S (15 s).

        If the intersection is already on the correct green, we simply extend
        its remaining duration.  If it is on the wrong green, we do nothing —
        SmartController will switch it through the normal low-traffic pressure
        path (which is fast because density is already low in night mode).

        No cooldown is started; no override flag is set.  This is a one-shot
        nudge, not a sustained hold.
        """
        target_green  = _PHASE_NS_GREEN if emg_axis == "NS" else _PHASE_EW_GREEN
        current_phase = net_state.intersections[tl_id].phase_index

        if current_phase != target_green:
            logger.debug(
                "NightExtension [%s] t=%.0f: wrong phase (%d vs %d) — skipping",
                tl_id, sim_time, current_phase, target_green,
            )
            return

        if self._traci is not None:
            try:
                self._traci.trafficlight.setPhaseDuration(tl_id, NIGHT_GREEN_EXTEND_S)
                self._night_extensions[tl_id] += 1
                logger.info(
                    "NightExtension [%s] t=%.0f: extended %s green by %.0f s",
                    tl_id, sim_time, emg_axis, NIGHT_GREEN_EXTEND_S,
                )
            except Exception as exc:
                logger.debug(
                    "NightExtension phase-duration set failed for %s: %s", tl_id, exc
                )
        else:
            logger.debug(
                "NightExtension [%s]: TraCI not connected, cannot extend phase", tl_id
            )

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _locate_emergency_axis(tl_id: str, report: CameraReport) -> str | None:
        """
        Determine which traffic axis (NS or EW) the confirmed emergency vehicle
        is on, using the lane_id of each emergency detection.

        Lane-naming convention (NETWORK_APPROACHES in traffic_env.py):
          NS lanes: nA_in_*, sA_in_*, nB_in_*, sB_in_*, nC_in_*, sC_in_*
          EW lanes: AB_east_*, AB_west_*, BC_east_*, BC_west_*
        """
        ns_count = 0
        ew_count = 0

        for det in report.detections:
            if not det.is_emergency:
                continue
            lid = det.lane_id
            if any(lid.startswith(p) for p in _NS_LANE_PREFIXES):
                ns_count += 1
            elif any(lid.startswith(p) for p in _EW_LANE_PREFIXES):
                ew_count += 1

        if ns_count == 0 and ew_count == 0:
            return None
        return "NS" if ns_count >= ew_count else "EW"
