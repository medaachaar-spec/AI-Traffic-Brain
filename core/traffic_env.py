"""
TrafficEnv - SUMO/TraCI environment wrapper for the 3-intersection network.

Network layout:
    north_A        north_B        north_C
       |               |               |
    [int_A] --AB-- [int_B] --BC-- [int_C]
       |               |               |
    south_A        south_B        south_C

Traffic light nodes: int_A (west), int_B (centre), int_C (east)
Primary controller node: int_B (the busiest 4-way crossroads)
int_A and int_C run their SUMO-generated TL programs unless overridden.
"""

import os
import subprocess
import time
from dataclasses import dataclass, field
from typing import Optional

import traci


# ---------------------------------------------------------------------------
# Traffic light node IDs
# ---------------------------------------------------------------------------
TL_IDS    = ["int_A", "int_B", "int_C"]
PRIMARY_TL = "int_B"   # used by single-TL controllers for backward compat

# ---------------------------------------------------------------------------
# Per-intersection approach lane definitions
# Lane IDs follow SUMO convention: <edge_id>_<lane_index>
# ---------------------------------------------------------------------------
NETWORK_APPROACHES: dict[str, dict[str, list[str]]] = {
    "int_A": {
        "west_in":  ["AB_west_0", "AB_west_1", "AB_west_2"],
        "north_in": ["nA_in_0",   "nA_in_1"],
        "south_in": ["sA_in_0",   "sA_in_1"],
    },
    "int_B": {
        "east_in":  ["AB_east_0", "AB_east_1", "AB_east_2"],
        "west_in":  ["BC_west_0", "BC_west_1", "BC_west_2"],
        "north_in": ["nB_in_0",   "nB_in_1"],
        "south_in": ["sB_in_0",   "sB_in_1"],
    },
    "int_C": {
        "east_in":  ["BC_east_0", "BC_east_1", "BC_east_2"],
        "north_in": ["nC_in_0",   "nC_in_1"],
        "south_in": ["sC_in_0",   "sC_in_1"],
    },
}

ALL_LANES: list[str] = [
    lane
    for approaches in NETWORK_APPROACHES.values()
    for lanes in approaches.values()
    for lane in lanes
]

TRACI_PORT     = 8813
EMERGENCY_TYPE = "emergency"


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class LaneData:
    lane_id: str
    vehicle_count: int
    waiting_time: float    # accumulated waiting time of all vehicles (s)
    mean_speed: float      # m/s
    halting_count: int     # vehicles with speed < 0.1 m/s
    has_emergency: bool


@dataclass
class IntersectionData:
    """Snapshot for one traffic-light node."""
    tl_id: str
    phase_index: int
    phase_duration: float
    approaches: dict       # approach_name -> approach summary dict
    lanes: dict            # lane_id -> LaneData


@dataclass
class NetworkState:
    """Full-network snapshot returned by get_lane_data() each step."""
    sim_time: float
    intersections: dict    # tl_id -> IntersectionData

    # ------------------------------------------------------------------
    # Backward-compatibility shims for controllers that only inspect int_B
    # ------------------------------------------------------------------
    @property
    def north_in(self) -> dict:
        return self.intersections["int_B"].approaches["north_in"]

    @property
    def south_in(self) -> dict:
        return self.intersections["int_B"].approaches["south_in"]

    @property
    def east_in(self) -> dict:
        return self.intersections["int_B"].approaches["east_in"]

    @property
    def west_in(self) -> dict:
        return self.intersections["int_B"].approaches["west_in"]

    @property
    def phase_index(self) -> int:
        return self.intersections["int_B"].phase_index

    @property
    def phase_duration(self) -> float:
        return self.intersections["int_B"].phase_duration

    # Alias kept for any code that imported IntersectionState by name
    @property
    def lanes(self) -> dict:
        merged = {}
        for idata in self.intersections.values():
            merged.update(idata.lanes)
        return merged


# Keep the old name importable
IntersectionState = NetworkState


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

class TrafficEnv:
    """
    Wraps a SUMO simulation via TraCI for a 3-intersection network.

    Usage
    -----
    env = TrafficEnv(sumo_cfg="simulation/simulation.sumocfg", gui=False)
    env.start()
    while True:
        state = env.step()          # returns NetworkState
        # state.intersections["int_B"].approaches["north_in"]["waiting_time"]
        # state.north_in  <-- shortcut for int_B north approach
        if env.is_done:
            break
    env.close()
    """

    def __init__(
        self,
        sumo_cfg: str = "simulation/simulation.sumocfg",
        gui: bool = False,
        port: int = TRACI_PORT,
        step_length: float = 1.0,
        seed: int = 42,
    ):
        self.sumo_cfg    = os.path.abspath(sumo_cfg)
        self.gui         = gui
        self.port        = port
        self.step_length = step_length
        self.seed        = seed

        self._sumo_proc: Optional[subprocess.Popen] = None
        self._connected  = False
        self._step_count = 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Launch SUMO and open a TraCI connection on self.port."""
        binary = "sumo-gui" if self.gui else "sumo"
        cmd = [
            binary,
            "-c", self.sumo_cfg,
            "--remote-port",         str(self.port),
            "--step-length",         str(self.step_length),
            "--no-step-log",         "true",
            "--waiting-time-memory", "3600",
            "--collision.action",    "warn",
            "--seed",                str(self.seed),
        ]
        self._sumo_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(1.0)
        traci.init(port=self.port)
        self._connected  = True
        self._step_count = 0

    def step(self, n: int = 1) -> NetworkState:
        """Advance simulation by n steps and return the current network state."""
        self._assert_connected()
        for _ in range(n):
            traci.simulationStep()
            self._step_count += 1
        return self.get_lane_data()

    def close(self) -> None:
        """Close TraCI and terminate SUMO. Handles slow GUI shutdown gracefully."""
        if self._connected:
            traci.close()
            self._connected = False
        if self._sumo_proc is not None:
            timeout = 30 if self.gui else 10
            try:
                self._sumo_proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self._sumo_proc.kill()
                self._sumo_proc.wait()
            self._sumo_proc = None

    # ------------------------------------------------------------------
    # Observation
    # ------------------------------------------------------------------

    def get_lane_data(self) -> NetworkState:
        """
        Poll every monitored approach lane via direct traci getter calls
        and return a NetworkState covering all 3 intersections.
        """
        self._assert_connected()
        sim_time = traci.simulation.getTime()

        intersections: dict[str, IntersectionData] = {}

        for tl_id, approach_map in NETWORK_APPROACHES.items():
            phase_index    = traci.trafficlight.getPhase(tl_id)
            phase_duration = traci.trafficlight.getPhaseDuration(tl_id)

            lanes: dict[str, LaneData] = {}
            for lane_ids in approach_map.values():
                for lane_id in lane_ids:
                    veh_ids = traci.lane.getLastStepVehicleIDs(lane_id)
                    has_emergency = any(
                        traci.vehicle.getTypeID(v) == EMERGENCY_TYPE
                        for v in veh_ids
                    )
                    lanes[lane_id] = LaneData(
                        lane_id       = lane_id,
                        vehicle_count = traci.lane.getLastStepVehicleNumber(lane_id),
                        waiting_time  = traci.lane.getWaitingTime(lane_id),
                        mean_speed    = traci.lane.getLastStepMeanSpeed(lane_id),
                        halting_count = traci.lane.getLastStepHaltingNumber(lane_id),
                        has_emergency = has_emergency,
                    )

            approaches: dict[str, dict] = {}
            for approach_name, lane_ids in approach_map.items():
                approaches[approach_name] = _approach_summary(lane_ids, lanes)

            intersections[tl_id] = IntersectionData(
                tl_id          = tl_id,
                phase_index    = phase_index,
                phase_duration = phase_duration,
                approaches     = approaches,
                lanes          = lanes,
            )

        return NetworkState(sim_time=sim_time, intersections=intersections)

    # ------------------------------------------------------------------
    # Traffic light control
    # ------------------------------------------------------------------

    def set_phase(self, phase_index: int) -> None:
        """Apply phase_index to ALL three TL nodes simultaneously.
        Used by FixedController / SmartController for coordinated control."""
        self._assert_connected()
        for tl_id in TL_IDS:
            try:
                traci.trafficlight.setPhase(tl_id, phase_index)
            except traci.exceptions.TraCIException:
                # Phase index may not exist on terminal T-junctions; skip silently
                pass

    def set_phase_at(self, tl_id: str, phase_index: int) -> None:
        """Apply phase_index to a single named TL node."""
        self._assert_connected()
        traci.trafficlight.setPhase(tl_id, phase_index)

    def set_phase_duration(self, duration: float) -> None:
        """Override remaining phase duration on all TL nodes."""
        self._assert_connected()
        for tl_id in TL_IDS:
            try:
                traci.trafficlight.setPhaseDuration(tl_id, duration)
            except traci.exceptions.TraCIException:
                pass

    def get_phase(self, tl_id: str = PRIMARY_TL) -> int:
        self._assert_connected()
        return traci.trafficlight.getPhase(tl_id)

    def get_sim_time(self) -> float:
        self._assert_connected()
        return traci.simulation.getTime()

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    @property
    def is_done(self) -> bool:
        if not self._connected:
            return True
        return (
            traci.simulation.getMinExpectedNumber() == 0
            and traci.simulation.getDepartedNumber() > 0
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _assert_connected(self) -> None:
        if not self._connected:
            raise RuntimeError(
                "TrafficEnv is not connected. Call start() first."
            )

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_):
        self.close()


# ---------------------------------------------------------------------------
# Module-level helper
# ---------------------------------------------------------------------------

def _approach_summary(lane_ids: list[str], lanes: dict[str, LaneData]) -> dict:
    """Aggregate LaneData for a list of lanes into a single approach dict."""
    total_count   = sum(lanes[l].vehicle_count  for l in lane_ids)
    total_waiting = sum(lanes[l].waiting_time   for l in lane_ids)
    total_halting = sum(lanes[l].halting_count  for l in lane_ids)
    n             = len(lane_ids)
    mean_speed    = sum(lanes[l].mean_speed for l in lane_ids) / n
    has_emergency = any(lanes[l].has_emergency  for l in lane_ids)
    return {
        "vehicle_count":  total_count,
        "waiting_time":   total_waiting,
        "mean_speed":     mean_speed,
        "halting_count":  total_halting,
        "has_emergency":  has_emergency,
        "lanes":          {l: lanes[l] for l in lane_ids},
    }
