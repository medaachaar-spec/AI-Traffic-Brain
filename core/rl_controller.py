"""
RLController - tabular Q-learning traffic controller for the 3-intersection network.

State representation (v6 — axis-aggregated + phase bits)
---------------------------------------------------------
A flat 11-element integer tuple.  Per-approach counts are aggregated by
traffic axis (NS vs EW) before binning.  Three phase bits (one per
intersection) make each state unambiguous — solving the aliasing problem
that caused imitation learning to write conflicting Q-values.
Practical state space: 3^6 × 2^5 = 23,328 states × 8 actions = 186,624
Q-table entries — reachable within 100 training episodes.

  [0]  A_NS    — _bin_axis(north_in + south_in at int_A)  {0,1,2}
  [1]  A_EW    — _bin_axis(west_in at int_A)              {0,1,2}
  [2]  B_NS    — _bin_axis(north_in + south_in at int_B)  {0,1,2}
  [3]  B_EW    — _bin_axis(east_in  + west_in  at int_B)  {0,1,2}
  [4]  B_inside — _bin_b_inside(moving vehicles in int_B) {0,1}
  [5]  C_NS    — _bin_axis(north_in + south_in at int_C)  {0,1,2}
  [6]  C_EW    — _bin_axis(east_in at int_C)              {0,1,2}
  [7]  emergency — 1 if any emergency vehicle present      {0,1}
  [8]  A_phase — _bin_phase(int_A SUMO phase_index)       {0=NS, 1=EW}
  [9]  B_phase — _bin_phase(int_B SUMO phase_index)       {0=NS, 1=EW}
  [10] C_phase — _bin_phase(int_C SUMO phase_index)       {0=NS, 1=EW}

  _bin_axis thresholds (raw vehicle sum on axis):
    0  light    — 0–4 vehicles
    1  moderate — 5–9 vehicles
    2  heavy    — 10+ vehicles

  _bin_b_inside threshold:
    0  safe      — 0–4 moving vehicles inside roundabout
    1  congested — 5+ moving vehicles inside roundabout

  _bin_phase mapping (SUMO phase_index → binary):
    0 (NS_GREEN)  → 0
    1 (NS_YELLOW) → 0  (yellow follows NS_GREEN; previous green was NS)
    2 (EW_GREEN)  → 1
    3 (EW_YELLOW) → 1  (yellow follows EW_GREEN; previous green was EW)

Action space (v2 — unchanged)
------------------------------
Each intersection receives a desired-green-phase directive (0 or 1):
  int_A  0 = NS_GREEN   1 = EW_GREEN
  int_B  0 = EW_GREEN   1 = NS_GREEN
  int_C  0 = NS_GREEN   1 = EW_GREEN

Joint action: 3-tuple, e.g. (0, 1, 0).  Total: 2³ = 8 combinations.

Reward (v4 — scaled for stability)
------------------------------------
  r = throughput        *  10.0    (cars that exited the sim this step)
    + queue_improvement *  15.0    (queue shrank vs previous step)
    - roundabout_overflow * 5.0    (B_inside > 8)
    + emergency_cleared * 100.0    (emergency vehicle just cleared)
    - starvation_penalty * 10.0    (count of approaches with wait > 120 s)
  Normalised by dividing by 100 → range roughly -10 … +10 per step.

Anti-oscillation
----------------
  MIN_GREEN = 8 s: RL cannot switch a green phase until 8 s have elapsed.

Hybrid confidence
-----------------
  HYBRID_CONFIDENCE_THRESHOLD: the max Q-value above which RL overrides Smart.

Q-update (Bellman):
  Q(s,a) ← Q(s,a) + α · (r + γ · max_a′ Q(s′,a′) − Q(s,a))

Persistence
  Q-table pickled to/from qtable_path (default: data/qtable.pkl).
  Compatibility check: Q-tables built with a different state length or with
  float-encoded states (v3) are detected and discarded automatically.
"""

from __future__ import annotations

import logging
import math
import os
import pickle
import random
from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.traffic_env import TrafficEnv, NetworkState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hyper-parameters
# ---------------------------------------------------------------------------

ALPHA     = 0.1    # learning rate
GAMMA     = 0.95   # discount factor
EPS_START = 0.9    # initial exploration rate
EPS_MIN   = 0.01   # floor for exploration
EPS_DECAY = 0.98   # multiplicative decay per episode

MIN_GREEN = 8.0    # s — minimum time on a green phase before switching (anti-oscillation)

# Reward weights
W_THROUGHPUT          =  10.0   # cars passed this step
W_QUEUE_IMPROVEMENT   =  15.0   # queue reduction bonus
W_ROUNDABOUT_OVERFLOW =   5.0   # B_inside > 8 is dangerous
W_EMERGENCY_CLEARED   = 100.0   # emergency vehicle just passed
W_STARVATION          =  10.0   # approach waiting > 120 s

STARVATION_THRESHOLD  = 500.0   # s — waiting time that triggers starvation penalty
OVERFLOW_THRESHOLD    =   8     # vehicles — B_inside above this = overflow

W_SWITCH_PENALTY      =   2.0   # cost subtracted from reward each time RL triggers a phase switch
W_QUEUE_PENALTY       =   0.1   # cost per queued vehicle across all approaches (direct congestion signal)

REWARD_BASELINE_WINDOW = 100    # steps in the moving-average baseline (advantage-like normalisation)

# Hybrid mode: RL overrides Smart when max Q-value exceeds this threshold
HYBRID_CONFIDENCE_THRESHOLD = 2.0

# Imitation learning: stable bootstrap constants (avoids brittle hard-coded spikes)
PRETRAIN_INIT      =  5.0   # first-visit Q-value for a Smart (state, action) pair
PRETRAIN_INCREMENT =  0.5   # per-revisit additive increment for Smart (state, action)
PRETRAIN_CAP       = 20.0   # upper cap on imitation Q-values
PRETRAIN_OTHER     =  0.0   # initial Q for non-Smart actions in visited states

# State encoding
_STATE_LEN = 11    # elements in encoded state tuple (v6: axis-aggregated + phase bits)

# Phase indices (matches SUMO programme for all three nodes)
PHASE_NS_GREEN  = 0
PHASE_NS_YELLOW = 1
PHASE_EW_GREEN  = 2
PHASE_EW_YELLOW = 3

_GREEN_PHASES = {PHASE_NS_GREEN, PHASE_EW_GREEN}

_TL_ORDER = ["int_A", "int_B", "int_C"]

# ---------------------------------------------------------------------------
# Action semantics
# ---------------------------------------------------------------------------

_ACTION_PHASE: dict[str, dict[int, int]] = {
    "int_A": {0: PHASE_NS_GREEN, 1: PHASE_EW_GREEN},
    "int_B": {0: PHASE_EW_GREEN, 1: PHASE_NS_GREEN},
    "int_C": {0: PHASE_NS_GREEN, 1: PHASE_EW_GREEN},
}

_PHASE_TO_ACTION: dict[str, dict[int, int]] = {
    tl: {v: k for k, v in mapping.items()}
    for tl, mapping in _ACTION_PHASE.items()
}

# ---------------------------------------------------------------------------
# State encoding — v5 axis-aggregated, coarse
# ---------------------------------------------------------------------------

def _bin_axis(total: float) -> int:
    """
    Map the total vehicle count on one traffic axis (sum of all approaches
    on that axis) to a 3-level load indicator:
      0  light    — 0–4 vehicles
      1  moderate — 5–9 vehicles
      2  heavy    — 10+ vehicles
    """
    if total <= 4:
        return 0
    if total <= 9:
        return 1
    return 2


def _bin_b_inside(n: float) -> int:
    """
    Map moving-vehicle count inside the int_B roundabout to a binary
    congestion flag:
      0  safe      — 0–4 moving vehicles
      1  congested — 5+ moving vehicles
    """
    return 1 if n >= 5 else 0


def _bin_phase(phase_index: int) -> int:
    """
    Map a SUMO phase index to a binary green-direction flag.
    Phases 0 and 1 (NS_GREEN, NS_YELLOW) → 0  (NS is or was green)
    Phases 2 and 3 (EW_GREEN, EW_YELLOW) → 1  (EW is or was green)
    Yellow phases are mapped to the preceding green so the bit captures
    which axis was green before the transition started.
    """
    return 0 if phase_index < 2 else 1


def _encode_state(net_state: "NetworkState") -> tuple:
    """
    Encode full network state as an 11-element integer tuple.
    Axes are aggregated per intersection to keep the state space small.
    Three binary phase bits (one per intersection) resolve the aliasing
    problem: the same traffic load at different phases now maps to
    different states, giving imitation learning and Q-updates a
    coherent, unambiguous policy to learn from.
    Practical state space: 3^6 × 2^5 = 23,328 states.
    """
    iA = net_state.intersections["int_A"]
    iB = net_state.intersections["int_B"]
    iC = net_state.intersections["int_C"]

    # ── int_A: NS axis vs EW axis ─────────────────────────────────────────────
    a_ns = (iA.approaches["north_in"]["vehicle_count"]
            + iA.approaches["south_in"]["vehicle_count"])
    a_ew =  iA.approaches["west_in"]["vehicle_count"]

    # ── int_B: NS axis vs EW axis + inside congestion ────────────────────────
    b_ns = (iB.approaches["north_in"]["vehicle_count"]
            + iB.approaches["south_in"]["vehicle_count"])
    b_ew = (iB.approaches["east_in"]["vehicle_count"]
            + iB.approaches["west_in"]["vehicle_count"])
    b_total_veh  = b_ns + b_ew
    b_total_halt = sum(ap["halting_count"] for ap in iB.approaches.values())
    b_inside     = max(0, b_total_veh - b_total_halt)

    # ── int_C: NS axis vs EW axis ─────────────────────────────────────────────
    c_ns = (iC.approaches["north_in"]["vehicle_count"]
            + iC.approaches["south_in"]["vehicle_count"])
    c_ew =  iC.approaches["east_in"]["vehicle_count"]

    # ── Global ────────────────────────────────────────────────────────────────
    emergency = 1 if any(
        ap["has_emergency"]
        for idata in net_state.intersections.values()
        for ap in idata.approaches.values()
    ) else 0

    # ── Phase bits (v6) — one per intersection ────────────────────────────────
    a_phase = _bin_phase(iA.phase_index)
    b_phase = _bin_phase(iB.phase_index)
    c_phase = _bin_phase(iC.phase_index)

    return (
        _bin_axis(a_ns),
        _bin_axis(a_ew),
        _bin_axis(b_ns),
        _bin_axis(b_ew),
        _bin_b_inside(b_inside),
        _bin_axis(c_ns),
        _bin_axis(c_ew),
        emergency,
        a_phase,
        b_phase,
        c_phase,
    )


def _all_actions() -> list[tuple[int, int, int]]:
    """All 8 joint actions."""
    return [(a, b, c) for a in (0, 1) for b in (0, 1) for c in (0, 1)]


_ACTION_SPACE = _all_actions()


def _smart_to_rl_action(smart_nodes: dict) -> tuple:
    """
    Convert SmartController per-node FSM states to the equivalent RL joint-action.

    Mapping logic
    -------------
    Each intersection's FSM state maps to the SUMO phase it *currently holds*
    (for green states) or is *transitioning into* (for yellow states):

      NS_GREEN  → PHASE_NS_GREEN  → RL digit that requests NS_GREEN for this node
      EW_GREEN  → PHASE_EW_GREEN  → RL digit that requests EW_GREEN for this node
      NS_YELLOW → PHASE_EW_GREEN  (yellow ends → next green is EW)
      EW_YELLOW → PHASE_NS_GREEN  (yellow ends → next green is NS)

    The target SUMO phase is looked up in _PHASE_TO_ACTION to get the RL digit
    (0 or 1) for that node.  Three digits are assembled into a 3-tuple.

    Falls back to digit 0 for any unrecognised FSM state, so no step is lost.

    Returns
    -------
    3-tuple (digit_A, digit_B, digit_C), each ∈ {0, 1}.
    """
    from core.smart_controller import _State

    _FSM_TARGET_PHASE: dict = {
        _State.NS_GREEN:  PHASE_NS_GREEN,
        _State.EW_GREEN:  PHASE_EW_GREEN,
        _State.NS_YELLOW: PHASE_EW_GREEN,   # yellow ends → next green is EW
        _State.EW_YELLOW: PHASE_NS_GREEN,   # yellow ends → next green is NS
    }

    result: list[int] = []
    for tl_id in _TL_ORDER:
        node_state   = smart_nodes[tl_id].state
        target_phase = _FSM_TARGET_PHASE.get(node_state, PHASE_NS_GREEN)
        action_digit = _PHASE_TO_ACTION[tl_id].get(target_phase, 0)
        result.append(action_digit)

    return tuple(result)


# ---------------------------------------------------------------------------
# Reward — v3 shaped to beat Smart
# ---------------------------------------------------------------------------

def _compute_reward(
    net_state: "NetworkState",
    prev_emergency:   int,
    prev_total_queue: int,
) -> tuple[float, int, int]:
    """
    Multi-component shaped reward.

    Returns
    -------
    (reward, current_emergency_count, current_total_queue)
    """
    try:
        import traci as _traci
        cars_passed = _traci.simulation.getArrivedNumber()
    except Exception:
        cars_passed = 0

    curr_queue      = 0
    starvation_pen  = 0.0
    current_emg     = 0

    # Roundabout overflow: moving vehicles inside int_B
    iB           = net_state.intersections["int_B"]
    b_total_veh  = sum(ap["vehicle_count"] for ap in iB.approaches.values())
    b_total_halt = sum(ap["halting_count"]  for ap in iB.approaches.values())
    b_inside     = max(0, b_total_veh - b_total_halt)
    overflow     = 1 if b_inside > OVERFLOW_THRESHOLD else 0

    for idata in net_state.intersections.values():
        for ap in idata.approaches.values():
            vc = ap["vehicle_count"]
            hc = ap["halting_count"]
            wt = ap["waiting_time"]

            curr_queue    += vc

            if wt > STARVATION_THRESHOLD:
                starvation_pen += 1.0

            for lane in ap["lanes"].values():
                if lane.has_emergency:
                    current_emg += 1

    queue_improvement = prev_total_queue - curr_queue
    cleared           = max(0, prev_emergency - current_emg)

    reward = (
          cars_passed       * W_THROUGHPUT
        + queue_improvement * W_QUEUE_IMPROVEMENT
        - overflow          * W_ROUNDABOUT_OVERFLOW
        + cleared           * W_EMERGENCY_CLEARED
        - starvation_pen    * W_STARVATION
        - curr_queue        * W_QUEUE_PENALTY        # direct congestion penalty
    )

    reward /= 100.0   # scale to ~-10 … +10 per step; keeps differences meaningful

    return reward, current_emg, curr_queue


# ---------------------------------------------------------------------------
# Module-level helper
# ---------------------------------------------------------------------------

def _try_unlink(path: "Path") -> None:
    """Delete a file silently (used for temp-file cleanup)."""
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------

class RLController:
    """
    Tabular Q-learning controller for all 3 intersections (v3).

    Uses normalized float state encoding for 10× more resolution than v2 bins.
    Inference mode (training=False): epsilon fixed at EPS_MIN.
    Training mode  (training=True):  epsilon decays from EPS_START.
    """

    def __init__(
        self,
        env:          "TrafficEnv",
        qtable_path:  str | Path = "data/qtable.pkl",
        training:     bool       = False,
    ):
        self.env         = env
        self.qtable_path = Path(qtable_path)
        self.training    = training

        self._qtable:  dict[tuple, float] = {}
        self._epsilon: float = EPS_START if training else EPS_MIN

        # Per-step tracking
        self._elapsed:          dict[str, float] = {}
        self._prev_state:       tuple | None     = None
        self._prev_action:      tuple | None     = None
        self._prev_emergency:   int              = 0
        self._prev_total_queue: int              = 0
        self._prev_switched:    bool             = False
        self._total_steps:      int              = 0
        self._episode_reward:   float            = 0.0

        # Running reward baseline (cross-episode moving average for advantage-like updates)
        self._reward_window: deque = deque(maxlen=REWARD_BASELINE_WINDOW)

        # Cumulative diagnostics
        self._phase_changes: int   = 0
        self._total_reward:  float = 0.0

        self._load_qtable()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset per-episode state. Call before each simulation episode."""
        self._elapsed          = {tl_id: 0.0 for tl_id in _TL_ORDER}
        self._prev_state       = None
        self._prev_action      = None
        self._prev_emergency   = 0
        self._prev_total_queue = 0
        self._prev_switched    = False
        self._total_steps      = 0
        self._episode_reward   = 0.0
        for tl_id in _TL_ORDER:
            try:
                self.env.set_phase_at(tl_id, PHASE_NS_GREEN)
            except Exception:
                pass

    def update(self, net_state: "NetworkState") -> dict:
        """
        One control step. Encodes state, computes reward, performs Q-update
        (training only), selects and applies action.

        Returns a dict compatible with main.py's CSV logger.
        """
        dt = self.env.step_length
        self._total_steps += 1

        for tl_id in _TL_ORDER:
            if net_state.intersections[tl_id].phase_index in _GREEN_PHASES:
                self._elapsed[tl_id] = self._elapsed.get(tl_id, 0.0) + dt

        s = _encode_state(net_state)

        reward, current_emg, curr_queue = _compute_reward(
            net_state, self._prev_emergency, self._prev_total_queue
        )

        # Switching penalty: charged to the action taken in the previous step
        # that caused one or more phase transitions. This discourages unnecessary
        # oscillation without blocking valid switches.
        if self._prev_switched:
            reward -= W_SWITCH_PENALTY

        # Reward baseline: subtract the running mean so Q-updates learn
        # *relative* improvement rather than fighting a noisy absolute signal.
        # The window is cross-episode so it stabilises quickly across runs.
        # Raw reward is kept for diagnostics; only the Q-update uses the centred value.
        self._reward_window.append(reward)
        avg_reward   = sum(self._reward_window) / len(self._reward_window)
        reward_delta = reward - avg_reward

        self._episode_reward  += reward
        self._total_reward    += reward

        if self.training and self._prev_state is not None:
            self._q_update(self._prev_state, self._prev_action, reward_delta, s)

        self._prev_emergency   = current_emg
        self._prev_total_queue = curr_queue

        raw_action = self._choose_action(s)
        action     = self._apply_min_green(raw_action, net_state)

        switched_nodes = self._apply_action(action, net_state)
        self._prev_switched = bool(switched_nodes)

        for tl_id in switched_nodes:
            self._elapsed[tl_id] = 0.0

        self._prev_state  = s
        self._prev_action = action

        iB = net_state.intersections["int_B"]
        return {
            "state":          f"phase_{iB.phase_index}",
            "phase":          f"phase_{iB.phase_index}",
            "switched":       bool(switched_nodes),
            "reason":         "rl_policy_v3",
            "action":         action,
            "reward":         round(reward, 2),
            "epsilon":        round(self._epsilon, 4),
            "episode_reward": round(self._episode_reward, 1),
            "intA_phase":     net_state.intersections["int_A"].phase_index,
            "intB_phase":     iB.phase_index,
            "intC_phase":     net_state.intersections["int_C"].phase_index,
        }

    # ------------------------------------------------------------------
    # Diagnosis: compare RL decision vs Smart decision
    # ------------------------------------------------------------------

    def compare_decision(
        self, net_state: "NetworkState", smart_controller
    ) -> dict:
        """
        For a given network state, compare what Smart is doing vs what RL
        would do. Used by HybridController to decide when to override.

        Parameters
        ----------
        net_state       : current NetworkState from env.step()
        smart_controller: SmartController instance (after its update() ran)

        Returns
        -------
        dict with keys:
          encoded_state  — normalized float tuple passed to Q-table
          rl_action      — best 3-tuple action from Q-table
          rl_phases      — desired SUMO phase per tl_id
          smart_phases   — current FSM phase per tl_id from SmartController
          max_q_value    — max Q-value across all actions (confidence signal)
          agreement      — per-tl_id bool: RL and Smart agree?
          would_override — True if RL disagrees with Smart on >= 1 node
        """
        from core.smart_controller import _STATE_PHASE as _SMART_STATE_PHASE

        s       = _encode_state(net_state)
        rl_act  = self._best_action(s)
        max_q   = self._max_q_value(s)

        rl_phases = {
            tl_id: _ACTION_PHASE[tl_id][rl_act[i]]
            for i, tl_id in enumerate(_TL_ORDER)
        }

        smart_phases = {
            tl_id: _SMART_STATE_PHASE[ns.state]
            for tl_id, ns in smart_controller._nodes.items()
        }

        agreement = {
            tl_id: (rl_phases[tl_id] == smart_phases[tl_id])
            for tl_id in _TL_ORDER
        }

        return {
            "encoded_state":  s,
            "rl_action":      rl_act,
            "rl_phases":      rl_phases,
            "smart_phases":   smart_phases,
            "max_q_value":    round(max_q, 3),
            "agreement":      agreement,
            "would_override": not all(agreement.values()),
        }

    # ------------------------------------------------------------------
    # Imitation learning warm-start
    # ------------------------------------------------------------------

    def pretrain_from_smart(
        self,
        episodes: int = 5,
        cfg: str | None = None,
    ) -> None:
        """
        Imitation learning warm-start using SmartController as the expert.

        Runs ``episodes`` full simulation episodes driven entirely by
        SmartController.  At every step:
          1. The current NetworkState is encoded with RL's own state encoder.
          2. Smart's active green directive per intersection is converted to
             the equivalent RL joint-action tuple.
          3. The Q-table entry (state, smart_action) is seeded to
             +PRETRAIN_Q_VALUE (10.0) **only if the entry is absent** — so
             real Bellman updates from subsequent training() calls will
             overwrite the seed naturally.

        Yellow-phase steps are mapped to the green the intersection is
        transitioning *into* (NS_YELLOW → EW_GREEN action; EW_YELLOW →
        NS_GREEN action) so every step produces a valid (s, a) pair.

        Call this BEFORE train() to give RL a Smart-level warm baseline
        instead of starting from an all-zero Q-table.

        Seeding strategy (stable bootstrap)
        ------------------------------------
        For each observed (state, smart_action) pair:
          - First visit : Q(s, a) = PRETRAIN_INIT  (+5)
          - Revisit     : Q(s, a) += PRETRAIN_INCREMENT (+0.5), capped at PRETRAIN_CAP (+20)
        For all other actions in the same visited state:
          - If unseen   : Q(s, other) = PRETRAIN_OTHER (0.0)   — gently lower, not negative

        The Smart-to-RL action mapping is handled by _smart_to_rl_action().
        """
        from core.smart_controller import SmartController

        if cfg is not None:
            self.env.sumo_cfg = str(Path(cfg).resolve())

        import traci

        logger.info(
            "Imitation pretraining: %d episodes with SmartController "
            "→ init=+%.1f  increment=+%.1f  cap=+%.1f  other=%.1f",
            episodes, PRETRAIN_INIT, PRETRAIN_INCREMENT, PRETRAIN_CAP, PRETRAIN_OTHER,
        )

        total_steps = 0
        new_entries = 0
        base_seed = self.env.seed

        for ep in range(1, episodes + 1):
            self.env.seed = base_seed + ep - 1   # unique traffic pattern per episode
            smart = SmartController(self.env)
            self.env.start()
            smart.reset()

            step = 0
            try:
                while True:
                    net_state    = self.env.step()
                    step        += 1
                    total_steps += 1

                    # Encode state with RL's encoder BEFORE Smart acts
                    s = _encode_state(net_state)

                    # Smart decides and applies phases to SUMO
                    smart.update(net_state)

                    # Convert Smart's FSM states → RL joint-action via helper
                    smart_action = _smart_to_rl_action(smart._nodes)  # e.g. (0, 1, 0)

                    # ── Stable imitation bootstrap ────────────────────────────────────
                    # Smart (state, action): gentle increment, capped — avoids hard spikes
                    key = (s, smart_action)
                    if key not in self._qtable:
                        self._qtable[key] = PRETRAIN_INIT          # +5 first visit
                        new_entries += 1
                    else:
                        self._qtable[key] = min(
                            self._qtable[key] + PRETRAIN_INCREMENT,  # +0.5 per revisit
                            PRETRAIN_CAP,                            # cap at +20
                        )

                    # Non-Smart actions: initialize lower but NOT hard-negative
                    for alt in _ACTION_SPACE:
                        if alt == smart_action:
                            continue
                        alt_key = (s, alt)
                        if alt_key not in self._qtable:
                            self._qtable[alt_key] = PRETRAIN_OTHER  # 0.0

                    if traci.simulation.getMinExpectedNumber() == 0:
                        break

            except Exception as exc:
                logger.warning(
                    "Pretrain episode %d aborted at step %d: %s", ep, step, exc
                )
            finally:
                self.env.close()

            logger.info(
                "Pretrain ep %2d/%d | steps=%4d | new_entries=%5d | qtable=%5d",
                ep, episodes, step, new_entries, len(self._qtable),
            )

        self._save_qtable()
        logger.info(
            "Pretraining complete. Q-table: %d entries seeded "
            "(%d total steps observed).",
            len(self._qtable), total_steps,
        )

    # ------------------------------------------------------------------
    # Training loop
    # ------------------------------------------------------------------

    def train(self, episodes: int = 50, cfg: str | None = None) -> None:
        """Run `episodes` full simulation episodes; save Q-table after each."""
        if cfg is not None:
            self.env.sumo_cfg = str(Path(cfg).resolve())

        self.training = True
        self._epsilon = EPS_START

        import traci

        logger.info(
            "RL training started: %d episodes, eps=%.2f -> %.2f",
            episodes, EPS_START, EPS_MIN,
        )

        base_seed = self.env.seed
        for ep in range(1, episodes + 1):
            ep_start    = __import__("time").perf_counter()
            self.env.seed = base_seed + ep - 1   # unique traffic pattern per episode
            self.env.start()
            self.reset()

            step        = 0
            ep_reward   = 0.0
            ep_switches = 0

            try:
                while True:
                    net_state = self.env.step()
                    act_dict  = self.update(net_state)

                    ep_reward   += act_dict["reward"]
                    ep_switches += sum(act_dict["action"])
                    step        += 1

                    if traci.simulation.getMinExpectedNumber() == 0:
                        break
            except Exception as exc:
                logger.warning("Episode %d aborted at step %d: %s", ep, step, exc)
            finally:
                self.env.close()

            self._epsilon = max(EPS_MIN, self._epsilon * EPS_DECAY)

            ep_elapsed = __import__("time").perf_counter() - ep_start
            logger.info(
                "Episode %3d/%d | steps=%4d | reward=%10.1f | "
                "switches=%4d | eps=%.4f | wall=%.1fs | qtable=%d",
                ep, episodes, step, ep_reward,
                ep_switches, self._epsilon,
                ep_elapsed, len(self._qtable),
            )

            self._save_qtable()

        self.training = False
        logger.info("Training complete. Q-table entries: %d", len(self._qtable))

    # ------------------------------------------------------------------
    # Properties / diagnostics
    # ------------------------------------------------------------------

    @property
    def current_phase(self) -> int:
        return self.env.get_phase("int_B")

    def summary(self) -> dict:
        return {
            "total_steps":    self._total_steps,
            "phase_changes":  self._phase_changes,
            "total_reward":   round(self._total_reward, 1),
            "epsilon":        round(self._epsilon, 4),
            "qtable_entries": len(self._qtable),
            "qtable_path":    str(self.qtable_path),
        }

    # ------------------------------------------------------------------
    # Q-learning core
    # ------------------------------------------------------------------

    def _q(self, state: tuple, action: tuple) -> float:
        return self._qtable.get((state, action), 0.0)

    def _max_q_value(self, state: tuple) -> float:
        """Return the maximum Q-value across all actions (RL confidence signal)."""
        return max(self._q(state, a) for a in _ACTION_SPACE)

    def _best_action(self, state: tuple) -> tuple:
        best_val = -math.inf
        best_act = _ACTION_SPACE[0]
        for act in _ACTION_SPACE:
            val = self._q(state, act)
            if val > best_val:
                best_val = val
                best_act = act
        return best_act

    def _choose_action(self, state: tuple) -> tuple:
        if random.random() < self._epsilon:
            return random.choice(_ACTION_SPACE)
        return self._best_action(state)

    def _q_update(
        self, s: tuple, a: tuple, reward: float, s_next: tuple
    ) -> None:
        best_next = max(self._q(s_next, a2) for a2 in _ACTION_SPACE)
        old       = self._q(s, a)
        new       = old + ALPHA * (reward + GAMMA * best_next - old)
        self._qtable[(s, a)] = new

    # ------------------------------------------------------------------
    # Min-green enforcement (anti-oscillation)
    # ------------------------------------------------------------------

    def _apply_min_green(
        self, action: tuple[int, int, int], net_state: "NetworkState"
    ) -> tuple[int, int, int]:
        """
        Override any switch action on an intersection that hasn't yet served
        MIN_GREEN (8 s) on its current green phase.  Also suppresses switch
        requests while an intersection is in yellow.
        """
        result = list(action)
        for i, tl_id in enumerate(_TL_ORDER):
            current_phase = net_state.intersections[tl_id].phase_index
            target_phase  = _ACTION_PHASE[tl_id][result[i]]

            if current_phase == target_phase:
                continue

            if current_phase not in _GREEN_PHASES:
                dest_green = (
                    PHASE_EW_GREEN if current_phase == PHASE_NS_YELLOW
                    else PHASE_NS_GREEN
                )
                result[i] = _PHASE_TO_ACTION[tl_id].get(dest_green, result[i])
                continue

            if self._elapsed.get(tl_id, 0.0) < MIN_GREEN:
                result[i] = _PHASE_TO_ACTION[tl_id][current_phase]

        return tuple(result)  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # SUMO phase application
    # ------------------------------------------------------------------

    def _apply_action(
        self, action: tuple[int, int, int], net_state: "NetworkState"
    ) -> list[str]:
        """
        Apply desired-phase actions to SUMO. When the target phase differs
        from the current phase, initiate a yellow transition.

        Returns list of tl_ids where a transition was initiated this step.
        """
        switched = []
        for tl_id, desired_dir in zip(_TL_ORDER, action):
            target_phase  = _ACTION_PHASE[tl_id][desired_dir]
            current_phase = net_state.intersections[tl_id].phase_index

            if current_phase == target_phase:
                continue

            if current_phase not in _GREEN_PHASES:
                continue

            yellow_phase = (
                PHASE_NS_YELLOW if current_phase == PHASE_NS_GREEN
                else PHASE_EW_YELLOW
            )
            try:
                self.env.set_phase_at(tl_id, yellow_phase)
                switched.append(tl_id)
                self._phase_changes += 1
            except Exception as exc:
                logger.debug(
                    "set_phase_at(%s, %d) failed: %s", tl_id, yellow_phase, exc
                )

        return switched

    # ------------------------------------------------------------------
    # Q-table persistence (atomic, Windows-safe)
    # ------------------------------------------------------------------

    def _load_qtable(self) -> None:
        path = self.qtable_path

        if not path.exists():
            logger.info("No Q-table found at %s — starting fresh.", path)
            return

        if path.stat().st_size == 0:
            logger.warning("Q-table %s is 0 bytes — starting fresh.", path)
            return

        try:
            with open(path, "rb") as fh:
                data = pickle.load(fh)
        except EOFError:
            logger.warning(
                "Q-table %s is truncated (EOFError). Starting fresh.", path,
            )
            self._qtable = {}
            return
        except pickle.UnpicklingError as exc:
            logger.error("Q-table %s corrupted (%s). Starting fresh.", path, exc)
            self._qtable = {}
            return
        except Exception as exc:
            logger.error("Q-table load error %s (%s). Starting fresh.", path, exc)
            self._qtable = {}
            return

        if not isinstance(data, dict):
            logger.error("Q-table %s contains %s, not dict. Starting fresh.",
                         path, type(data).__name__)
            self._qtable = {}
            return

        # Compatibility check — state-tuple length and encoding type
        if data:
            sample_key = next(iter(data))
            if (
                not isinstance(sample_key, tuple)
                or len(sample_key) != 2
                or not isinstance(sample_key[0], tuple)
                or len(sample_key[0]) != _STATE_LEN
            ):
                logger.warning(
                    "Q-table %s has wrong state encoding "
                    "(expected len=%d). Discarding and starting fresh.",
                    path, _STATE_LEN,
                )
                self._qtable = {}
                return

            # Detect v3 float-normalized encoding — v5 uses integer bins
            sample_state = sample_key[0]
            if sample_state and isinstance(sample_state[0], float):
                logger.warning(
                    "Q-table %s was built with float-normalized encoding (v3). "
                    "v5 uses integer axis-aggregated bins. Discarding and starting fresh. "
                    "Delete %s to suppress this warning.",
                    path, path.name,
                )
                self._qtable = {}
                return

        self._qtable = data
        print(
            f"[RLController] Q-table loaded: {len(self._qtable):,} entries "
            f"from {path.name}"
        )
        logger.info("Q-table loaded: %d entries from %s", len(self._qtable), path)

    def _save_qtable(self) -> None:
        """
        Atomic, Windows-safe Q-table save.

        1. Serialise to qtable.tmp with fsync.
        2. Promote existing qtable.pkl → qtable.bak.
        3. os.replace() the .tmp over qtable.pkl.
        """
        self.qtable_path.parent.mkdir(parents=True, exist_ok=True)

        tmp = self.qtable_path.with_suffix(".tmp")
        bak = self.qtable_path.with_suffix(".bak")

        try:
            with open(tmp, "wb") as fh:
                pickle.dump(self._qtable, fh, protocol=pickle.HIGHEST_PROTOCOL)
                fh.flush()
                os.fsync(fh.fileno())
        except Exception as exc:
            logger.error("Q-table write failed (%s) — original untouched.", exc)
            _try_unlink(tmp)
            return

        if self.qtable_path.exists() and self.qtable_path.stat().st_size > 0:
            try:
                os.replace(str(self.qtable_path), str(bak))
            except Exception as exc:
                logger.warning("Q-table backup failed (%s) — continuing.", exc)

        try:
            os.replace(str(tmp), str(self.qtable_path))
        except Exception as exc:
            logger.error("Q-table atomic replace failed (%s) — "
                         "temp left at %s.", exc, tmp)
            return

        count = len(self._qtable)
        print(f"[RLController] Q-table saved: {count:,} entries -> {self.qtable_path.name}")
        logger.info("Q-table saved: %d entries -> %s", count, self.qtable_path)
