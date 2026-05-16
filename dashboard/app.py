"""
AI Traffic Brain - Streamlit results dashboard.

Run with:
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import csv
import html
import math
import pickle
import re
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import plotly.graph_objects as go
import streamlit as st


# ---------------------------------------------------------------------------
# Paths and controller configuration
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
QTABLE_PATH = DATA_DIR / "qtable.pkl"

CONTROLLERS = {
    "fixed": {
        "label": "Fixed",
        "file": "results_fixed.csv",
        "color": "#ff9f1c",
        "short": "Fixed cycle",
    },
    "smart": {
        "label": "Smart",
        "file": "results_smart.csv",
        "color": "#2f80ff",
        "short": "Adaptive rules",
    },
    "vision": {
        "label": "Vision",
        "file": "results_vision.csv",
        "color": "#9b5cff",
        "short": "Camera-aware",
    },
    "rl": {
        "label": "RL",
        "file": "results_rl.csv",
        "color": "#22f3b6",
        "short": "Q-learning",
    },
}

EXPECTED_FILES = [cfg["file"] for cfg in CONTROLLERS.values()]


# ---------------------------------------------------------------------------
# Column aliases
# ---------------------------------------------------------------------------

TIME_ALIASES = ("sim_time", "simulation_time", "time", "step", "timestep")
TOTAL_WAIT_ALIASES = (
    "total_waiting_time",
    "total_wait",
    "waiting_total",
    "waiting_time_total",
    "totalwaitingtime",
    "total_waiting",
)
AVG_WAIT_ALIASES = (
    "avg_waiting_time",
    "average_waiting_time",
    "avg_wait",
    "mean_waiting_time",
    "mean_wait",
)
TOTAL_QUEUE_ALIASES = ("total_queue", "queue_total", "current_queue")
PEAK_QUEUE_ALIASES = ("peak_queue", "max_queue", "queue_peak")
ARRIVED_ALIASES = ("vehicles_arrived", "arrived_vehicles", "arrived", "throughput")
DEPARTED_ALIASES = ("vehicles_departed", "departed_vehicles", "departed")
TOTAL_VEHICLE_ALIASES = ("total_vehicles", "vehicles", "vehicle_count")
REWARD_ALIASES = ("total_reward", "episode_reward", "reward")
EPSILON_ALIASES = ("epsilon", "eps")
PHASE_CHANGE_ALIASES = ("phase_changes", "phase_change_count")
PHASE_ALIASES = ("tl_phase", "phase", "controller_phase")
EMERGENCY_ALIASES = ("emergency_count", "emergency", "emergency_vehicles")
REASON_ALIASES = ("controller_reason", "reason", "control_reason")

QUEUE_APPROACH_COLS = (
    ("North", ("queue_north", "north_queue")),
    ("South", ("queue_south", "south_queue")),
    ("East", ("queue_east", "east_queue")),
    ("West", ("queue_west", "west_queue")),
)

APPROACH_WAIT_COLS = (
    ("North", ("north_wait", "north_waiting_time")),
    ("South", ("south_wait", "south_waiting_time")),
    ("East", ("east_wait", "east_waiting_time")),
    ("West", ("west_wait", "west_waiting_time")),
)

INTERSECTION_WAIT_COLS = (
    ("int_A", ("intA_wait", "int_a_wait", "intersection_a_wait")),
    ("int_B", ("intB_wait", "int_b_wait", "intersection_b_wait")),
    ("int_C", ("intC_wait", "int_c_wait", "intersection_c_wait")),
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ResultSet:
    key: str
    label: str
    short: str
    color: str
    path: Path
    found: bool
    rows: list[dict[str, object]]
    columns: dict[str, list[object]]
    original_columns: list[str]
    normalized_columns: dict[str, str]
    error: str = ""
    modified: str = ""

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def column_count(self) -> int:
        return len(self.original_columns)


# ---------------------------------------------------------------------------
# Page config and CSS
# ---------------------------------------------------------------------------

def set_page_config() -> None:
    st.set_page_config(
        page_title="AI Traffic Brain",
        page_icon="🚦",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def inject_global_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Mono:wght@400;700&display=swap');

        :root {
            --bg: #070b15;
            --panel: rgba(13, 19, 34, 0.78);
            --line: rgba(148, 163, 184, 0.16);
            --text: #e5edf8;
            --muted: #8fa0bd;
            --faint: #4f607f;
            --cyan: #00d4ff;
            --blue: #2f80ff;
            --purple: #9b5cff;
            --green: #22f3b6;
            --orange: #ff9f1c;
        }

        html, body, [data-testid="stAppViewContainer"] {
            background:
                linear-gradient(rgba(0, 212, 255, 0.026) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0, 212, 255, 0.026) 1px, transparent 1px),
                linear-gradient(135deg, #050812 0%, #0a1020 52%, #080c18 100%) !important;
            background-size: 44px 44px, 44px 44px, auto !important;
            color: var(--text);
            font-family: "Inter", sans-serif;
        }

        [data-testid="stHeader"] { background: transparent !important; }
        [data-testid="stMainBlockContainer"] {
            padding: 0.75rem clamp(1rem, 2vw, 2rem) 2rem;
            max-width: 1360px;
        }
        [data-testid="stVerticalBlock"] { gap: 0.62rem; }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #050812 0%, #081020 58%, #050812 100%) !important;
            border-right: 1px solid rgba(0, 212, 255, 0.12) !important;
            box-shadow: 8px 0 34px rgba(0, 0, 0, 0.38);
        }
        [data-testid="stSidebarContent"] { padding: 0.85rem 0.78rem 1rem; }
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
            margin-bottom: 10px;
            border: 1px solid rgba(0, 212, 255, 0.15) !important;
            border-radius: 8px !important;
            background:
                linear-gradient(145deg, rgba(0, 212, 255, 0.055), rgba(155, 92, 255, 0.035)),
                rgba(9, 14, 27, 0.70) !important;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.045), 0 12px 34px rgba(0,0,0,0.22);
        }
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] > div { padding: 10px 11px !important; }
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"] { gap: 0.55rem !important; }
        [data-testid="stSidebar"] .stSelectbox {
            margin: 0 0 0.62rem 0 !important;
        }
        [data-testid="stSidebar"] .stCheckbox {
            margin: 0.2rem 0 0.55rem 0 !important;
        }
        [data-testid="stSidebar"] .stButton {
            margin-top: 0.12rem !important;
        }

        @keyframes sidebarPulse {
            0%, 100% { filter: drop-shadow(0 0 8px rgba(0, 212, 255, 0.26)); transform: scale(1); }
            50% { filter: drop-shadow(0 0 14px rgba(34, 243, 182, 0.32)); transform: scale(1.04); }
        }
        @keyframes statusBlink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.38; }
        }
        .sb-card {
            position: relative;
            margin-bottom: 10px;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid rgba(0, 212, 255, 0.15);
            background:
                linear-gradient(145deg, rgba(0, 212, 255, 0.055), rgba(155, 92, 255, 0.035)),
                rgba(9, 14, 27, 0.70);
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.045), 0 12px 34px rgba(0,0,0,0.22);
            overflow: hidden;
        }
        .sb-card::before {
            content: "";
            position: absolute;
            left: 0;
            right: 0;
            top: 0;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(0, 212, 255, 0.42), transparent);
        }
        .sb-card.identity {
            border-color: rgba(0, 212, 255, 0.22);
            background:
                linear-gradient(135deg, rgba(0, 212, 255, 0.10), rgba(34, 243, 182, 0.045) 58%, rgba(155, 92, 255, 0.035)),
                rgba(8, 14, 27, 0.82);
        }
        .sb-identity {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 0 0 9px 0;
        }
        .sb-logo {
            display: grid;
            place-items: center;
            width: 34px;
            height: 34px;
            border-radius: 8px;
            border: 1px solid rgba(0, 212, 255, 0.26);
            background: rgba(0, 212, 255, 0.08);
            font-size: 1.42rem;
            line-height: 1;
            animation: sidebarPulse 4.5s ease-in-out infinite;
        }
        .sb-title {
            font-family: "Space Mono", monospace;
            font-size: 0.82rem;
            font-weight: 700;
            color: #f2f8ff;
            letter-spacing: 0.04em;
        }
        .sb-sub {
            margin-top: 3px;
            color: var(--faint);
            font-size: 0.7rem;
        }
        .sb-online {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            width: fit-content;
            padding: 5px 8px;
            border-radius: 999px;
            border: 1px solid rgba(34, 243, 182, 0.36);
            background: rgba(34, 243, 182, 0.075);
            color: var(--green);
            font-family: "Space Mono", monospace;
            font-size: 0.55rem;
            font-weight: 700;
            letter-spacing: 0.10em;
            text-transform: uppercase;
            box-shadow: 0 0 20px rgba(34, 243, 182, 0.10);
        }
        .sb-online-dot {
            width: 7px;
            height: 7px;
            border-radius: 999px;
            background: var(--green);
            box-shadow: 0 0 14px rgba(34, 243, 182, 0.5);
            animation: statusBlink 2.2s ease-in-out infinite;
        }
        .sb-card-title {
            margin-bottom: 8px;
            color: #dff7ff;
            font-family: "Space Mono", monospace;
            font-size: 0.62rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
        }
        .sb-label {
            font-family: "Space Mono", monospace;
            color: var(--faint);
            font-size: 0.58rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin-bottom: 6px;
        }
        .sb-value {
            color: var(--muted);
            font-size: 0.76rem;
            line-height: 1.38;
            margin-bottom: 4px;
        }
        .sb-value.strong {
            color: #dbe7f6;
            font-weight: 700;
        }
        .sb-accent {
            color: var(--cyan);
            font-family: "Space Mono", monospace;
            font-size: 0.66rem;
            font-weight: 700;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            margin-top: 4px;
        }
        .sb-footer {
            color: var(--faint);
            font-family: "Space Mono", monospace;
            font-size: 0.62rem;
            letter-spacing: 0.08em;
            text-align: center;
            text-transform: uppercase;
        }

        .hero {
            display: grid;
            grid-template-columns: minmax(0, 1fr) minmax(280px, 340px);
            gap: 16px;
            align-items: stretch;
            padding: 22px;
            border: 1px solid rgba(0, 212, 255, 0.18);
            border-radius: 8px;
            background:
                linear-gradient(120deg, rgba(0, 212, 255, 0.10), rgba(155, 92, 255, 0.07) 42%, rgba(34, 243, 182, 0.04)),
                rgba(9, 14, 27, 0.76);
            box-shadow: 0 24px 80px rgba(0, 0, 0, 0.42);
            overflow: visible;
        }
        .hero-title {
            margin: 0;
            font-family: "Space Mono", monospace;
            font-size: clamp(2rem, 4.4vw, 3.65rem);
            line-height: 0.98;
            color: #f4f9ff;
        }
        .hero-kicker {
            margin-bottom: 9px;
            font-family: "Space Mono", monospace;
            font-size: 0.66rem;
            font-weight: 700;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: var(--cyan);
        }
        .hero-subtitle {
            margin: 10px 0 14px 0;
            color: var(--muted);
            font-size: 0.95rem;
        }
        .hero-meta {
            margin-top: 12px;
            color: var(--faint);
            font-size: 0.78rem;
            line-height: 1.45;
        }
        .badge-row {
            display: flex;
            flex-wrap: wrap;
            gap: 7px;
        }
        .badge {
            display: inline-flex;
            align-items: center;
            min-height: 25px;
            padding: 4px 10px;
            border-radius: 999px;
            border: 1px solid rgba(0, 212, 255, 0.26);
            background: rgba(0, 212, 255, 0.08);
            color: #bff4ff;
            font-family: "Space Mono", monospace;
            font-size: 0.62rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }
        .verdict-card, .kpi-card, .insight-card, .status-card {
            border-radius: 8px;
            border: 1px solid var(--line);
            background: var(--panel);
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.04), 0 18px 48px rgba(0,0,0,0.28);
        }
        .verdict-card {
            min-width: 0;
            margin: 2px 2px 2px 0;
            padding: 20px;
            border-color: rgba(34, 243, 182, 0.32);
            background:
                linear-gradient(145deg, rgba(34, 243, 182, 0.13), rgba(47, 128, 255, 0.06)),
                rgba(8, 14, 27, 0.86);
        }
        .verdict-label, .kpi-label, .card-label {
            font-family: "Space Mono", monospace;
            font-size: 0.66rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: var(--faint);
        }
        .verdict-value {
            margin-top: 9px;
            font-family: "Space Mono", monospace;
            font-size: clamp(1.9rem, 3vw, 2.35rem);
            line-height: 1;
            color: var(--green);
        }
        .verdict-delta {
            margin-top: 10px;
            color: #c8fff0;
            font-size: 0.86rem;
            line-height: 1.45;
        }
        .verdict-note {
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid rgba(255,255,255,0.07);
            color: var(--faint);
            font-size: 0.75rem;
            line-height: 1.45;
        }
        .section-title {
            margin: 22px 0 10px 0;
            padding-left: 12px;
            border-left: 3px solid var(--cyan);
            font-family: "Space Mono", monospace;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: #f0f7ff;
        }
        .section-title span {
            color: var(--faint);
            font-weight: 400;
            margin-left: 8px;
            letter-spacing: 0.08em;
        }
        .subsection-label {
            margin: 14px 0 8px 0;
            font-family: "Space Mono", monospace;
            font-size: 0.69rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: #9fb1d0;
        }
        .chart-caption {
            margin: -4px 0 8px 2px;
            color: var(--faint);
            font-size: 0.76rem;
            line-height: 1.45;
        }
        .kpi-card {
            min-height: 142px;
            padding: 16px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            overflow: hidden;
        }
        .kpi-card::before {
            content: "";
            display: block;
            height: 2px;
            margin: -16px -16px 12px -16px;
            background: var(--accent);
            box-shadow: 0 0 24px var(--accent-soft);
        }
        .kpi-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
        }
        .kpi-tag {
            flex: 0 0 auto;
            padding: 3px 7px;
            border-radius: 999px;
            border: 1px solid var(--accent-soft);
            color: var(--accent);
            background: rgba(255,255,255,0.035);
            font-family: "Space Mono", monospace;
            font-size: 0.56rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }
        .kpi-value {
            margin-top: 11px;
            font-family: "Space Mono", monospace;
            font-size: clamp(1.45rem, 2.7vw, 2.05rem);
            line-height: 1;
            color: #f6fbff;
            overflow-wrap: anywhere;
        }
        .kpi-unit {
            margin-top: 5px;
            color: var(--muted);
            font-size: 0.82rem;
        }
        .kpi-delta {
            margin-top: 10px;
            color: var(--delta);
            font-size: 0.78rem;
            line-height: 1.35;
        }
        .insight-card {
            min-height: 116px;
            padding: 16px;
            border-color: rgba(148, 163, 184, 0.14);
        }
        .insight-stat {
            margin-top: 9px;
            font-family: "Space Mono", monospace;
            font-size: 1.28rem;
            line-height: 1.05;
            color: var(--accent);
            overflow-wrap: anywhere;
        }
        .insight-body {
            margin-top: 9px;
            color: var(--muted);
            font-size: 0.84rem;
            line-height: 1.45;
        }
        .story-panel {
            margin-bottom: 10px;
            padding: 16px 18px;
            border-radius: 8px;
            border: 1px solid rgba(34, 243, 182, 0.20);
            background:
                linear-gradient(120deg, rgba(34, 243, 182, 0.08), rgba(47, 128, 255, 0.045)),
                rgba(8, 14, 27, 0.74);
        }
        .story-title {
            font-family: "Space Mono", monospace;
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: #dffdf4;
        }
        .story-body {
            margin-top: 7px;
            color: var(--muted);
            font-size: 0.86rem;
            line-height: 1.5;
        }
        .compare-card {
            min-height: 344px;
            padding: 14px;
            border-radius: 8px;
            border: 1px solid var(--line);
            background: rgba(13, 19, 34, 0.70);
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
        }
        .compare-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.78rem;
        }
        .compare-table th {
            padding: 9px 8px;
            color: var(--faint);
            font-family: "Space Mono", monospace;
            font-size: 0.58rem;
            letter-spacing: 0.10em;
            text-transform: uppercase;
            text-align: left;
            border-bottom: 1px solid rgba(148,163,184,0.12);
        }
        .compare-table td {
            padding: 10px 8px;
            color: #dbe7f6;
            border-bottom: 1px solid rgba(148,163,184,0.07);
            vertical-align: middle;
        }
        .compare-table tr:last-child td { border-bottom: none; }
        .compare-name {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            font-weight: 700;
        }
        .compare-dot {
            width: 8px;
            height: 8px;
            border-radius: 999px;
            box-shadow: 0 0 16px currentColor;
        }
        .compare-badge {
            display: inline-block;
            padding: 3px 7px;
            border-radius: 999px;
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(148,163,184,0.12);
            color: #9fb1d0;
            font-family: "Space Mono", monospace;
            font-size: 0.56rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }
        .compare-badge.best {
            color: var(--green);
            border-color: rgba(34,243,182,0.32);
            background: rgba(34,243,182,0.08);
        }
        .compare-badge.watch {
            color: var(--orange);
            border-color: rgba(255,159,28,0.30);
            background: rgba(255,159,28,0.08);
        }
        .status-card {
            min-height: 92px;
            padding: 13px;
            border-color: rgba(148, 163, 184, 0.13);
        }
        .status-card-value {
            margin-top: 9px;
            font-family: "Space Mono", monospace;
            font-size: 1.08rem;
            color: #f5faff;
        }
        .status-card-meta {
            margin-top: 6px;
            color: var(--faint);
            font-size: 0.73rem;
            line-height: 1.35;
        }
        .status-ok { color: var(--green); }
        .status-warn { color: var(--orange); }
        .stButton > button {
            background: linear-gradient(135deg, rgba(0, 212, 255, 0.15), rgba(47, 128, 255, 0.08)) !important;
            border: 1px solid rgba(0, 212, 255, 0.34) !important;
            color: #c9f7ff !important;
            border-radius: 8px !important;
            font-family: "Space Mono", monospace !important;
            font-size: 0.72rem !important;
            font-weight: 700 !important;
            letter-spacing: 0.08em !important;
            text-transform: uppercase !important;
        }
        div[data-baseweb="select"] > div {
            background: rgba(255, 255, 255, 0.035) !important;
            border: 1px solid rgba(148, 163, 184, 0.14) !important;
            border-radius: 8px !important;
            color: var(--text) !important;
            min-height: 40px !important;
        }
        .stPlotlyChart {
            border-radius: 8px;
            overflow: hidden;
        }
        @media (max-width: 900px) {
            .hero { grid-template-columns: 1fr; padding: 20px; }
            .verdict-value { font-size: 2rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# General helpers
# ---------------------------------------------------------------------------

def clean_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(name).strip().lower())


def parse_value(value: object) -> object:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    lowered = text.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        return float(text)
    except ValueError:
        return text


def is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def as_float(value: object) -> float | None:
    return float(value) if is_number(value) else None


def number_values(values: Iterable[object]) -> list[float]:
    return [float(value) for value in values if is_number(value)]


def safe_mean(values: Iterable[object]) -> float | None:
    nums = number_values(values)
    return statistics.fmean(nums) if nums else None


def safe_max(values: Iterable[object]) -> float | None:
    nums = number_values(values)
    return max(nums) if nums else None


def safe_sum(values: Iterable[object]) -> float | None:
    nums = number_values(values)
    return sum(nums) if nums else None


def safe_last(values: Iterable[object]) -> object | None:
    for value in reversed(list(values)):
        if value not in (None, ""):
            return value
    return None


def pct_lower(target: float | None, baseline: float | None) -> float | None:
    if target is None or baseline is None or abs(baseline) < 1e-9:
        return None
    return (baseline - target) / abs(baseline) * 100


def pct_higher(target: float | None, baseline: float | None) -> float | None:
    if target is None or baseline is None or abs(baseline) < 1e-9:
        return None
    return (target - baseline) / abs(baseline) * 100


def fmt_value(value: object, decimals: int = 1, compact: bool = False) -> str:
    numeric = as_float(value)
    if numeric is None:
        return "—"
    if compact and abs(numeric) >= 1000:
        text = f"{numeric / 1000:.1f}k"
        return text.replace(".0k", "k")
    if abs(numeric - round(numeric)) < 1e-9:
        return f"{numeric:.0f}"
    return f"{numeric:.{decimals}f}"


def format_delta(delta: float | None, better_word: str = "lower") -> tuple[str, str]:
    if delta is None:
        return "Baseline unavailable", "#8fa0bd"
    if delta >= 0:
        return f"{delta:.1f}% {better_word} vs Fixed", "#22f3b6"
    inverse = "higher" if better_word == "lower" else "lower"
    return f"{abs(delta):.1f}% {inverse} vs Fixed", "#ff9f1c"


def escape_text(value: object) -> str:
    return html.escape(str(value))


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    color = hex_color.lstrip("#")
    if len(color) != 6:
        return f"rgba(0, 212, 255, {alpha})"
    r = int(color[0:2], 16)
    g = int(color[2:4], 16)
    b = int(color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def rolling_mean(values: list[object], window: int) -> list[float | None]:
    if window <= 1:
        return [as_float(value) for value in values]
    out: list[float | None] = []
    numeric: list[float] = []
    for value in values:
        num = as_float(value)
        numeric.append(num if num is not None else float("nan"))
        recent = [item for item in numeric[-window:] if math.isfinite(item)]
        out.append(statistics.fmean(recent) if recent else None)
    return out


def find_column(result: ResultSet, aliases: Iterable[str], *, fuzzy: bool = False) -> str | None:
    normalized_aliases = [clean_name(alias) for alias in aliases]
    for alias in normalized_aliases:
        if alias in result.normalized_columns:
            return result.normalized_columns[alias]
    if not fuzzy:
        return None
    for original in result.original_columns:
        cleaned = clean_name(original)
        if any(alias and alias in cleaned for alias in normalized_aliases):
            return original
    return None


def get_series(result: ResultSet, aliases: Iterable[str], *, fuzzy: bool = False) -> list[object]:
    column = find_column(result, aliases, fuzzy=fuzzy)
    return result.columns.get(column, []) if column else []


def row_sum_series(result: ResultSet, specs: Iterable[tuple[str, Iterable[str]]]) -> list[float]:
    columns = [find_column(result, aliases) for _, aliases in specs]
    columns = [column for column in columns if column]
    if not columns:
        return []
    length = max((len(result.columns.get(column, [])) for column in columns), default=0)
    totals: list[float] = []
    for idx in range(length):
        total = 0.0
        has_value = False
        for column in columns:
            values = result.columns.get(column, [])
            if idx < len(values):
                num = as_float(values[idx])
                if num is not None:
                    total += num
                    has_value = True
        totals.append(total if has_value else float("nan"))
    return totals


def ordered_loaded_results(results: dict[str, ResultSet]) -> list[ResultSet]:
    return [results[key] for key in CONTROLLERS if key in results and results[key].found and results[key].row_count > 0]


# ---------------------------------------------------------------------------
# Data loading and metrics
# ---------------------------------------------------------------------------

def load_results() -> dict[str, ResultSet]:
    loaded: dict[str, ResultSet] = {}
    for key, cfg in CONTROLLERS.items():
        path = DATA_DIR / cfg["file"]
        found = path.exists()
        rows: list[dict[str, object]] = []
        columns: dict[str, list[object]] = {}
        original_columns: list[str] = []
        error = ""
        modified = ""

        if found:
            try:
                modified = time.strftime("%Y-%m-%d %H:%M", time.localtime(path.stat().st_mtime))
                with open(path, newline="", encoding="utf-8-sig", errors="replace") as handle:
                    reader = csv.DictReader(handle)
                    original_columns = list(reader.fieldnames or [])
                    columns = {name: [] for name in original_columns}
                    for row in reader:
                        parsed_row: dict[str, object] = {}
                        for name in original_columns:
                            parsed = parse_value(row.get(name))
                            parsed_row[name] = parsed
                            columns[name].append(parsed)
                        rows.append(parsed_row)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"

        loaded[key] = ResultSet(
            key=key,
            label=str(cfg["label"]),
            short=str(cfg["short"]),
            color=str(cfg["color"]),
            path=path,
            found=found and not error,
            rows=rows,
            columns=columns,
            original_columns=original_columns,
            normalized_columns={clean_name(column): column for column in original_columns},
            error=error,
            modified=modified,
        )
    return loaded


@st.cache_data(ttl=120, show_spinner=False)
def load_qtable_info() -> dict[str, object]:
    if not QTABLE_PATH.exists():
        return {"exists": False, "entries": None, "error": "", "modified": ""}
    try:
        with open(QTABLE_PATH, "rb") as handle:
            qtable = pickle.load(handle)
        entries = len(qtable) if hasattr(qtable, "__len__") else None
        modified = time.strftime("%Y-%m-%d %H:%M", time.localtime(QTABLE_PATH.stat().st_mtime))
        return {"exists": True, "entries": entries, "error": "", "modified": modified}
    except Exception as exc:
        return {"exists": True, "entries": None, "error": f"{type(exc).__name__}: {exc}", "modified": ""}


def compute_phase_changes(result: ResultSet) -> int | None:
    logged_changes = get_series(result, PHASE_CHANGE_ALIASES)
    if logged_changes:
        total = safe_sum(logged_changes)
        return int(total) if total is not None else None
    phase_values = [value for value in get_series(result, PHASE_ALIASES) if value is not None]
    if len(phase_values) < 2:
        return None
    return sum(1 for prev, cur in zip(phase_values, phase_values[1:]) if cur != prev)


def compute_reward(result: ResultSet) -> float | None:
    reward_col = find_column(result, REWARD_ALIASES)
    if not reward_col:
        return None
    values = result.columns.get(reward_col, [])
    if clean_name(reward_col) in {clean_name("total_reward"), clean_name("episode_reward")}:
        return as_float(safe_last(values))
    return safe_sum(values)


def compute_metrics(results: dict[str, ResultSet]) -> dict[str, dict[str, object]]:
    metrics: dict[str, dict[str, object]] = {}
    for result in ordered_loaded_results(results):
        time_series = get_series(result, TIME_ALIASES) or list(range(1, result.row_count + 1))
        total_wait = get_series(result, TOTAL_WAIT_ALIASES, fuzzy=True)
        avg_wait = get_series(result, AVG_WAIT_ALIASES, fuzzy=True)
        wait_basis = "total_waiting_time" if total_wait else "avg_waiting_time"
        avg_wait_value = safe_mean(total_wait) if total_wait else safe_mean(avg_wait)
        total_wait_average = safe_mean(total_wait)

        total_queue_logged = get_series(result, TOTAL_QUEUE_ALIASES)
        queue_series = total_queue_logged or row_sum_series(result, QUEUE_APPROACH_COLS)
        peak_queue_logged = get_series(result, PEAK_QUEUE_ALIASES)
        peak_queue = safe_max(peak_queue_logged) if peak_queue_logged else safe_max(queue_series)

        arrived = get_series(result, ARRIVED_ALIASES)
        departed = get_series(result, DEPARTED_ALIASES)
        total_vehicles = get_series(result, TOTAL_VEHICLE_ALIASES)
        if arrived:
            throughput = safe_max(arrived)
            throughput_source = "vehicles arrived"
        elif departed:
            throughput = safe_max(departed)
            throughput_source = "vehicles departed"
        else:
            throughput = safe_max(total_vehicles)
            throughput_source = "max active vehicles"

        emergency_values = get_series(result, EMERGENCY_ALIASES)
        emergency_steps = sum(1 for value in emergency_values if (as_float(value) or 0) > 0)
        time_nums = number_values(time_series)
        duration = max(time_nums) - min(time_nums) if len(time_nums) > 1 else None

        metrics[result.label] = {
            "key": result.key,
            "label": result.label,
            "short": result.short,
            "color": result.color,
            "rows": result.row_count,
            "avg_wait": avg_wait_value,
            "avg_wait_unit": "s/veh" if wait_basis == "avg_waiting_time" else "s",
            "wait_basis": wait_basis,
            "avg_total_wait": total_wait_average,
            "total_wait_series": total_wait,
            "time_series": time_series,
            "queue_series": queue_series,
            "peak_queue": peak_queue,
            "throughput": throughput,
            "throughput_source": throughput_source,
            "duration": duration,
            "emergency_steps": emergency_steps,
            "phase_changes": compute_phase_changes(result),
            "reward_total": compute_reward(result),
            "epsilon": as_float(safe_last(get_series(result, EPSILON_ALIASES))),
        }
    return metrics


def best_by_metric(
    metrics: dict[str, dict[str, object]],
    field: str,
    *,
    higher_is_better: bool = False,
) -> tuple[str, dict[str, object]] | None:
    candidates = [(label, metric) for label, metric in metrics.items() if as_float(metric.get(field)) is not None]
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: as_float(item[1].get(field)) or 0, reverse=higher_is_better)[0]


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def apply_plot_theme(fig: go.Figure, *, height: int = 360, showlegend: bool = True) -> go.Figure:
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#dbe7f6", size=12),
        margin=dict(l=52, r=22, t=54, b=48),
        showlegend=showlegend,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.03,
            xanchor="right",
            x=1,
            bgcolor="rgba(7, 11, 21, 0.78)",
            bordercolor="rgba(148,163,184,0.14)",
            borderwidth=1,
            font=dict(size=10),
        ),
        hoverlabel=dict(bgcolor="rgba(7, 11, 21, 0.96)", bordercolor="rgba(0, 212, 255, 0.22)"),
        hovermode="x unified",
    )
    fig.update_xaxes(
        gridcolor="rgba(148,163,184,0.09)",
        zeroline=False,
        linecolor="rgba(148,163,184,0.14)",
        tickfont=dict(color="#91a4c2"),
        title_font=dict(color="#9fb1d0", size=11),
        title_standoff=12,
    )
    fig.update_yaxes(
        gridcolor="rgba(148,163,184,0.09)",
        zeroline=False,
        linecolor="rgba(148,163,184,0.14)",
        tickfont=dict(color="#91a4c2"),
        title_font=dict(color="#9fb1d0", size=11),
        title_standoff=12,
    )
    return fig


def section_title(title: str, detail: str | None = None) -> None:
    suffix = f"<span>{escape_text(detail)}</span>" if detail else ""
    st.markdown(f'<div class="section-title">{escape_text(title)}{suffix}</div>', unsafe_allow_html=True)


def subsection_label(label: str) -> None:
    st.markdown(f'<div class="subsection-label">{escape_text(label)}</div>', unsafe_allow_html=True)


def chart_caption(text: str) -> None:
    st.markdown(f'<div class="chart-caption">{escape_text(text)}</div>', unsafe_allow_html=True)


def metric_card(
    label: str,
    value: str,
    unit: str,
    delta: str,
    accent: str,
    delta_color: str = "#8fa0bd",
    tag: str = "",
) -> str:
    tag_markup = f'<div class="kpi-tag">{escape_text(tag)}</div>' if tag else ""
    return (
        f'<div class="kpi-card" style="--accent:{accent};--accent-soft:{hex_to_rgba(accent, 0.24)};--delta:{delta_color};">'
        f'<div class="kpi-header"><div class="kpi-label">{escape_text(label)}</div>{tag_markup}</div>'
        f'<div class="kpi-value">{escape_text(value)}</div>'
        f'<div class="kpi-unit">{escape_text(unit)}</div>'
        f'<div class="kpi-delta">{escape_text(delta)}</div></div>'
    )


def insight_card(label: str, stat: str, body: str, accent: str) -> str:
    return (
        f'<div class="insight-card" style="--accent:{accent};">'
        f'<div class="card-label">{escape_text(label)}</div>'
        f'<div class="insight-stat">{escape_text(stat)}</div>'
        f'<div class="insight-body">{escape_text(body)}</div></div>'
    )


def story_panel(title: str, body: str) -> str:
    return (
        '<div class="story-panel">'
        f'<div class="story-title">{escape_text(title)}</div>'
        f'<div class="story-body">{escape_text(body)}</div></div>'
    )


def status_card(result: ResultSet) -> str:
    if result.error:
        status, cls, meta = "Error", "status-warn", result.error
    elif result.found and result.row_count:
        status, cls, meta = "Loaded", "status-ok", f"{result.row_count:,} rows · {result.column_count} columns"
    elif result.path.exists():
        status, cls, meta = "Empty", "status-warn", f"Found {result.path.name}, but no rows were parsed"
    else:
        status, cls, meta = "Missing", "status-warn", f"Expected data/{result.path.name}"
    return (
        '<div class="status-card">'
        f'<div class="card-label">{escape_text(result.label)}</div>'
        f'<div class="status-card-value {cls}">{escape_text(status)}</div>'
        f'<div class="status-card-meta">{escape_text(meta)}</div></div>'
    )


def render_comparison_table(metrics: dict[str, dict[str, object]]) -> None:
    best_wait = best_by_metric(metrics, "avg_wait")
    worst_wait = best_by_metric(metrics, "avg_wait", higher_is_better=True)
    rows: list[str] = []
    for key in CONTROLLERS:
        label = str(CONTROLLERS[key]["label"])
        metric = metrics.get(label)
        if not metric:
            continue
        badge = "Loaded"
        badge_cls = ""
        if best_wait and label == best_wait[0]:
            badge, badge_cls = "Best", " best"
        elif worst_wait and label == worst_wait[0] and best_wait and worst_wait[0] != best_wait[0]:
            badge, badge_cls = "Watch", " watch"
        rows.append(
            "<tr><td><span class=\"compare-name\">"
            f"<span class=\"compare-dot\" style=\"background:{metric['color']}; color:{metric['color']};\"></span>"
            f"{escape_text(label)}</span></td>"
            f"<td>{escape_text(fmt_value(metric.get('avg_wait'), 2))}</td>"
            f"<td>{escape_text(fmt_value(metric.get('peak_queue'), 0))}</td>"
            f"<td>{escape_text(fmt_value(metric.get('throughput'), 0))}</td>"
            f"<td><span class=\"compare-badge{badge_cls}\">{escape_text(badge)}</span></td></tr>"
        )
    table_html = (
        '<div class="compare-card"><table class="compare-table"><thead><tr>'
        "<th>Controller</th><th>Avg wait</th><th>Peak queue</th><th>Flow</th><th>Read</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )
    st.markdown(table_html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Render sections
# ---------------------------------------------------------------------------

def render_sidebar(results: dict[str, ResultSet], metrics: dict[str, dict[str, object]]) -> str:
    with st.sidebar:
        identity_html = (
            '<div class="sb-card identity"><div class="sb-identity"><div class="sb-logo">🚦</div><div>'
            '<div class="sb-title">AI TRAFFIC BRAIN</div><div class="sb-sub">Smart City Command Center</div>'
            '</div></div><div class="sb-online"><span class="sb-online-dot"></span>SYSTEM ONLINE</div></div>'
        )
        st.markdown(identity_html, unsafe_allow_html=True)

        project_info_html = (
            '<div class="sb-card"><div class="sb-card-title">Project Information</div>'
            '<div class="sb-label">Project Team</div>'
            '<div class="sb-value strong">ACHAAR Mohammed Amine</div>'
            '<div class="sb-value strong">ZAKANE Mohamed</div>'
            '<div class="sb-label" style="margin-top:10px;">Supervisor</div>'
            '<div class="sb-value strong">Dr. EN-NOUAARY ABDELSLAM</div>'
            '<div class="sb-label" style="margin-top:10px;">Institution</div>'
            '<div class="sb-value">Institut National des Postes et Télécommunications</div>'
            '<div class="sb-accent">INPT · Rabat, Morocco</div></div>'
        )
        st.markdown(project_info_html, unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown('<div class="sb-card-title">Controls</div>', unsafe_allow_html=True)
            st.markdown('<div class="sb-label">Dashboard focus</div>', unsafe_allow_html=True)
            focus_options = ["Auto: Best Controller"] + list(metrics.keys())
            selected_focus = st.selectbox("Controller focus", options=focus_options, label_visibility="collapsed")
            focus = "Best available" if selected_focus == "Auto: Best Controller" else selected_focus

            st.markdown('<div class="sb-label">Simulation mode</div>', unsafe_allow_html=True)
            mode_labels = {
                "fixed": "Fixed cycle",
                "smart": "Smart adaptive",
                "vision": "Vision camera AI",
                "rl": "Q-learning AI",
            }
            sim_mode = st.selectbox(
                "Simulation mode",
                options=list(mode_labels.keys()),
                format_func=lambda mode: mode_labels[mode],
                label_visibility="collapsed",
                key="sidebar_sim_mode",
            )
            gui_flag = st.checkbox("Open SUMO GUI", value=False, key="sidebar_sumo_gui")

            if st.button("Run Simulation", use_container_width=True, type="primary"):
                cmd = [sys.executable, str(ROOT / "main.py"), "--mode", sim_mode]
                if gui_flag:
                    cmd.append("--gui")
                status_box = st.empty()
                with st.spinner(f"Running {mode_labels[sim_mode]} simulation..."):
                    try:
                        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
                    except FileNotFoundError:
                        status_box.error("main.py was not found. Check the project root path.")
                    except Exception as exc:
                        status_box.error(f"Simulation could not start: {type(exc).__name__}: {exc}")
                    else:
                        if result.returncode == 0:
                            status_box.success(f"{mode_labels[sim_mode]} simulation complete.")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            details = (result.stderr or result.stdout or "No process output was captured.")[-2000:]
                            status_box.error("Simulation failed. See details below.")
                            st.code(details, language="bash")

        st.markdown('<div class="sb-footer"><div>Academic Project</div><div>2025–2026</div></div>', unsafe_allow_html=True)
    return focus


def render_header(metrics: dict[str, dict[str, object]]) -> None:
    best = best_by_metric(metrics, "avg_wait")
    fixed = metrics.get("Fixed")
    loaded_count = len(metrics)
    if best:
        best_label, best_metric = best
        improvement = pct_lower(as_float(best_metric.get("avg_wait")), as_float(fixed.get("avg_wait")) if fixed else None)
        improvement_text, _ = format_delta(improvement, "lower")
        verdict = best_label
        detail = improvement_text if improvement is not None else "Awaiting fixed baseline"
    else:
        verdict = "Awaiting Data"
        detail = "Load result CSVs to compute the winner"

    st.markdown(
        f"""
        <div class="hero">
            <div>
                <div class="hero-kicker">Executive verdict</div>
                <h1 class="hero-title">AI Traffic Brain</h1>
                <div class="hero-subtitle">Intelligent Urban Traffic Management System</div>
                <div class="badge-row">
                    <span class="badge">SUMO Simulation</span>
                    <span class="badge">Adaptive Control</span>
                    <span class="badge">RL Policy Review</span>
                </div>
                <div class="hero-meta">{loaded_count}/4 controller result files loaded · Decision metric: lowest average waiting time</div>
            </div>
            <div class="verdict-card">
                <div class="verdict-label">Best Controller</div>
                <div class="verdict-value">{escape_text(verdict)}</div>
                <div class="verdict-delta">{escape_text(detail)}</div>
                <div class="verdict-note">Queue pressure, throughput, and RL signals are reviewed below for operational context.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_cards(metrics: dict[str, dict[str, object]]) -> None:
    section_title("KPI Overview", "best and worst controller signals")
    if not metrics:
        st.warning("No result data loaded yet. Expected CSV files in the data/ directory.")
        return
    fixed = metrics.get("Fixed")
    best_wait = best_by_metric(metrics, "avg_wait")
    worst_wait = best_by_metric(metrics, "avg_wait", higher_is_better=True)
    best_queue = best_by_metric(metrics, "peak_queue")
    best_throughput = best_by_metric(metrics, "throughput", higher_is_better=True)
    cols = st.columns(4)

    if best_wait:
        label, metric = best_wait
        delta, color = format_delta(pct_lower(as_float(metric.get("avg_wait")), as_float(fixed.get("avg_wait")) if fixed else None), "lower")
        cols[0].markdown(
            metric_card("Lowest avg wait", fmt_value(metric.get("avg_wait"), 2), f"{label} controller", delta, str(metric["color"]), color, "Best"),
            unsafe_allow_html=True,
        )
    if worst_wait:
        label, metric = worst_wait
        best_value = as_float(best_wait[1].get("avg_wait")) if best_wait else None
        gap = pct_higher(as_float(metric.get("avg_wait")), best_value)
        delta, color = ("No spread detected", "#8fa0bd") if gap is None or label == (best_wait[0] if best_wait else "") else (f"{gap:.1f}% higher than best", "#ff9f1c")
        cols[1].markdown(
            metric_card("Highest avg wait", fmt_value(metric.get("avg_wait"), 2), f"{label} controller", delta, str(metric["color"]), color, "Watch"),
            unsafe_allow_html=True,
        )
    if best_queue:
        label, metric = best_queue
        delta, color = format_delta(pct_lower(as_float(metric.get("peak_queue")), as_float(fixed.get("peak_queue")) if fixed else None), "lower")
        cols[2].markdown(metric_card("Queue control", fmt_value(metric.get("peak_queue"), 0), f"{label} · lowest peak queue", delta, str(metric["color"]), color, "Best"), unsafe_allow_html=True)
    if best_throughput:
        label, metric = best_throughput
        delta, color = format_delta(pct_higher(as_float(metric.get("throughput")), as_float(fixed.get("throughput")) if fixed else None), "higher")
        cols[3].markdown(
            metric_card("Flow leader", fmt_value(metric.get("throughput"), 0), f"{label} · max active vehicles", delta, str(metric["color"]), color, "Best"),
            unsafe_allow_html=True,
        )


def render_controller_comparison(metrics: dict[str, dict[str, object]]) -> None:
    if not metrics:
        return
    section_title("Controller Comparison", "delay, queue, and flow scorecard")
    left, right = st.columns([1.55, 1])
    labels = list(metrics.keys())
    colors = [str(metrics[label]["color"]) for label in labels]
    avg_waits = [as_float(metrics[label].get("avg_wait")) for label in labels]

    with left:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=labels,
                y=avg_waits,
                marker=dict(color=colors, line=dict(color="rgba(255,255,255,0.22)", width=1)),
                text=[fmt_value(value, 2) for value in avg_waits],
                textposition="outside",
                cliponaxis=False,
                hovertemplate="<b>%{x}</b><br>Average waiting time: %{y:.3f}s<extra></extra>",
            )
        )
        apply_plot_theme(fig, height=344, showlegend=False)
        fig.update_layout(
            title=dict(text="Average Waiting Time by Controller", font=dict(size=15, color="#f0f7ff", family="Space Mono"), x=0),
            yaxis_title="Average waiting time",
            xaxis_title="Controller",
            bargap=0.42,
        )
        st.plotly_chart(fig, width="stretch")
        chart_caption("Lower bars indicate a controller that clears vehicles with less accumulated delay.")
    with right:
        render_comparison_table(metrics)
        chart_caption("Best and watch labels are based on average waiting time.")


def render_waiting_time_chart(metrics: dict[str, dict[str, object]], *, focus_controller: str) -> None:
    if not metrics:
        return
    section_title("Traffic Evolution Over Time", "smoothed waiting-load timeline")
    best = best_by_metric(metrics, "avg_wait")
    highlight = best[0] if focus_controller == "Best available" and best else focus_controller
    fig = go.Figure()
    trace_count = 0
    for label, metric in metrics.items():
        x_values = metric.get("time_series") or []
        y_values = metric.get("total_wait_series") or []
        if not y_values:
            continue
        window = max(5, min(24, len(y_values) // 180 or 5))
        is_focus = label == highlight
        fig.add_trace(
            go.Scatter(
                x=x_values,
                y=rolling_mean(list(y_values), window),
                mode="lines",
                name=label,
                line=dict(color=str(metric["color"]), width=4 if is_focus else 2.4),
                opacity=0.98 if is_focus else 0.62,
                hovertemplate=f"<b>{label}</b><br>Time: %{{x:.0f}}s<br>Smoothed total wait: %{{y:.1f}}s<extra></extra>",
            )
        )
        trace_count += 1
    if trace_count == 0:
        st.info("No total waiting-time column was detected in the loaded CSV files.")
        return
    apply_plot_theme(fig, height=410, showlegend=True)
    fig.update_layout(
        title=dict(text="Waiting Load Across the Simulation", font=dict(size=15, color="#f0f7ff", family="Space Mono"), x=0),
        xaxis_title="Simulation time (seconds)",
        yaxis_title="Total waiting time (seconds)",
    )
    st.plotly_chart(fig, width="stretch")
    chart_caption("The selected focus controller is drawn with the strongest line; other controllers remain visible for context.")


def render_intersection_breakdown(results: dict[str, ResultSet], metrics: dict[str, dict[str, object]]) -> None:
    loaded = ordered_loaded_results(results)
    if not loaded:
        return
    has_intersection_data = any(find_column(result, aliases) for result in loaded for _, aliases in INTERSECTION_WAIT_COLS)
    has_approach_data = any(find_column(result, aliases) for result in loaded for _, aliases in APPROACH_WAIT_COLS)
    if not has_intersection_data and not has_approach_data:
        return

    subsection_label("Intersection delay split")
    if has_intersection_data:
        fig = go.Figure()
        x_labels = [name for name, _ in INTERSECTION_WAIT_COLS]
        for result in loaded:
            y_values = [safe_mean(get_series(result, aliases)) for _, aliases in INTERSECTION_WAIT_COLS]
            if any(value is not None for value in y_values):
                fig.add_trace(
                    go.Bar(
                        name=result.label,
                        x=x_labels,
                        y=y_values,
                        marker_color=result.color,
                        hovertemplate="<b>%{fullData.name}</b><br>%{x}: %{y:.2f}s average wait<extra></extra>",
                    )
                )
        apply_plot_theme(fig, height=322, showlegend=True)
        fig.update_layout(
            title=dict(text="Average Wait by Intersection", font=dict(size=14, color="#f0f7ff", family="Space Mono"), x=0),
            barmode="group",
            bargap=0.22,
            xaxis_title="Intersection",
            yaxis_title="Average waiting time (s)",
        )
        st.plotly_chart(fig, width="stretch")
        chart_caption("Grouped bars reveal whether delay is concentrated around a specific intersection.")
        return

    controllers: list[str] = []
    z_values: list[list[float | None]] = []
    for result in loaded:
        row = [safe_mean(get_series(result, aliases)) for _, aliases in APPROACH_WAIT_COLS]
        if any(value is not None for value in row):
            controllers.append(result.label)
            z_values.append(row)
    if not z_values:
        return
    fig = go.Figure(
        data=go.Heatmap(
            z=z_values,
            x=[name for name, _ in APPROACH_WAIT_COLS],
            y=controllers,
            colorscale=[[0.0, "#06111d"], [0.45, "#2f80ff"], [0.72, "#9b5cff"], [1.0, "#ff9f1c"]],
            colorbar=dict(title="seconds"),
            hovertemplate="<b>%{y}</b><br>%{x}: %{z:.2f}s average wait<extra></extra>",
        )
    )
    apply_plot_theme(fig, height=312, showlegend=False)
    fig.update_layout(
        title=dict(text="Approach-Level Delay Heatmap", font=dict(size=14, color="#f0f7ff", family="Space Mono"), x=0),
        xaxis_title="Approach",
        yaxis_title="Controller",
    )
    st.plotly_chart(fig, width="stretch")
    chart_caption("Warmer cells identify approaches where queues are more likely to accumulate.")


def render_rl_insights(metrics: dict[str, dict[str, object]], qtable_info: dict[str, object]) -> None:
    section_title("AI / RL Analytics", "policy memory, control activity, and learning signals")
    rl = metrics.get("RL")
    fixed = metrics.get("Fixed")
    smart = metrics.get("Smart")
    if not rl:
        st.info("RL result data is not loaded. The section will populate when data/results_rl.csv is available.")
        return

    entries = qtable_info.get("entries")
    reward = rl.get("reward_total")
    epsilon = rl.get("epsilon")
    phase_changes = rl.get("phase_changes")
    improvement = pct_lower(as_float(rl.get("avg_wait")), as_float(fixed.get("avg_wait")) if fixed else None)
    improvement_text, improvement_color = format_delta(improvement, "lower")
    improvement_value = f"{improvement:.1f}%" if improvement is not None else "—"

    reward_text = fmt_value(reward, 1, compact=True)
    epsilon_text = fmt_value(epsilon, 4)
    if reward is None and epsilon is None:
        signal_delta, signal_color = "Reward and epsilon were not exported", "#8fa0bd"
    elif reward is None:
        signal_delta, signal_color = "Reward missing · epsilon logged", "#8fa0bd"
    elif epsilon is None:
        signal_delta, signal_color = "Reward logged · epsilon missing", "#8fa0bd"
    else:
        signal_delta, signal_color = "Both learning signals logged", "#22f3b6"

    if improvement is not None and improvement >= 0:
        story_title = "RL is reducing delay against the fixed baseline"
        story_body = f"The learned policy records {improvement_text}. Use phase changes and Q-table size to judge whether that gain comes with stable behavior."
    elif improvement is not None:
        story_title = "RL needs another look on this run"
        story_body = f"The current RL result is {improvement_text}. Reward, epsilon, and phase-change signals remain visible for tuning."
    else:
        story_title = "RL comparison is waiting for a fixed baseline"
        story_body = "RL data loaded, but the fixed baseline is missing or incomplete, so improvement cannot be computed yet."
    st.markdown(story_panel(story_title, story_body), unsafe_allow_html=True)

    cols = st.columns(4)
    cols[0].markdown(metric_card("Q-table entries", fmt_value(entries, 0, compact=True), "policy memory size", "Loaded from data/qtable.pkl" if entries is not None else "Q-table not available", "#22f3b6", "#22f3b6" if entries is not None else "#8fa0bd", "Policy"), unsafe_allow_html=True)
    cols[1].markdown(metric_card("RL vs Fixed", improvement_value, "average wait reduction", improvement_text, "#00d4ff", improvement_color, "Delta"), unsafe_allow_html=True)
    cols[2].markdown(metric_card("Phase changes", fmt_value(phase_changes, 0), "signal timing activity", "Computed from phase transitions" if phase_changes is not None else "Not available in CSV", "#2f80ff", "#8fa0bd" if phase_changes is None else "#2f80ff", "Control"), unsafe_allow_html=True)
    cols[3].markdown(metric_card("Reward / epsilon", f"{reward_text} / {epsilon_text}", "training signal coverage", signal_delta, "#9b5cff", signal_color, "Logs"), unsafe_allow_html=True)

    smart_note = "Rule-based stability baseline"
    if smart and smart.get("phase_changes") is not None:
        smart_note = f"{fmt_value(smart.get('phase_changes'), 0)} phase changes detected"
    cards = st.columns(3)
    cards[0].markdown(insight_card("Delay story", improvement_text, "The primary RL question is whether the learned policy lowers average waiting time versus fixed timing.", "#22f3b6"), unsafe_allow_html=True)
    cards[1].markdown(insight_card("Signal coverage", "Logged" if reward is not None or epsilon is not None else "Missing", signal_delta, "#00d4ff"), unsafe_allow_html=True)
    cards[2].markdown(insight_card("Controller activity", fmt_value(phase_changes, 0), f"RL phase activity is compared with Smart control context: {smart_note}.", "#2f80ff"), unsafe_allow_html=True)


def render_insight_cards(results: dict[str, ResultSet], metrics: dict[str, dict[str, object]]) -> None:
    if not metrics:
        return
    section_title("Key Insights", "presentation-ready takeaways")
    best = best_by_metric(metrics, "avg_wait")
    vision_result = results.get("vision")
    fixed = metrics.get("Fixed")
    insight_items: list[tuple[str, str, str, str]] = []
    if best:
        label, metric = best
        insight_items.append(("Lowest delay", label, f"{label} currently leads the scenario with {fmt_value(metric.get('avg_wait'), 2)} {metric.get('avg_wait_unit', 's')} average delay.", str(metric.get("color"))))
    if vision_result and vision_result.found:
        reasons = get_series(vision_result, REASON_ALIASES)
        emergency_reasons = [reason for reason in reasons if isinstance(reason, str) and ("camera" in reason.lower() or "emg" in reason.lower() or "emergency" in reason.lower())]
        if emergency_reasons:
            insight_items.append(("Camera intelligence", f"{len(emergency_reasons):,} steps", f"Vision mode logged {len(emergency_reasons):,} camera or emergency-aware control steps.", "#9b5cff"))
        else:
            insight_items.append(("Camera intelligence", "Vision loaded", "Vision mode is available for camera-aware emergency behavior comparison.", "#9b5cff"))
    if fixed:
        best_label = best[0] if best else "adaptive control"
        body = "Fixed timing is a useful baseline, but adaptive controllers respond to changing demand."
        if best_label != "Fixed":
            body = f"Fixed timing anchors the comparison, while {best_label} adapts better to the loaded scenario."
        insight_items.append(("Baseline behavior", f"{fmt_value(fixed.get('avg_wait'), 2)} {fixed.get('avg_wait_unit', 's')}", body, "#ff9f1c"))
    for col, item in zip(st.columns(3), insight_items[:3]):
        label, stat, body, accent = item
        col.markdown(insight_card(label, stat, body, accent), unsafe_allow_html=True)


def render_data_status(results: dict[str, ResultSet]) -> None:
    section_title("Data Quality / File Status", "source freshness and schema checks")
    status_cols = st.columns(len(results) or 1)
    for col, result in zip(status_cols, results.values()):
        col.markdown(status_card(result), unsafe_allow_html=True)
    with st.expander("Column coverage and file diagnostics", expanded=False):
        rows = []
        for result in results.values():
            if result.error:
                status = "Error"
            elif result.found and result.row_count:
                status = "Loaded"
            elif result.path.exists():
                status = "Empty"
            else:
                status = "Missing"
            rows.append(
                {
                    "Controller": result.label,
                    "File": result.path.name,
                    "Status": status,
                    "Rows": result.row_count,
                    "Columns": result.column_count,
                    "Modified": result.modified or "—",
                    "Issue": result.error or "",
                }
            )
        st.dataframe(rows, width="stretch", hide_index=True)
        missing = [name for name in EXPECTED_FILES if not (DATA_DIR / name).exists()]
        if missing:
            st.warning("Missing result files: " + ", ".join(missing))
        for result in results.values():
            if result.original_columns:
                st.markdown(
                    f"**{escape_text(result.label)} columns:** "
                    + ", ".join(f"`{escape_text(col)}`" for col in result.original_columns)
                )


def render_footer() -> None:
    st.markdown(
        """
        <div style="margin-top: 34px; padding-top: 18px; border-top: 1px solid rgba(148,163,184,0.10);
                    color:#53637f; font-size:0.76rem; text-align:center;">
            AI Traffic Brain · Intelligent Adaptive Traffic Light Control · INPT
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# App entry point
# ---------------------------------------------------------------------------

def main() -> None:
    set_page_config()
    inject_global_css()

    results = load_results()
    metrics = compute_metrics(results)
    qtable_info = load_qtable_info()

    focus = render_sidebar(results, metrics)
    render_header(metrics)
    render_kpi_cards(metrics)
    render_controller_comparison(metrics)
    render_waiting_time_chart(metrics, focus_controller=focus)
    render_intersection_breakdown(results, metrics)
    render_rl_insights(metrics, qtable_info)
    render_insight_cards(results, metrics)
    render_data_status(results)
    render_footer()


if __name__ == "__main__":
    main()
