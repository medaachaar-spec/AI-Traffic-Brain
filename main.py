"""
AI-Traffic-Brain - simulation entry point.

Usage
-----
  python main.py --mode fixed          # headless, fixed controller
  python main.py --mode smart          # headless, smart controller
  python main.py --mode vision         # smart controller + camera-vision bridge
  python main.py --mode rl             # Q-learning inference (loads data/qtable.pkl)
  python main.py --mode rl-train       # Q-learning training (saves data/qtable.pkl)
  python main.py --mode smart --gui    # open sumo-gui
  python main.py --mode fixed --cfg simulation/simulation.sumocfg
  python main.py --mode rl-train --episodes 100
"""

import argparse
import csv
import logging
import os
import random
import sys
import time
from contextlib import nullcontext
from pathlib import Path

os.environ["PYTHONIOENCODING"] = "utf-8"

# ---------------------------------------------------------------------------
# Project root on sys.path so `core.*` imports work when run from any cwd
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core.traffic_env import TrafficEnv, IntersectionState
from core.fixed_controller import FixedController
from core.smart_controller import SmartController
from core.rl_controller import (
    RLController,
    HYBRID_CONFIDENCE_THRESHOLD,
    MIN_GREEN,
    PRETRAIN_INIT,
    PRETRAIN_INCREMENT,
    PRETRAIN_CAP,
    _ACTION_PHASE,
    _TL_ORDER,
    _GREEN_PHASES,
    PHASE_NS_YELLOW,
    PHASE_EW_YELLOW,
)
from core.vision_bridge import VisionBridgeController

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CSV schema
# ---------------------------------------------------------------------------
CSV_FIELDS = [
    "sim_time",
    "tl_phase",
    "total_vehicles",
    "total_waiting_time",
    "avg_waiting_time",
    # int_B approaches (primary intersection)
    "north_count",   "north_wait",
    "south_count",   "south_wait",
    "east_count",    "east_wait",
    "west_count",    "west_wait",
    "queue_north",   "queue_south",
    "queue_east",    "queue_west",
    # per-intersection totals
    "intA_wait",     "intB_wait",     "intC_wait",
    "emergency_count",
    "controller_state",
    "controller_reason",
    # hybrid-mode columns (empty for non-hybrid modes)
    "rl_override",
    "max_q_value",
    "override_rate",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _queue_length(approach: dict) -> int:
    """Vehicles with speed < 0.1 m/s are considered queued."""
    count = 0
    for lane in approach["lanes"].values():
        if lane.mean_speed < 0.1:
            count += lane.vehicle_count
    return count


def _emergency_count(state) -> int:
    """Count approach lane groups that contain an emergency vehicle (all 3 nodes)."""
    total = 0
    for idata in state.intersections.values():
        for ap in idata.approaches.values():
            if ap["has_emergency"]:
                total += 1
    return total


def _intersection_waiting(idata) -> float:
    return sum(ap["waiting_time"] for ap in idata.approaches.values())


def _build_row(state, action: dict) -> dict:
    # int_B approaches used for the per-direction columns (primary intersection)
    n = state.north_in
    s = state.south_in
    e = state.east_in
    w = state.west_in

    # Aggregate vehicles and waiting time across ALL 3 intersections
    total_vehicles = sum(
        ap["vehicle_count"]
        for idata in state.intersections.values()
        for ap in idata.approaches.values()
    )
    intA_wait = _intersection_waiting(state.intersections["int_A"])
    intB_wait = _intersection_waiting(state.intersections["int_B"])
    intC_wait = _intersection_waiting(state.intersections["int_C"])
    total_waiting = intA_wait + intB_wait + intC_wait
    avg_waiting   = total_waiting / max(total_vehicles, 1)

    return {
        "sim_time":           state.sim_time,
        "tl_phase":           state.phase_index,
        "total_vehicles":     total_vehicles,
        "total_waiting_time": round(total_waiting, 2),
        "avg_waiting_time":   round(avg_waiting, 3),
        "north_count":        n["vehicle_count"],
        "north_wait":         round(n["waiting_time"], 2),
        "south_count":        s["vehicle_count"],
        "south_wait":         round(s["waiting_time"], 2),
        "east_count":         e["vehicle_count"],
        "east_wait":          round(e["waiting_time"], 2),
        "west_count":         w["vehicle_count"],
        "west_wait":          round(w["waiting_time"], 2),
        "queue_north":        _queue_length(n),
        "queue_south":        _queue_length(s),
        "queue_east":         _queue_length(e),
        "queue_west":         _queue_length(w),
        "intA_wait":          round(intA_wait, 2),
        "intB_wait":          round(intB_wait, 2),
        "intC_wait":          round(intC_wait, 2),
        "emergency_count":    _emergency_count(state),
        "controller_state":   action.get("state", ""),
        "controller_reason":  action.get("reason", ""),
    }


# ---------------------------------------------------------------------------
# Hybrid controller: Smart runs normally, RL overrides when confident
# ---------------------------------------------------------------------------

class HybridController:
    """
    Smart controller runs its full FSM every step and applies phases to SUMO.
    After each Smart update, RL checks whether it would make a different choice.

    Override conditions (ALL must hold):
      1. RL max Q-value > CONFIDENCE_THRESHOLD  (RL is sure it knows better)
      2. RL disagrees with Smart on >= 1 green-phase intersection
      3. That intersection has been in its current green >= HOLD_TIME seconds
         (anti-oscillation guard)

    Metrics logged per step:
      rl_override   — True if RL overrode Smart this step
      max_q_value   — RL's confidence for the current state
      override_rate — cumulative fraction of steps where RL overrode
    """

    CONFIDENCE_THRESHOLD = HYBRID_CONFIDENCE_THRESHOLD
    HOLD_TIME            = MIN_GREEN              # 8 s anti-oscillation

    def __init__(self, env: TrafficEnv, qtable_path) -> None:
        self._env   = env
        self._smart = SmartController(env)
        self._rl    = RLController(env, qtable_path=qtable_path, training=False)

        self._total_steps     = 0
        self._total_overrides = 0
        # Elapsed time on current green per node (for anti-oscillation)
        self._hold_elapsed: dict[str, float] = {}

    def reset(self) -> None:
        self._smart.reset()
        self._rl.reset()
        self._total_steps     = 0
        self._total_overrides = 0
        self._hold_elapsed    = {tl_id: self.HOLD_TIME for tl_id in _TL_ORDER}

    def update(self, state) -> dict:
        dt = self._env.step_length
        self._total_steps += 1

        # Smart runs its full FSM and applies phases to SUMO
        smart_action = self._smart.update(state)

        # Tick hold-elapsed counters for all nodes
        for tl_id in _TL_ORDER:
            self._hold_elapsed[tl_id] = self._hold_elapsed.get(tl_id, 0.0) + dt

        # RL compares its desired action against Smart's FSM state
        comparison  = self._rl.compare_decision(state, self._smart)
        max_q       = comparison["max_q_value"]
        rl_overrode = False
        override_nodes: list[str] = []

        if max_q > self.CONFIDENCE_THRESHOLD and comparison["would_override"]:
            for i, tl_id in enumerate(_TL_ORDER):
                if comparison["agreement"][tl_id]:
                    continue  # agree — nothing to override

                # Anti-oscillation: must have held current phase >= HOLD_TIME
                if self._hold_elapsed.get(tl_id, 0.0) < self.HOLD_TIME:
                    continue

                # Only override green phases — never interrupt a yellow transition
                current_phase = state.intersections[tl_id].phase_index
                if current_phase not in _GREEN_PHASES:
                    continue

                desired_phase = comparison["rl_phases"][tl_id]
                if desired_phase == current_phase:
                    continue

                yellow = (
                    PHASE_NS_YELLOW if current_phase == 0  # PHASE_NS_GREEN
                    else PHASE_EW_YELLOW
                )
                try:
                    self._env.set_phase_at(tl_id, yellow)
                    override_nodes.append(tl_id)
                    self._hold_elapsed[tl_id] = 0.0
                    rl_overrode = True
                except Exception as exc:
                    logger.debug("HybridController set_phase_at(%s) failed: %s",
                                 tl_id, exc)

        if rl_overrode:
            self._total_overrides += 1
            logger.info(
                "RL overrides Smart at %s  (max_q=%.2f > threshold=%.1f)",
                override_nodes, max_q, self.CONFIDENCE_THRESHOLD,
            )

        action = dict(smart_action)
        action["rl_override"]   = rl_overrode
        action["max_q_value"]   = round(max_q, 3)
        action["override_rate"] = round(
            self._total_overrides / self._total_steps, 3
        )
        action["reason"] = (
            "rl_override" if rl_overrode else smart_action.get("reason", "smart")
        )
        return action

    def summary(self) -> dict:
        s    = self._smart.summary()
        rl_s = self._rl.summary()
        s["rl_overrides"]            = self._total_overrides
        s["override_rate"]           = round(
            self._total_overrides / max(self._total_steps, 1), 3
        )
        s["rl_confidence_threshold"] = self.CONFIDENCE_THRESHOLD
        s["rl_qtable_entries"]       = rl_s.get("qtable_entries", 0)
        return s


# ---------------------------------------------------------------------------
# Training entry point (rl-train mode)
# ---------------------------------------------------------------------------

def run_rl_pretrain(pretrain_episodes: int, train_episodes: int,
                    cfg: str, qtable: str | None = None,
                    seed: int = 42) -> None:
    """
    Phase 1 — Imitation pretraining: run SmartController for
    ``pretrain_episodes`` episodes to seed the Q-table from Smart's policy.
    Phase 2 — Q-learning training: continue normal training for
    ``train_episodes`` episodes from the warm-started Q-table.
    """
    random.seed(seed)

    data_dir    = ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    qtable_path = Path(qtable) if qtable else data_dir / "qtable.pkl"

    env        = TrafficEnv(sumo_cfg=cfg, gui=False, port=8813, seed=seed)
    controller = RLController(env, qtable_path=qtable_path, training=True)

    separator = "-" * 60

    # ── Phase 1: imitation pretraining ──────────────────────────────
    print(f"\n{separator}")
    print(f"  AI-Traffic-Brain  |  RL-PRETRAIN  Phase 1/2: Imitation")
    print(f"  SmartController expert · {pretrain_episodes} episodes")
    print(separator)

    controller.pretrain_from_smart(episodes=pretrain_episodes, cfg=cfg)

    pretrain_entries = len(controller._qtable)
    print(f"  Q-table after pretraining : {pretrain_entries:,} entries")
    print(f"  (Smart pairs: init=+{PRETRAIN_INIT:.1f}, increment=+{PRETRAIN_INCREMENT:.1f}, cap=+{PRETRAIN_CAP:.1f}  |  other actions: +{0.0:.1f})")
    print(separator)

    # ── Phase 2: Q-learning on top of the warm start ────────────────
    print(f"\n{separator}")
    print(f"  AI-Traffic-Brain  |  RL-PRETRAIN  Phase 2/2: Q-Learning")
    print(f"  Starting from pretrained baseline · {train_episodes} episodes")
    print(separator)

    controller.train(episodes=train_episodes, cfg=cfg)

    print(f"\n{separator}")
    print(f"  AI-Traffic-Brain  |  mode: RL-PRETRAIN  (complete)")
    print(separator)
    s = controller.summary()
    for key, val in s.items():
        print(f"  {key:<32}: {val}")
    print(f"  {'pretrain_seeded_entries':<32}: {pretrain_entries:,}")
    print(separator)


def run_rl_train(episodes: int, cfg: str, qtable: str | None = None,
                 seed: int = 42) -> None:
    """Run Q-learning training for `episodes` episodes and save the Q-table."""
    random.seed(seed)

    data_dir    = ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    qtable_path = Path(qtable) if qtable else data_dir / "qtable.pkl"

    env        = TrafficEnv(sumo_cfg=cfg, gui=False, port=8813, seed=seed)
    controller = RLController(env, qtable_path=qtable_path, training=True)

    logger.info("RL training: %d episodes  cfg=%s", episodes, cfg)
    controller.train(episodes=episodes, cfg=cfg)

    separator = "-" * 60
    print(f"\n{separator}")
    print(f"  AI-Traffic-Brain  |  mode: RL-TRAIN")
    print(separator)
    s = controller.summary()
    for key, val in s.items():
        print(f"  {key:<32}: {val}")
    print(separator)


# ---------------------------------------------------------------------------
# Run loop
# ---------------------------------------------------------------------------

def run(mode: str, gui: bool, cfg: str,
        qtable: str | None = None, no_csv: bool = False,
        episodes: int = 1, seed: int = 42) -> None:
    random.seed(seed)

    data_dir = ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    csv_path = data_dir / f"results_{mode}.csv"

    env = TrafficEnv(sumo_cfg=cfg, gui=gui, port=8813, seed=seed)

    if mode == "fixed":
        controller = FixedController(env)
    elif mode == "smart":
        controller = SmartController(env)
    elif mode == "vision":
        controller = VisionBridgeController(env)
    elif mode == "hybrid":
        qtable_path = Path(qtable) if qtable else data_dir / "qtable.pkl"
        controller  = HybridController(env, qtable_path=qtable_path)
    else:  # rl
        qtable_path = Path(qtable) if qtable else data_dir / "qtable.pkl"
        controller  = RLController(env, qtable_path=qtable_path, training=False)

    # ------------------------------------------------------------------
    # Accumulators for final summary
    # ------------------------------------------------------------------
    total_waiting_accum: float = 0.0
    departed_vehicles: int = 0
    arrived_vehicles: int = 0
    emergency_steps: int = 0      # steps where >= 1 emergency vehicle present
    peak_queue: int = 0
    step_count: int = 0
    wall_start = time.perf_counter()

    if no_csv:
        logger.info("Starting simulation  mode=%-6s  gui=%s  cfg=%s  episodes=%d  (CSV disabled)",
                    mode, gui, cfg, episodes)
    else:
        logger.info("Starting simulation  mode=%-6s  gui=%s  cfg=%s  episodes=%d",
                    mode, gui, cfg, episodes)
        logger.info("Output CSV -> %s", csv_path)

    _file_ctx = (
        open(csv_path, "w", newline="") if not no_csv else nullcontext()
    )
    with _file_ctx as fh:
        writer: csv.DictWriter | None = None
        if not no_csv:
            writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS, restval="")
            writer.writeheader()

        for episode in range(1, episodes + 1):
            if episodes > 1:
                logger.info("--- Episode %d / %d ---", episode, episodes)

            try:
                env.start()
                controller.reset()

                import traci  # available after env.start()

                # Give camera-aware controllers live TraCI access for per-vehicle queries
                if hasattr(controller, "connect_traci"):
                    controller.connect_traci(traci)

                while True:
                    # Advance one second
                    state = env.step()
                    action = controller.update(state)

                    # Build row (always needed for summary accumulators)
                    row = _build_row(state, action)
                    # Propagate hybrid-mode extra columns when present
                    for key in ("rl_override", "max_q_value", "override_rate"):
                        if key in action:
                            row[key] = action[key]
                    if writer is not None:
                        writer.writerow(row)

                    # Accumulate summary stats
                    total_waiting_accum += row["total_waiting_time"]
                    step_count += 1

                    emg = row["emergency_count"]
                    if emg > 0:
                        emergency_steps += 1

                    q_total = (
                        row["queue_north"] + row["queue_south"] +
                        row["queue_east"]  + row["queue_west"]
                    )
                    if q_total > peak_queue:
                        peak_queue = q_total

                    # TraCI counters
                    departed_vehicles += traci.simulation.getDepartedNumber()
                    arrived_vehicles  += traci.simulation.getArrivedNumber()

                    # Progress log every 300 steps
                    if step_count % 300 == 0:
                        logger.info(
                            "t=%6.0f s | vehicles=%4d | total_wait=%8.1f s | "
                            "wait A=%.1f B=%.1f C=%.1f | "
                            "queues N=%d S=%d E=%d W=%d",
                            state.sim_time,
                            row["total_vehicles"],
                            row["total_waiting_time"],
                            row["intA_wait"], row["intB_wait"], row["intC_wait"],
                            row["queue_north"], row["queue_south"],
                            row["queue_east"],  row["queue_west"],
                        )

                    # Stop when SUMO signals end-of-simulation
                    if traci.simulation.getMinExpectedNumber() == 0:
                        logger.info("All vehicles processed - episode %d complete.",
                                    episode)
                        break

            except Exception as exc:
                logger.exception("Episode %d aborted: %s", episode, exc)
                raise
            finally:
                env.close()

    wall_elapsed = time.perf_counter() - wall_start

    # ------------------------------------------------------------------
    # Final summary
    # ------------------------------------------------------------------
    avg_waiting = total_waiting_accum / max(step_count, 1)

    ctrl_summary = controller.summary()

    separator = "-" * 60
    print(f"\n{separator}")
    print(f"  AI-Traffic-Brain  |  mode: {mode.upper()}")
    print(separator)
    print(f"  Simulation steps      : {step_count:,}")
    print(f"  Wall-clock time       : {wall_elapsed:.1f} s")
    print()
    print(f"  Vehicles departed     : {departed_vehicles:,}")
    print(f"  Vehicles arrived      : {arrived_vehicles:,}")
    print(f"  Vehicles in transit   : {departed_vehicles - arrived_vehicles:,}")
    print()
    print(f"  Avg total waiting/step: {avg_waiting:.2f} s")
    print(f"  Peak simultaneous queue: {peak_queue} vehicles")
    print()
    print(f"  Steps w/ emergency veh: {emergency_steps:,}")
    print()
    print("  Controller summary:")
    for key, val in ctrl_summary.items():
        if isinstance(val, dict):
            print(f"    {key}:")
            for subkey, subval in val.items():
                print(f"      {subkey:<30}: {subval}")
        else:
            print(f"    {key:<32}: {val}")
    print(separator)
    print(f"  Full results saved to : {csv_path}")
    print(separator)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI-Traffic-Brain simulation runner",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        choices=["fixed", "smart", "vision", "rl", "rl-train", "rl-pretrain", "hybrid"],
        required=True,
        help=(
            "Controller: 'fixed' (30s/5s cycle), 'smart' (demand-adaptive), "
            "'vision' (smart + camera bridge), "
            "'rl' (Q-learning inference), 'rl-train' (Q-learning training), "
            "'rl-pretrain' (imitation warm-start then Q-learning training), "
            "'hybrid' (Smart runs normally; RL overrides when confident)."
        ),
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        default=False,
        help="Open sumo-gui instead of running headless (ignored for rl-train).",
    )
    parser.add_argument(
        "--cfg",
        default=str(ROOT / "simulation" / "simulation.sumocfg"),
        metavar="PATH",
        help="Path to the SUMO .sumocfg file.",
    )
    parser.add_argument(
        "--episodes",
        type=int,
        default=100,
        metavar="N",
        help="Number of episodes. For rl-train: training episodes (default 100). "
             "For hybrid: test episodes to run (default 100; use 3 for a quick test).",
    )
    parser.add_argument(
        "--qtable",
        default=None,
        metavar="PATH",
        help="Path to Q-table pickle file for rl/rl-train modes (default: data/qtable.pkl).",
    )
    parser.add_argument(
        "--no-csv",
        action="store_true",
        default=False,
        help="Disable CSV output (speeds up rl mode; rl-train never writes CSV).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        metavar="N",
        help="Random seed for SUMO and Python RNG (default 42).",
    )
    parser.add_argument(
        "--pretrain-episodes",
        type=int,
        default=5,
        metavar="N",
        dest="pretrain_episodes",
        help="Episodes of SmartController imitation for rl-pretrain mode (default 5).",
    )
    parser.add_argument(
        "--train-episodes-after-pretrain",
        type=int,
        default=5,
        metavar="N",
        dest="train_episodes_after_pretrain",
        help="Q-learning episodes to run after imitation pretraining (default 5).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.mode == "rl-train":
        run_rl_train(episodes=args.episodes, cfg=args.cfg,
                     qtable=args.qtable, seed=args.seed)
    elif args.mode == "rl-pretrain":
        run_rl_pretrain(
            pretrain_episodes=args.pretrain_episodes,
            train_episodes=args.train_episodes_after_pretrain,
            cfg=args.cfg,
            qtable=args.qtable,
            seed=args.seed,
        )
    else:
        ep = args.episodes if args.mode == "hybrid" else 1
        run(mode=args.mode, gui=args.gui, cfg=args.cfg,
            qtable=args.qtable, no_csv=args.no_csv, episodes=ep,
            seed=args.seed)
