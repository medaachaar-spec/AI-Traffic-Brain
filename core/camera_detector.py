"""
CameraDetector - simulates a per-intersection YOLO-based traffic camera.

Since no real camera feed exists, the detector pulls live vehicle data from
TraCI (vehicle IDs, types, positions) and re-packages it as if a YOLOv8 model
had just run inference on a camera frame.

Output format mirrors a real detection pipeline:
  - List of DetectedVehicle objects (type, confidence, bbox, lane position)
  - CameraReport summarising detections and recommending a controller action

OpenCV is used to render an optional synthetic top-down frame (a 640x480 numpy
array with coloured boxes).  If opencv-python is not installed the frame
rendering path is skipped gracefully; all detection logic still works.

Emergency vehicle identification
---------------------------------
A vehicle is flagged as emergency only when BOTH conditions hold:
  - Its SUMO vehicle ID starts with 'ems' (matches routes.rou.xml naming), AND
  - Its SUMO type ID is exactly 'emergency'
Both conditions must be true simultaneously to avoid false positives.
Confidence is raised to 0.97-0.99 for confirmed emergency detections.

Night / low-traffic mode
--------------------------
If the mean vehicle density across all monitored lanes drops below
NIGHT_DENSITY_THRESHOLD (0.1 vehicles/lane), night_mode is set True and the
report recommends NIGHT_MODE.

Recommended action priority
----------------------------
  EMERGENCY_OVERRIDE  > CONGESTION_RELIEF > NIGHT_MODE > NORMAL
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from core.traffic_env import IntersectionData

logger = logging.getLogger(__name__)

# Optional OpenCV import — detection works without it; only frame rendering needs it
try:
    import cv2
    import numpy as np
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False
    logger.debug("opencv-python not installed; frame rendering disabled.")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NIGHT_DENSITY_THRESHOLD  = 0.1   # vehicles per lane below which night_mode activates
CONGESTION_WAIT_THRESHOLD = 500.0 # s  total node waiting_time for CONGESTION_RELIEF

# Virtual camera frame dimensions (pixels)
FRAME_W = 640
FRAME_H = 480

# Confidence ranges per vehicle type (min, max)
_CONF_RANGES: dict[str, tuple[float, float]] = {
    "car":              (0.88, 0.99),
    "motorcycle":       (0.85, 0.96),
    "truck":            (0.90, 0.99),
    "bus":              (0.91, 0.99),
    "emergency":        (0.97, 0.99),
    "pedestrian_proxy": (0.85, 0.94),
    "obstacle":         (0.86, 0.95),
    "unknown":          (0.85, 0.92),
}

# Approximate bbox dimensions per type in the virtual frame (w, h) pixels
_BBOX_SIZE: dict[str, tuple[int, int]] = {
    "car":              (36, 20),
    "motorcycle":       (18, 14),
    "truck":            (60, 28),
    "bus":              (70, 30),
    "emergency":        (42, 22),
    "pedestrian_proxy": (12, 26),
    "obstacle":         (55, 24),
    "unknown":          (36, 20),
}

# BGR colours for frame rendering per type
_BGR: dict[str, tuple[int, int, int]] = {
    "car":              (200, 200, 200),
    "motorcycle":       (255, 200, 100),
    "truck":            ( 80, 140, 220),
    "bus":              ( 60, 200,  60),
    "emergency":        (  0,   0, 255),
    "pedestrian_proxy": (255, 100, 100),
    "obstacle":         ( 20, 100, 255),
    "unknown":          (180, 180, 180),
}


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class DetectedVehicle:
    """One vehicle detection result, mimicking YOLO output."""
    vehicle_id:    str
    vehicle_type:  str          # car / truck / bus / motorcycle / emergency / …
    confidence:    float        # 0.85 – 0.99
    bbox:          tuple        # (x1, y1, x2, y2) in virtual frame pixels
    lane_id:       str
    lane_position: float        # normalised 0–1 along the lane (0=start, 1=end)
    is_emergency:  bool
    speed_ms:      float        # mean lane speed used as proxy for this vehicle


@dataclass
class CameraReport:
    """Aggregated camera analysis for one intersection."""
    tl_id:                str
    sim_time:             float
    total_detected:       int
    type_breakdown:       dict           # vehicle_type -> count
    emergency_detected:   bool
    emergency_confidence: float          # 0.0 when no emergency
    night_mode:           bool
    low_traffic:          bool
    avg_density:          float          # vehicles per lane
    total_waiting:        float          # seconds across all approaches
    recommended_action:   str            # NORMAL / EMERGENCY_OVERRIDE / CONGESTION_RELIEF / NIGHT_MODE
    detections:           list           # list[DetectedVehicle]

    def __str__(self) -> str:
        return (
            f"CameraReport[{self.tl_id}] t={self.sim_time:.0f}s "
            f"detected={self.total_detected} action={self.recommended_action} "
            f"emg={self.emergency_detected}"
        )


# ---------------------------------------------------------------------------
# Lane-to-frame geometry helpers
# ---------------------------------------------------------------------------

def _lane_column_range(lane_id: str, total_lanes: int, lane_index: int) -> tuple[int, int]:
    """
    Map a lane index to a horizontal pixel range in the virtual frame.
    Lanes divide the frame width evenly with a small gutter.
    """
    gutter   = 10
    usable_w = FRAME_W - gutter * (total_lanes + 1)
    lane_w   = max(usable_w // total_lanes, 40)
    x_start  = gutter + lane_index * (lane_w + gutter)
    x_end    = x_start + lane_w
    return x_start, x_end


def _simulate_bbox(
    lane_id: str,
    lane_index: int,
    total_lanes: int,
    vehicle_index: int,
    total_in_lane: int,
    vtype: str,
) -> tuple[int, int, int, int]:
    """
    Generate a plausible bounding box for a vehicle in a lane.
    Vehicles are spread evenly along the lane's vertical extent.
    """
    x_start, x_end = _lane_column_range(lane_id, total_lanes, lane_index)
    bw, bh = _BBOX_SIZE.get(vtype, (36, 20))

    # Horizontal centre within the lane column, with small jitter
    cx = (x_start + x_end) // 2 + random.randint(-6, 6)
    cx = max(x_start + bw // 2, min(x_end - bw // 2, cx))

    # Vertical position: divide frame height by slot for each vehicle
    slot_h   = max(FRAME_H // max(total_in_lane, 1), bh + 8)
    cy       = slot_h * vehicle_index + slot_h // 2 + random.randint(-4, 4)
    cy       = max(bh // 2 + 4, min(FRAME_H - bh // 2 - 4, cy))

    x1, y1 = cx - bw // 2, cy - bh // 2
    x2, y2 = cx + bw // 2, cy + bh // 2
    return (x1, y1, x2, y2)


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------

class CameraDetector:
    """
    Simulates a fixed overhead traffic camera with a YOLO detection backend.

    The detector does not hold a TraCI reference itself; caller passes the live
    IntersectionData snapshot (and optionally a traci module reference for
    per-vehicle ID/type queries).

    Usage
    -----
    detector = CameraDetector()
    # inside simulation loop:
    import traci
    detector.set_traci(traci)
    report = detector.get_camera_report(tl_id, idata, sim_time=state.sim_time)
    """

    def __init__(self) -> None:
        self._traci = None        # set via set_traci() once env.start() is called
        self._frame_cache: dict[str, object] = {}   # tl_id -> last rendered frame
        self._report_history: list[CameraReport] = []

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_traci(self, traci_module) -> None:
        """Inject live TraCI module so the detector can query vehicle IDs/types."""
        self._traci = traci_module

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def analyze_frame(
        self,
        tl_id: str,
        idata: "IntersectionData",
        sim_time: float = 0.0,
    ) -> list[DetectedVehicle]:
        """
        Produce a list of DetectedVehicle objects for one intersection.

        If a live TraCI module has been set, per-vehicle IDs and types are
        queried directly.  Otherwise, types are estimated from the flow mix
        defined in routes.rou.xml (70 % car, 10 % motorcycle, 10 % truck,
        5 % bus, 5 % obstacle/unknown).
        """
        detections: list[DetectedVehicle] = []

        for ap_name, ap in idata.approaches.items():
            lanes      = ap["lanes"]          # lane_id -> LaneData
            lane_list  = list(lanes.keys())
            total_lanes = len(lane_list)

            for lane_idx, (lane_id, lane_data) in enumerate(lanes.items()):
                count = lane_data.vehicle_count
                if count == 0:
                    continue

                # --- Obtain per-vehicle IDs and types ---
                veh_type_map = self._fetch_vehicle_types(lane_id, count, lane_data.has_emergency)

                for v_idx, (vid, vtype) in enumerate(veh_type_map.items()):
                    is_emg = self._is_emergency(vid, vtype)

                    conf_lo, conf_hi = _CONF_RANGES.get(vtype, (0.85, 0.95))
                    if is_emg:
                        conf_lo, conf_hi = 0.97, 0.99
                    confidence = round(random.uniform(conf_lo, conf_hi), 3)

                    bbox = _simulate_bbox(
                        lane_id, lane_idx, total_lanes,
                        v_idx, count, vtype,
                    )

                    # Normalised lane position based on vehicle index
                    lane_pos = round((v_idx + 0.5) / max(count, 1), 3)

                    detections.append(DetectedVehicle(
                        vehicle_id    = vid,
                        vehicle_type  = vtype,
                        confidence    = confidence,
                        bbox          = bbox,
                        lane_id       = lane_id,
                        lane_position = lane_pos,
                        is_emergency  = is_emg,
                        speed_ms      = round(lane_data.mean_speed, 2),
                    ))

        return detections

    def get_camera_report(
        self,
        tl_id: str,
        idata: "IntersectionData",
        sim_time: float = 0.0,
    ) -> CameraReport:
        """
        Full pipeline: analyze frame -> aggregate -> recommend action.
        """
        detections = self.analyze_frame(tl_id, idata, sim_time)

        # --- Aggregate type breakdown ---
        type_breakdown: dict[str, int] = {}
        for det in detections:
            type_breakdown[det.vehicle_type] = type_breakdown.get(det.vehicle_type, 0) + 1

        # --- Emergency ---
        emg_dets     = [d for d in detections if d.is_emergency]
        emg_detected = len(emg_dets) > 0
        emg_conf     = max((d.confidence for d in emg_dets), default=0.0)

        # --- Density / night mode ---
        total_lanes  = sum(len(ap["lanes"]) for ap in idata.approaches.values())
        total_count  = sum(d.vehicle_id != "" for d in detections)   # same as len(detections)
        avg_density  = total_count / max(total_lanes, 1)
        night_mode   = avg_density < NIGHT_DENSITY_THRESHOLD
        low_traffic  = night_mode

        # --- Waiting time ---
        total_waiting = sum(ap["waiting_time"] for ap in idata.approaches.values())

        # --- Recommended action (priority order) ---
        if emg_detected:
            action = "EMERGENCY_OVERRIDE"
        elif total_waiting > CONGESTION_WAIT_THRESHOLD:
            action = "CONGESTION_RELIEF"
        elif low_traffic:
            action = "NIGHT_MODE"
        else:
            action = "NORMAL"

        report = CameraReport(
            tl_id                = tl_id,
            sim_time             = sim_time,
            total_detected       = len(detections),
            type_breakdown       = type_breakdown,
            emergency_detected   = emg_detected,
            emergency_confidence = round(emg_conf, 3),
            night_mode           = night_mode,
            low_traffic          = low_traffic,
            avg_density          = round(avg_density, 3),
            total_waiting        = round(total_waiting, 2),
            recommended_action   = action,
            detections           = detections,
        )
        self._report_history.append(report)
        return report

    def render_frame(
        self,
        tl_id: str,
        idata: "IntersectionData",
        sim_time: float = 0.0,
    ) -> Optional[object]:
        """
        Render a synthetic top-down camera frame as a BGR numpy array (640x480).
        Returns None if opencv-python is not installed.

        The frame shows:
          - Dark grey road background
          - Lane dividers as white dashed lines
          - Coloured filled rectangles for each detected vehicle
          - Red rectangle + 'EMG' label for emergency vehicles
          - Confidence score overlaid on each bbox
        """
        if not _CV2_AVAILABLE:
            return None

        frame = np.zeros((FRAME_H, FRAME_W, 3), dtype=np.uint8)
        frame[:] = (40, 40, 40)   # dark road background

        # Compute total lanes for geometry
        lanes_per_approach = {
            ap_name: list(ap["lanes"].keys())
            for ap_name, ap in idata.approaches.items()
        }
        all_lane_ids = [lid for lids in lanes_per_approach.values() for lid in lids]
        total_lanes  = len(all_lane_ids)

        # Draw lane dividers
        for i in range(1, total_lanes):
            x_start, _ = _lane_column_range("", total_lanes, i - 1)
            _, x_end   = _lane_column_range("", total_lanes, i - 1)
            x_div = x_end + 5
            for y in range(0, FRAME_H, 20):
                cv2.line(frame, (x_div, y), (x_div, min(y + 12, FRAME_H - 1)),
                         (120, 120, 120), 1)

        # Draw vehicles
        detections = self.analyze_frame(tl_id, idata, sim_time)
        for det in detections:
            colour = _BGR.get(det.vehicle_type, (180, 180, 180))
            x1, y1, x2, y2 = det.bbox
            cv2.rectangle(frame, (x1, y1), (x2, y2), colour, -1)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 1)

            if det.is_emergency:
                cv2.rectangle(frame, (x1 - 2, y1 - 2), (x2 + 2, y2 + 2), (0, 0, 255), 2)
                cv2.putText(frame, "EMG", (x1, y1 - 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
            else:
                label = f"{det.confidence:.2f}"
                cv2.putText(frame, label, (x1, y1 - 2),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.28, (220, 220, 220), 1)

        # HUD overlay
        hud = f"t={sim_time:.0f}s  {tl_id}  n={len(detections)}"
        cv2.putText(frame, hud, (6, 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 220, 255), 1)

        self._frame_cache[tl_id] = frame
        return frame

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def last_report(self, tl_id: str) -> Optional[CameraReport]:
        """Return the most recent report for a given intersection, or None."""
        for rpt in reversed(self._report_history):
            if rpt.tl_id == tl_id:
                return rpt
        return None

    def session_stats(self) -> dict:
        """Summary stats across all reports seen this session."""
        if not self._report_history:
            return {"reports": 0}
        total_emg   = sum(1 for r in self._report_history if r.emergency_detected)
        total_night = sum(1 for r in self._report_history if r.night_mode)
        actions: dict[str, int] = {}
        for r in self._report_history:
            actions[r.recommended_action] = actions.get(r.recommended_action, 0) + 1
        return {
            "reports":           len(self._report_history),
            "emergency_steps":   total_emg,
            "night_mode_steps":  total_night,
            "action_counts":     actions,
            "cv2_available":     _CV2_AVAILABLE,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_vehicle_types(
        self,
        lane_id: str,
        count: int,
        has_emergency: bool,
    ) -> dict[str, str]:
        """
        Returns {vehicle_id: vehicle_type} for all vehicles in a lane.

        Strategy:
          1. If TraCI is live, query exact IDs and types.
          2. Otherwise, simulate IDs and estimate types from the known flow mix.
        """
        if self._traci is not None:
            try:
                veh_ids = self._traci.lane.getLastStepVehicleIDs(lane_id)
                return {
                    vid: self._traci.vehicle.getTypeID(vid)
                    for vid in veh_ids
                }
            except Exception as exc:
                logger.debug("TraCI vehicle query failed for %s: %s", lane_id, exc)
                # Fall through to estimation

        # --- Estimation fallback ---
        # Flow mix from routes.rou.xml:
        #   ~70% car, ~10% motorcycle, ~10% truck, ~5% bus, remainder obstacle/unknown
        # If the lane has an emergency flag, reserve one slot for emergency.
        # ID is prefixed with 'ems_' so it passes the strict _is_emergency() check.
        result: dict[str, str] = {}
        emg_slot = 1 if has_emergency else 0
        regular  = count - emg_slot

        if emg_slot:
            # Prefix must NOT start with "ems" so this synthetic ID cannot pass
            # _is_emergency() and trigger false overrides.  Emergency presence is
            # already captured by has_emergency on the parent lane_data.
            result[f"fallback_emg_{lane_id}"] = "car"

        type_weights = [
            ("car",        0.70),
            ("motorcycle", 0.10),
            ("truck",      0.10),
            ("bus",        0.05),
            ("obstacle",   0.05),
        ]
        for i in range(regular):
            r     = random.random()
            cumul = 0.0
            vtype = "unknown"
            for tname, w in type_weights:
                cumul += w
                if r < cumul:
                    vtype = tname
                    break
            result[f"{lane_id}_v{i}"] = vtype

        return result

    @staticmethod
    def _is_emergency(vehicle_id: str, vehicle_type: str) -> bool:
        """
        True only when BOTH conditions are satisfied:
          - vehicle_id starts with 'ems'  (routes.rou.xml convention: ems_01 … ems_15,
            and the fallback simulator uses ems_sim_<lane_id>)
          - vehicle_type is exactly 'emergency'
        Requiring both prevents false positives from:
          - vehicles whose IDs accidentally contain 'ems' (e.g. schemes_van)
          - vehicles of type 'emergency' that arrive from external flows with
            non-standard IDs
        """
        return vehicle_id.startswith("ems") and vehicle_type == "emergency"
