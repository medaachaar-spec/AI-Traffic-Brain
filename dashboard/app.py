"""
AI Traffic Brain — Streamlit comparison dashboard.
Uses only: streamlit, plotly, subprocess, csv (stdlib), statistics (stdlib),
           collections (stdlib).

Run with:
    streamlit run dashboard/app.py
"""

import csv
import statistics
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT       = Path(__file__).resolve().parent.parent
DATA_DIR   = ROOT / "data"
MAIN_PY    = ROOT / "main.py"
FIXED_CSV  = DATA_DIR / "results_fixed.csv"
SMART_CSV  = DATA_DIR / "results_smart.csv"
VISION_CSV = DATA_DIR / "results_vision.csv"

# ---------------------------------------------------------------------------
# Colour palette  ── Smart City Command Center
# ---------------------------------------------------------------------------
C_FIXED   = "#ff9500"   # amber
C_SMART   = "#00d4ff"   # electric teal
C_VISION  = "#8b5cf6"   # purple
C_RL      = "#10b981"   # green
C_WARN    = "#ff4757"   # alert red
C_TEXT    = "#c8d4f0"
C_SUBTEXT = "#4a5a7a"
C_SURFACE = "rgba(255,255,255,0.035)"
C_BORDER  = "rgba(255,255,255,0.07)"
C_BG      = "#0a0e1a"

AREA_COLOURS = ["#00d4ff", "#ff9500", "#8b5cf6", "#10b981"]
AREA_FILL_COLOURS = [
    "rgba(0,212,255,0.12)",
    "rgba(255,149,0,0.12)",
    "rgba(139,92,246,0.12)",
    "rgba(16,185,129,0.12)",
]

PLOTLY_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor ="rgba(0,0,0,0)",
    font=dict(color=C_TEXT, family="'Space Mono', 'Courier New', monospace", size=11),
    xaxis=dict(
        showgrid=False,
        zerolinecolor="rgba(255,255,255,0.06)",
        linecolor="rgba(255,255,255,0.05)",
        tickfont=dict(family="'Space Mono', 'Courier New', monospace", size=10),
    ),
    yaxis=dict(
        showgrid=False,
        zerolinecolor="rgba(255,255,255,0.06)",
        linecolor="rgba(255,255,255,0.05)",
        tickfont=dict(family="'Space Mono', 'Courier New', monospace", size=10),
    ),
    margin=dict(l=52, r=24, t=48, b=48),
)

LEGEND_H = dict(
    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
    bgcolor="rgba(10,14,26,0.9)",
    bordercolor="rgba(255,255,255,0.08)",
    borderwidth=1,
    font=dict(family="'Space Mono', 'Courier New', monospace", size=10),
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Traffic Brain",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Global CSS  ── Premium Smart City Command Center
# ---------------------------------------------------------------------------
st.html("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&family=Inter:wght@300;400;500;600;700;800;900&display=swap');

/* ── Reset & Base ─────────────────────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"] {
    background-color: #0a0e1a !important;
    background-image:
        linear-gradient(rgba(0,212,255,0.022) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,212,255,0.022) 1px, transparent 1px);
    background-size: 48px 48px;
    color: #c8d4f0;
    font-family: 'Inter', sans-serif;
}
[data-testid="stHeader"]           { background: transparent !important; }
[data-testid="stMainBlockContainer"]{ padding-top: 0.5rem; }
[data-testid="stVerticalBlock"]    { gap: 0.75rem; }

/* ── Sidebar ──────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#060910 0%,#0b1020 45%,#080c1a 100%) !important;
    border-right: 1px solid rgba(0,212,255,0.12) !important;
    box-shadow: 4px 0 40px rgba(0,0,0,0.6);
}
[data-testid="stSidebar"] a {
    color: #6b7a9e !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.84rem !important;
    text-decoration: none !important;
    transition: color 0.2s !important;
}
[data-testid="stSidebar"] a:hover { color: #00d4ff !important; }

/* ── Animations ───────────────────────────────────────────────────────── */
@keyframes fadeInUp {
    from { opacity:0; transform:translateY(18px); }
    to   { opacity:1; transform:translateY(0);    }
}
@keyframes logoPulse {
    0%,100% { transform:scale(1) rotate(0deg); filter:drop-shadow(0 0 10px rgba(0,212,255,0.35)); }
    30%     { transform:scale(1.08) rotate(-4deg); filter:drop-shadow(0 0 18px rgba(0,212,255,0.6)); }
    70%     { transform:scale(1.08) rotate(4deg);  filter:drop-shadow(0 0 18px rgba(139,92,246,0.6)); }
}
@keyframes gradientShift {
    0%   { background-position:0% 50%; }
    50%  { background-position:100% 50%; }
    100% { background-position:0% 50%; }
}
@keyframes statusBlink {
    0%,100% { opacity:1; }
    50%      { opacity:0.3; }
}
@keyframes shimmer {
    from { left:-100%; }
    to   { left:200%;  }
}

/* ── KPI Cards ────────────────────────────────────────────────────────── */
.kpi-card {
    position: relative;
    background: rgba(255,255,255,0.03);
    backdrop-filter: blur(24px) saturate(160%);
    -webkit-backdrop-filter: blur(24px) saturate(160%);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 18px;
    padding: 26px 20px 22px;
    text-align: center;
    overflow: hidden;
    transition: transform 0.3s cubic-bezier(0.34,1.56,0.64,1),
                box-shadow 0.3s ease;
    animation: fadeInUp 0.55s ease both;
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: var(--ka, rgba(0,212,255,0.7));
    border-radius: 18px 18px 0 0;
}
.kpi-card::after {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 50%;
    height: 100%;
    background: linear-gradient(90deg,transparent,rgba(255,255,255,0.04),transparent);
    transition: left 0.7s ease;
    pointer-events: none;
}
.kpi-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 20px 60px rgba(0,0,0,0.7),
                0 0 0 1px rgba(255,255,255,0.09),
                0 0 40px var(--ka-glow, rgba(0,212,255,0.08));
}
.kpi-card:hover::after { left: 200%; }

.kpi-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.62rem;
    font-weight: 700;
    color: #3a4a6a;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    margin-bottom: 14px;
}
.kpi-value {
    font-family: 'Space Mono', monospace;
    font-size: 1.95rem;
    font-weight: 700;
    line-height: 1.1;
    letter-spacing: -0.03em;
}
.kpi-delta {
    font-family: 'Inter', sans-serif;
    font-size: 0.76rem;
    font-weight: 500;
    margin-top: 11px;
}
.good  { color: #00d4ff; }
.bad   { color: #ff4757; }
.muted { color: #3a4a6a; }

/* ── Mode Cards ───────────────────────────────────────────────────────── */
.mode-card {
    background: rgba(255,255,255,0.025);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 16px;
    padding: 22px 18px;
    height: 100%;
    transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
    animation: fadeInUp 0.5s ease both;
}
.mode-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 14px 44px rgba(0,0,0,0.6);
    border-color: rgba(255,255,255,0.11);
}
.mode-icon { font-size: 1.65rem; margin-bottom: 11px; display: block; }
.mode-name {
    font-family: 'Space Mono', monospace;
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 8px;
}
.mode-desc {
    font-family: 'Inter', sans-serif;
    font-size: 0.81rem;
    color: #3a4a6a;
    line-height: 1.65;
}
.mode-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-family: 'Space Mono', monospace;
    font-size: 0.58rem;
    font-weight: 700;
    margin-bottom: 10px;
    letter-spacing: 0.08em;
}

/* ── Insight Cards ────────────────────────────────────────────────────── */
.insight-card {
    background: rgba(255,255,255,0.025);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 16px;
    padding: 26px 22px;
    height: 100%;
    transition: transform 0.25s ease;
    animation: fadeInUp 0.65s ease both;
}
.insight-card:hover { transform: translateY(-4px); }
.insight-icon  { font-size: 1.75rem; margin-bottom: 12px; display: block; }
.insight-title {
    font-family: 'Space Mono', monospace;
    font-size: 0.63rem;
    font-weight: 700;
    color: #3a4a6a;
    text-transform: uppercase;
    letter-spacing: 0.13em;
    margin-bottom: 10px;
}
.insight-body {
    font-family: 'Inter', sans-serif;
    font-size: 0.86rem;
    color: #6b7a9e;
    line-height: 1.65;
}
.insight-stat {
    font-family: 'Space Mono', monospace;
    font-size: 1.55rem;
    font-weight: 700;
    margin: 10px 0 6px;
    letter-spacing: -0.02em;
}

/* ── Camera Cards ─────────────────────────────────────────────────────── */
.cam-card {
    background: rgba(139,92,246,0.05);
    border: 1px solid rgba(139,92,246,0.18);
    border-radius: 14px;
    padding: 18px 14px;
    text-align: center;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.cam-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 32px rgba(139,92,246,0.15);
}
.cam-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.6rem;
    color: #3a2a6a;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 10px;
}
.cam-value {
    font-family: 'Space Mono', monospace;
    font-size: 1.75rem;
    font-weight: 700;
    color: #8b5cf6;
}
.cam-sub {
    font-family: 'Inter', sans-serif;
    font-size: 0.72rem;
    color: #3a2a6a;
    margin-top: 6px;
}

/* ── Section Headings ─────────────────────────────────────────────────── */
.sec {
    font-family: 'Space Mono', monospace;
    font-size: 0.72rem;
    font-weight: 700;
    color: #c8d4f0;
    text-transform: uppercase;
    letter-spacing: 0.16em;
    border-left: 3px solid #00d4ff;
    padding: 7px 0 7px 14px;
    margin: 32px 0 20px;
    background: linear-gradient(90deg, rgba(0,212,255,0.07) 0%, transparent 55%);
    border-radius: 0 8px 8px 0;
}
.sec-vision {
    font-family: 'Space Mono', monospace;
    font-size: 0.72rem;
    font-weight: 700;
    color: #c8d4f0;
    text-transform: uppercase;
    letter-spacing: 0.16em;
    border-left: 3px solid #8b5cf6;
    padding: 7px 0 7px 14px;
    margin: 32px 0 20px;
    background: linear-gradient(90deg, rgba(139,92,246,0.07) 0%, transparent 55%);
    border-radius: 0 8px 8px 0;
}

/* ── Emergency Table ──────────────────────────────────────────────────── */
.emg-tbl { width:100%; border-collapse:collapse; font-size:0.83rem; }
.emg-tbl th {
    background: rgba(255,255,255,0.025);
    color: #3a4a6a;
    font-family: 'Space Mono', monospace;
    font-weight: 700;
    font-size: 0.6rem;
    padding: 10px 14px;
    text-align: left;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    border-bottom: 1px solid rgba(255,255,255,0.05);
}
.emg-tbl td {
    padding: 9px 14px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    font-family: 'Inter', sans-serif;
}
.emg-tbl tr:last-child td { border-bottom:none; }
.emg-tbl tr:hover td     { background: rgba(255,255,255,0.02); }

/* ── Badges ───────────────────────────────────────────────────────────── */
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-family: 'Space Mono', monospace;
    font-size: 0.6rem;
    font-weight: 700;
    letter-spacing: 0.06em;
}
.bf { background:rgba(255,149,0,0.1);   color:#ff9500; border:1px solid rgba(255,149,0,0.28); }
.bs { background:rgba(0,212,255,0.1);   color:#00d4ff; border:1px solid rgba(0,212,255,0.28); }
.bv { background:rgba(139,92,246,0.1);  color:#8b5cf6; border:1px solid rgba(139,92,246,0.28); }

/* ── Sidebar text helpers ─────────────────────────────────────────────── */
.sb-title {
    font-family: 'Space Mono', monospace;
    font-size: 0.88rem;
    font-weight: 700;
    color: #c8d4f0;
    margin-bottom: 2px;
}
.sb-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.59rem;
    color: #2a3a5a;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-top: 18px;
    margin-bottom: 5px;
}
.sb-value {
    font-family: 'Inter', sans-serif;
    font-size: 0.83rem;
    color: #6b7a9e;
    margin-bottom: 2px;
}
.sb-divider {
    border: none;
    border-top: 1px solid rgba(255,255,255,0.045);
    margin: 18px 0;
}

/* ── Footer ───────────────────────────────────────────────────────────── */
.footer {
    text-align: center;
    color: #1a2438;
    font-family: 'Inter', sans-serif;
    font-size: 0.73rem;
    padding: 36px 0 18px;
    border-top: 1px solid rgba(255,255,255,0.04);
    margin-top: 48px;
}
.footer strong { color: #2a3a5a; }

/* ── Streamlit widget overrides ───────────────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg,rgba(0,212,255,0.14),rgba(0,212,255,0.06)) !important;
    border: 1px solid rgba(0,212,255,0.35) !important;
    color: #00d4ff !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.1em !important;
    border-radius: 10px !important;
    text-transform: uppercase !important;
    transition: all 0.25s ease !important;
    padding: 10px 20px !important;
}
.stButton > button:hover {
    background: rgba(0,212,255,0.22) !important;
    box-shadow: 0 0 28px rgba(0,212,255,0.22) !important;
    transform: translateY(-2px) !important;
    border-color: rgba(0,212,255,0.6) !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg,rgba(0,212,255,0.2),rgba(139,92,246,0.15)) !important;
    border-color: rgba(0,212,255,0.5) !important;
}
div[data-baseweb="select"] > div {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 10px !important;
    color: #c8d4f0 !important;
    font-family: 'Inter', sans-serif !important;
}
.stCheckbox label { font-family: 'Inter', sans-serif !important; color: #6b7a9e !important; }
.stAlert { border-radius: 12px !important; }
</style>
""")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
@st.cache_data
def load_csv(path: Path) -> dict | None:
    if not path.exists():
        return None
    columns: dict[str, list] = defaultdict(list)
    with open(path, newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            for key, val in row.items():
                try:
                    columns[key].append(float(val))
                except (ValueError, TypeError):
                    columns[key].append(val)
    return dict(columns)


def rolling_mean(values: list[float], window: int) -> list[float]:
    out = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        out.append(statistics.mean(values[start : i + 1]))
    return out


def col(d: dict, key: str) -> list:
    return d.get(key, [])

def safe_mean(lst: list) -> float:
    nums = [v for v in lst if isinstance(v, (int, float))]
    return statistics.mean(nums) if nums else 0.0

def safe_max(lst: list) -> float:
    nums = [v for v in lst if isinstance(v, (int, float))]
    return max(nums) if nums else 0.0

def total_queue(d: dict) -> list[float]:
    return [a + b + c + w for a, b, c, w in zip(
        col(d, "queue_north"), col(d, "queue_south"),
        col(d, "queue_east"),  col(d, "queue_west"),
    )]

def pct_change(new: float, base: float) -> float:
    return (base - new) / max(abs(base), 1e-9) * 100

def delta_label(pct: float, better_is_lower: bool = True) -> tuple[str, str]:
    improved = pct > 0 if better_is_lower else pct < 0
    sym = "▼" if pct > 0 else "▲"
    cls = "good" if improved else "bad"
    return f"{sym} {abs(pct):.1f}% vs fixed", cls

# ---------------------------------------------------------------------------
# ── SIDEBAR
# ---------------------------------------------------------------------------
with st.sidebar:
    st.html("""
    <div style="padding:16px 0 10px 0;">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;">
        <div style="font-size:2rem;animation:logoPulse 5s ease-in-out infinite;">🚦</div>
        <div>
          <div style="font-family:'Space Mono',monospace;font-size:0.82rem;font-weight:700;
                      background:linear-gradient(130deg,#00d4ff,#8b5cf6);
                      -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                      background-clip:text;letter-spacing:0.04em;">
            AI TRAFFIC BRAIN
          </div>
          <div style="font-family:'Inter',sans-serif;font-size:0.67rem;color:#2a3a5a;
                      margin-top:2px;letter-spacing:0.05em;">
            Smart City Command Center
          </div>
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:8px;
                  background:rgba(16,185,129,0.07);
                  border:1px solid rgba(16,185,129,0.18);
                  border-radius:8px;padding:6px 12px;">
        <div style="width:7px;height:7px;border-radius:50%;background:#10b981;
                    flex-shrink:0;animation:statusBlink 2.5s ease infinite;"></div>
        <span style="font-family:'Space Mono',monospace;font-size:0.6rem;color:#10b981;
                     letter-spacing:0.1em;">SYSTEM ONLINE</span>
      </div>
    </div>
    """)

    st.html('<hr class="sb-divider">')

    st.html("""
    <div class="sb-label" style="margin-top:0;">Project</div>
    <div class="sb-value">ACHAAR Mohammed Amine</div>
    <div class="sb-value">ZAKANE Mohamed</div>

    <div class="sb-label">Supervisor</div>
    <div class="sb-value">Dr. EN-NOUAARY ABDESLAM</div>

    <div class="sb-label">Institution</div>
    <div class="sb-value">Institut National des Postes et Télécommunications</div>
    <div style="font-family:'Space Mono',monospace;font-size:0.7rem;color:#00d4ff;
                font-weight:700;margin-top:4px;letter-spacing:0.06em;">
      INPT · RABAT, MOROCCO
    </div>
    """)

    st.html('<hr class="sb-divider">')

    st.html('<div class="sb-label" style="margin-top:0;">Navigation</div>')
    st.page_link("app.py",            label="📊  Performance Dashboard")
    st.page_link("pages/live_map.py", label="🎬  Live Map Demo")

    st.html('<hr class="sb-divider">')

    st.html('<div class="sb-label" style="margin-top:0;">Run Simulation</div>')

    _MODE_LABELS = {
        "fixed":  "Fixed cycle (30 s / 5 s)",
        "smart":  "Smart adaptive (demand-based)",
        "vision": "Vision — Camera AI",
        "rl":     "Q-Learning (trained AI)",
    }
    sim_mode = st.selectbox(
        "Controller mode",
        options=list(_MODE_LABELS.keys()),
        format_func=lambda x: _MODE_LABELS[x],
        label_visibility="collapsed",
    )

    gui_flag = st.checkbox("Open SUMO GUI", value=False)
    run_btn  = st.button("▶  Run Simulation", use_container_width=True, type="primary")

    if run_btn:
        cmd = [sys.executable, str(MAIN_PY), "--mode", sim_mode]
        if gui_flag:
            cmd.append("--gui")
        status_box = st.empty()
        with st.spinner(f"Running **{sim_mode}** simulation…"):
            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, cwd=str(ROOT),
                )
                if result.returncode == 0:
                    status_box.success(f"✅ {sim_mode.capitalize()} simulation complete!")
                    load_csv.clear()
                    st.rerun()
                else:
                    status_box.error("Simulation failed. See details below.")
                    st.code(result.stderr[-2000:], language="bash")
            except FileNotFoundError:
                st.error("`main.py` not found. Check your project root path.")

    st.html('<hr class="sb-divider">')
    st.html(
        '<div style="font-family:\'Inter\',sans-serif;font-size:0.68rem;color:#1a2438;'
        'text-align:center;letter-spacing:0.04em;">Academic Project · 2025–2026</div>',
    )

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
fixed  = load_csv(FIXED_CSV)
smart  = load_csv(SMART_CSV)
vision = load_csv(VISION_CSV)

both          = fixed is not None and smart is not None
vision_avail  = vision is not None

if not vision_avail:
    st.warning(
        "**Vision data not found** (`data/results_vision.csv`). "
        "Camera Intelligence sections will be unavailable. "
        "Select **Vision — Camera AI** in the sidebar and click **Run Simulation** to generate it."
    )

WINDOW = 30

# ---------------------------------------------------------------------------
# ── PAGE HEADER
# ---------------------------------------------------------------------------
st.html("""
<div style="padding:10px 0 28px 0;position:relative;overflow:hidden;">

  <!-- Decorative corner glow -->
  <div style="position:absolute;top:-20px;right:-20px;width:280px;height:160px;
              background:radial-gradient(ellipse at top right,
                rgba(0,212,255,0.08) 0%,rgba(139,92,246,0.05) 40%,transparent 70%);
              pointer-events:none;border-radius:0 0 0 120px;"></div>

  <div style="display:flex;align-items:center;gap:20px;flex-wrap:wrap;">

    <!-- Logo -->
    <div style="font-size:2.6rem;animation:logoPulse 5s ease-in-out infinite;flex-shrink:0;">
      🚦
    </div>

    <!-- Title block -->
    <div style="flex:1;min-width:280px;">
      <h1 style="font-family:'Space Mono',monospace;font-size:1.9rem;font-weight:700;
                 margin:0 0 6px 0;line-height:1.1;
                 background:linear-gradient(130deg,#00d4ff 0%,#8b5cf6 55%,#00d4ff 100%);
                 background-size:200% auto;
                 -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                 background-clip:text;animation:gradientShift 5s ease infinite;">
        AI Traffic Brain
      </h1>
      <p style="font-family:'Inter',sans-serif;color:#2a3a5a;margin:0;
                font-size:0.82rem;letter-spacing:0.07em;font-weight:500;">
        SMART CITY COMMAND CENTER &nbsp;·&nbsp; FIXED · SMART · VISION · Q-LEARNING
        &nbsp;·&nbsp; SUMO SIMULATION
      </p>
    </div>

    <!-- INPT Badge -->
    <div style="flex-shrink:0;background:rgba(0,212,255,0.06);
                border:1px solid rgba(0,212,255,0.18);border-radius:12px;
                padding:10px 18px;text-align:center;">
      <div style="font-family:'Space Mono',monospace;font-size:1.15rem;font-weight:700;
                  color:#00d4ff;letter-spacing:0.12em;">INPT</div>
      <div style="font-family:'Inter',sans-serif;font-size:0.6rem;color:#2a3a5a;
                  letter-spacing:0.1em;text-transform:uppercase;margin-top:2px;">
        Rabat · Morocco
      </div>
    </div>

  </div>
</div>
""")

# ---------------------------------------------------------------------------
# ── SECTION 0 — Controller mode explanations
# ---------------------------------------------------------------------------
st.html('<div class="sec">Controller Modes</div>')

mc1, mc2, mc3, mc4 = st.columns(4)

def mode_card(widget, icon, name, badge_color, badge_text, description):
    widget.html(
        f"""<div class="mode-card"
                  style="border-top:2px solid {badge_color}40;
                         box-shadow:inset 0 1px 0 {badge_color}20;">
              <span class="mode-icon">{icon}</span>
              <div>
                <span class="mode-badge"
                      style="background:{badge_color}14;color:{badge_color};
                             border:1px solid {badge_color}35;">
                  {badge_text}
                </span>
              </div>
              <div class="mode-name" style="color:{badge_color};">{name}</div>
              <div class="mode-desc">{description}</div>
            </div>"""
    )

mode_card(mc1, "⏱️", "Fixed Cycle",
    C_FIXED, "BASELINE",
    "Runs a rigid 30 s green / 5 s yellow cycle at all 3 intersections "
    "simultaneously. No awareness of traffic demand. Simple, predictable, "
    "but inefficient during uneven load or peak hours.")

mode_card(mc2, "🧠", "Smart Adaptive",
    C_SMART, "PRESSURE-BASED",
    "Measures per-intersection pressure (vehicle count + waiting time) every "
    "second. Switches green to the most congested axis when pressure ratio "
    "exceeds 1.5×. Adds green-wave coordination between intersections.")

mode_card(mc3, "📷", "Vision (Camera AI)",
    C_VISION, "CAMERA-BASED",
    "Simulates a YOLO-style overhead camera at each intersection. Detects "
    "vehicle types, emergency vehicles (confirmed over 3 frames), and night "
    "mode. Overrides Smart controller decisions based on camera intelligence.")

mode_card(mc4, "🤖", "Q-Learning (RL)",
    C_RL, "REINFORCEMENT LEARNING",
    "Tabular Q-learning agent trained over 50+ simulation episodes. State "
    "encodes binned vehicle count and waiting time per axis. Reward is "
    "negative total waiting time with +50 bonus for clearing emergencies.")

st.html("<br>")

# ---------------------------------------------------------------------------
# Guard — need at least Fixed + Smart to proceed
# ---------------------------------------------------------------------------
if not both:
    missing = []
    if fixed is None: missing.append("`data/results_fixed.csv`")
    if smart is None: missing.append("`data/results_smart.csv`")
    st.warning(
        f"**Missing result files:** {', '.join(missing)}. "
        "Use the **Run Simulation** panel in the sidebar to generate them."
    )
    st.stop()

# ---------------------------------------------------------------------------
# Pre-compute KPIs
# ---------------------------------------------------------------------------
avg_wait_f = safe_mean(col(fixed,  "total_waiting_time"))
avg_wait_s = safe_mean(col(smart,  "total_waiting_time"))
avg_wait_v = safe_mean(col(vision, "total_waiting_time")) if vision_avail else None

pct_s = pct_change(avg_wait_s, avg_wait_f)
pct_v = pct_change(avg_wait_v, avg_wait_f) if avg_wait_v is not None else None

peak_q_f = safe_max(total_queue(fixed))
peak_q_s = safe_max(total_queue(smart))
peak_q_v = safe_max(total_queue(vision)) if vision_avail else None

emg_steps_f = sum(1 for v in col(fixed,  "emergency_count") if isinstance(v, (int,float)) and v > 0)
emg_steps_s = sum(1 for v in col(smart,  "emergency_count") if isinstance(v, (int,float)) and v > 0)
emg_steps_v = sum(1 for v in col(vision, "emergency_count") if isinstance(v, (int,float)) and v > 0) if vision_avail else None

# ---------------------------------------------------------------------------
# ── SECTION 1 — KPI cards
# ---------------------------------------------------------------------------
st.html('<div class="sec">Key Performance Indicators</div>')

k1, k2, k3, k4 = st.columns(4)

def kpi_card(widget, label, value, delta_html, delta_cls, accent=C_TEXT):
    glow = accent.replace("#", "")
    r = int(glow[0:2], 16) if len(glow) >= 6 else 0
    g = int(glow[2:4], 16) if len(glow) >= 6 else 212
    b = int(glow[4:6], 16) if len(glow) >= 6 else 255
    widget.html(
        f"""<div class="kpi-card"
                  style="--ka:{accent}aa;--ka-glow:rgba({r},{g},{b},0.10);">
              <div class="kpi-label">{label}</div>
              <div class="kpi-value" style="color:{accent};">{value}</div>
              <div class="kpi-delta {delta_cls}">{delta_html}</div>
            </div>"""
    )

kpi_card(k1,
    "Avg Waiting — Fixed",
    f"{avg_wait_f:,.1f} s",
    f'<span style="color:{C_FIXED};font-family:\'Space Mono\',monospace;">●</span>'
    f'&nbsp; baseline reference',
    "muted", C_FIXED,
)

s_lbl, s_cls = delta_label(pct_s)
kpi_card(k2,
    "Avg Waiting — Smart",
    f"{avg_wait_s:,.1f} s",
    s_lbl, s_cls, C_SMART,
)

if vision_avail and pct_v is not None:
    v_lbl, v_cls = delta_label(pct_v)
    kpi_card(k3,
        "Avg Waiting — Vision",
        f"{avg_wait_v:,.1f} s",
        v_lbl, v_cls, C_VISION,
    )
else:
    kpi_card(k3,
        "Avg Waiting — Vision",
        "—",
        "Run Vision simulation to compare",
        "muted", C_VISION,
    )

candidates = [("Smart", avg_wait_s, pct_s, C_SMART)]
if vision_avail and pct_v is not None:
    candidates.append(("Vision", avg_wait_v, pct_v, C_VISION))
best_name, best_wait, best_pct, best_col = max(candidates, key=lambda x: x[2])

kpi_card(k4,
    "Best Controller",
    best_name,
    f"▼ {best_pct:.1f}% less waiting vs Fixed",
    "good", best_col,
)

st.html("<br>")

# ---------------------------------------------------------------------------
# ── SECTION 2 — Summary Insights
# ---------------------------------------------------------------------------
st.html('<div class="sec">Summary Insights</div>')

i1, i2, i3 = st.columns(3)

def insight_card(widget, icon, title, stat, stat_color, body):
    widget.html(
        f"""<div class="insight-card"
                  style="border-top:2px solid {stat_color}35;
                         box-shadow:inset 0 1px 0 {stat_color}18;">
              <span class="insight-icon">{icon}</span>
              <div class="insight-title">{title}</div>
              <div class="insight-stat" style="color:{stat_color};">{stat}</div>
              <div class="insight-body">{body}</div>
            </div>"""
    )

if vision_avail and pct_v is not None and pct_v > pct_s:
    best_insight_name  = "Vision"
    best_insight_wait  = avg_wait_v
    best_insight_color = C_VISION
    best_insight_pct   = pct_v
else:
    best_insight_name  = "Smart"
    best_insight_wait  = avg_wait_s
    best_insight_color = C_SMART
    best_insight_pct   = pct_s

insight_card(
    i1, "⏱️", "Waiting Time Reduction",
    f"{best_insight_pct:.1f}% less waiting",
    best_insight_color,
    f"The {best_insight_name} controller cuts average waiting time from "
    f"<strong style='color:{C_TEXT};'>{avg_wait_f:.1f}s</strong> to "
    f"<strong style='color:{best_insight_color};'>{best_insight_wait:.1f}s</strong>. "
    f"Drivers spend significantly less time at red lights because the system "
    f"reads live traffic demand and adapts the green phase in real time."
)

q_diff = int(peak_q_f - (peak_q_v if vision_avail and peak_q_v else peak_q_s))
q_pct  = abs(pct_change(float(peak_q_f - q_diff), peak_q_f))
insight_card(
    i2, "🚗", "Queue Length Control",
    f"{q_pct:.1f}% shorter queues",
    C_SMART if q_diff >= 0 else C_WARN,
    f"Peak queue drops from <strong style='color:{C_TEXT};'>{int(peak_q_f)}</strong> to "
    f"<strong style='color:{C_SMART};'>{int(peak_q_f - q_diff)}</strong> vehicles across all approaches. "
    f"Shorter queues reduce road spillback, cut fuel consumption, "
    f"and lower emissions at all three intersections."
)

emg_note = emg_steps_v if vision_avail and emg_steps_v is not None else emg_steps_s
insight_card(
    i3, "🚨", "Emergency Vehicle Handling",
    f"{emg_note} active steps",
    C_WARN,
    f"Across <strong style='color:{C_TEXT};'>{emg_note}</strong> simulation steps an emergency vehicle "
    f"was present. Smart and Vision controllers detect this in real time and "
    f"trigger green-axis priority. The fixed controller cannot react — "
    f"emergency vehicles face the same rigid 30 s cycle as regular traffic."
)

st.html("<br>")

# ---------------------------------------------------------------------------
# ── SECTION 3 — Waiting time line chart
# ---------------------------------------------------------------------------
st.html('<div class="sec">Total Waiting Time Over Simulation</div>')

t_f  = col(fixed, "sim_time")
t_s  = col(smart, "sim_time")
wt_f = rolling_mean(col(fixed, "total_waiting_time"), WINDOW)
wt_s = rolling_mean(col(smart, "total_waiting_time"), WINDOW)

fig_line = go.Figure()
fig_line.add_trace(go.Scatter(
    x=t_f, y=wt_f,
    name="Fixed",
    line=dict(color=C_FIXED, width=2.5),
    hovertemplate="t=%{x:.0f}s<br>wait=%{y:.1f}s<extra>Fixed</extra>",
))
fig_line.add_trace(go.Scatter(
    x=t_s, y=wt_s,
    name="Smart",
    line=dict(color=C_SMART, width=2.5),
    hovertemplate="t=%{x:.0f}s<br>wait=%{y:.1f}s<extra>Smart</extra>",
))
if vision_avail:
    t_v  = col(vision, "sim_time")
    wt_v = rolling_mean(col(vision, "total_waiting_time"), WINDOW)
    fig_line.add_trace(go.Scatter(
        x=t_v, y=wt_v,
        name="Vision",
        line=dict(color=C_VISION, width=2.5, dash="dot"),
        hovertemplate="t=%{x:.0f}s<br>wait=%{y:.1f}s<extra>Vision</extra>",
    ))
fig_line.update_layout(**{
    **PLOTLY_BASE,
    "height": 340,
    "xaxis_title": "Simulation time (s)",
    "yaxis_title": "Total waiting time (s)",
    "legend": LEGEND_H,
})
st.plotly_chart(fig_line, use_container_width=True)

# ---------------------------------------------------------------------------
# ── SECTION 4 — Per-intersection waiting time
# ---------------------------------------------------------------------------
st.html('<div class="sec">Per-Intersection Waiting Time</div>')

INT_COLS = [("int_A", "intA_wait", C_FIXED),
            ("int_B", "intB_wait", C_SMART),
            ("int_C", "intC_wait", C_RL)]

fig_int = go.Figure()
for ds, ds_name, ds_color in [(fixed, "Fixed", C_FIXED),
                               (smart, "Smart", C_SMART)] + (
                              [(vision, "Vision", C_VISION)] if vision_avail else []):
    for int_id, int_col_key, int_color in INT_COLS:
        raw = col(ds, int_col_key)
        if not raw:
            continue
        smoothed = rolling_mean(raw, WINDOW)
        t_ds = col(ds, "sim_time")
        fig_int.add_trace(go.Scatter(
            x=t_ds, y=smoothed,
            name=f"{ds_name} – {int_id}",
            line=dict(
                color=int_color, width=1.8,
                dash="solid" if ds_name == "Fixed"
                     else ("dash" if ds_name == "Smart" else "dot"),
            ),
            hovertemplate=f"{ds_name} {int_id}: %{{y:.1f}}s<extra></extra>",
        ))
fig_int.update_layout(**{
    **PLOTLY_BASE,
    "height": 300,
    "xaxis_title": "Simulation time (s)",
    "yaxis_title": "Waiting time (s)",
    "legend": LEGEND_H,
})
st.plotly_chart(fig_int, use_container_width=True)

# ---------------------------------------------------------------------------
# ── SECTION 5 — Peak queue bar chart
# ---------------------------------------------------------------------------
st.html('<div class="sec">Peak Queue Length by Approach</div>')

approaches  = ["North", "South", "East", "West"]
q_cols      = ["queue_north", "queue_south", "queue_east", "queue_west"]
peak_f_bars = [int(safe_max(col(fixed, c))) for c in q_cols]
peak_s_bars = [int(safe_max(col(smart, c))) for c in q_cols]

fig_bar = go.Figure()
fig_bar.add_trace(go.Bar(
    name="Fixed", x=approaches, y=peak_f_bars,
    marker_color=C_FIXED,
    marker_line=dict(width=0),
    text=peak_f_bars, textposition="outside",
    textfont=dict(color=C_TEXT, size=12, family="'Space Mono', monospace"),
))
fig_bar.add_trace(go.Bar(
    name="Smart", x=approaches, y=peak_s_bars,
    marker_color=C_SMART,
    marker_line=dict(width=0),
    text=peak_s_bars, textposition="outside",
    textfont=dict(color=C_TEXT, size=12, family="'Space Mono', monospace"),
))
if vision_avail:
    peak_v_bars = [int(safe_max(col(vision, c))) for c in q_cols]
    fig_bar.add_trace(go.Bar(
        name="Vision", x=approaches, y=peak_v_bars,
        marker_color=C_VISION,
        marker_line=dict(width=0),
        text=peak_v_bars, textposition="outside",
        textfont=dict(color=C_TEXT, size=12, family="'Space Mono', monospace"),
    ))
fig_bar.update_layout(**{
    **PLOTLY_BASE,
    "height": 320,
    "barmode": "group",
    "bargap": 0.22,
    "bargroupgap": 0.06,
    "xaxis_title": "Approach (int_B)",
    "yaxis_title": "Vehicles queued (peak)",
    "legend": LEGEND_H,
})
st.plotly_chart(fig_bar, use_container_width=True)

# ---------------------------------------------------------------------------
# ── SECTION 6 — Per-approach area charts
# ---------------------------------------------------------------------------
st.html('<div class="sec">Per-Approach Waiting Time Breakdown</div>')

APPROACH_WAIT = [
    ("North", "north_wait"),
    ("South", "south_wait"),
    ("East",  "east_wait"),
    ("West",  "west_wait"),
]

def make_area(d: dict, title: str) -> go.Figure:
    fig = go.Figure()
    t = col(d, "sim_time")
    for i, (label, key) in enumerate(APPROACH_WAIT):
        smoothed = rolling_mean(col(d, key), WINDOW)
        fig.add_trace(go.Scatter(
            x=t, y=smoothed,
            name=label,
            stackgroup="one",
            line=dict(width=0.8, color=AREA_COLOURS[i]),
            fillcolor=AREA_FILL_COLOURS[i],
            hovertemplate=f"{label}: %{{y:.1f}}s<extra></extra>",
        ))
    fig.update_layout(**{
        **PLOTLY_BASE,
        "height": 270,
        "title": dict(text=title, font=dict(
            size=12, color=C_TEXT, family="'Space Mono', monospace")),
        "xaxis_title": "Simulation time (s)",
        "yaxis_title": "Waiting time (s)",
        "legend": LEGEND_H,
        "margin": dict(l=48, r=16, t=54, b=44),
    })
    return fig

if vision_avail:
    a1, a2, a3 = st.columns(3)
    with a1: st.plotly_chart(make_area(fixed,  "Fixed"),  use_container_width=True)
    with a2: st.plotly_chart(make_area(smart,  "Smart"),  use_container_width=True)
    with a3: st.plotly_chart(make_area(vision, "Vision"), use_container_width=True)
else:
    a1, a2 = st.columns(2)
    with a1: st.plotly_chart(make_area(fixed, "Fixed"), use_container_width=True)
    with a2: st.plotly_chart(make_area(smart, "Smart"), use_container_width=True)

# ---------------------------------------------------------------------------
# ── SECTION 7 — Camera Intelligence
# ---------------------------------------------------------------------------
st.html('<div class="sec-vision">📷 Camera Intelligence Report</div>')

if not vision_avail:
    st.info(
        "Camera intelligence data is not yet available. "
        "Run a **Vision** simulation from the sidebar to populate this section."
    )
else:
    reason_col = col(vision, "controller_reason")

    override_counts = {}
    for tl in ("int_A", "int_B", "int_C"):
        override_counts[tl] = sum(
            1 for r in reason_col
            if isinstance(r, str) and "camera_emg" in r and tl in r
        )
    total_override_steps = sum(
        1 for r in reason_col
        if isinstance(r, str) and "camera_emg" in r
    )

    night_steps = sum(
        1 for v in col(vision, "total_vehicles")
        if isinstance(v, (int, float)) and v < 5
    )

    intA_v = col(vision, "intA_wait")
    intB_v = col(vision, "intB_wait")
    intC_v = col(vision, "intC_wait")
    congestion_steps = sum(
        1 for a, b, c in zip(intA_v, intB_v, intC_v)
        if isinstance(a, (int, float)) and isinstance(b, (int, float))
           and isinstance(c, (int, float)) and a + b + c > 500
    )

    cam_left, cam_right = st.columns([2, 3])

    with cam_left:
        st.html("""
        <div style="font-family:'Space Mono',monospace;font-size:0.62rem;color:#3a2a6a;
                    text-transform:uppercase;letter-spacing:0.12em;margin-bottom:14px;">
          Camera Event Summary
        </div>""")

        cm1, cm2, cm3 = st.columns(3)
        for widget, label, value, sub in [
            (cm1, "Override Steps",   total_override_steps, "emergency holds"),
            (cm2, "Night Mode Steps", night_steps,          "&lt;5 vehicles"),
            (cm3, "Congestion Steps", congestion_steps,     "wait &gt;500 s"),
        ]:
            widget.html(
                f"""<div class="cam-card">
                      <div class="cam-label">{label}</div>
                      <div class="cam-value">{value:,}</div>
                      <div class="cam-sub">{sub}</div>
                    </div>"""
            )

        st.html("<br>")
        reason_counts: dict[str, int] = {}
        for r in reason_col:
            if not isinstance(r, str):
                continue
            key = r.split("(")[0]
            reason_counts[key] = reason_counts.get(key, 0) + 1

        sorted_reasons = sorted(reason_counts.items(), key=lambda x: -x[1])[:8]

        html = """<table class="emg-tbl">
          <thead><tr>
            <th>Control Reason</th>
            <th style="text-align:right;">Steps</th>
          </tr></thead><tbody>"""
        for reason, count in sorted_reasons:
            is_cam = "camera" in reason
            color  = C_VISION if is_cam else C_SUBTEXT
            html += (
                f"<tr><td style='color:{color};"
                f"font-family:\"Space Mono\",monospace;font-size:0.76rem;'>"
                f"{reason}</td>"
                f"<td style='text-align:right;font-weight:700;"
                f"font-family:\"Space Mono\",monospace;color:{C_TEXT};'>{count:,}</td></tr>"
            )
        html += "</tbody></table>"
        st.html(html)

    with cam_right:
        fig_ovr = go.Figure()
        tl_labels = ["int_A (West)", "int_B (Centre)", "int_C (East)"]
        ovr_vals  = [override_counts.get(tl, 0) for tl in ("int_A", "int_B", "int_C")]
        bar_colors = [
            C_VISION if v > 0 else "rgba(255,255,255,0.06)"
            for v in ovr_vals
        ]
        fig_ovr.add_trace(go.Bar(
            x=tl_labels,
            y=ovr_vals,
            marker_color=bar_colors,
            marker_line=dict(width=0),
            text=ovr_vals,
            textposition="outside",
            textfont=dict(color=C_TEXT, size=13, family="'Space Mono', monospace"),
            hovertemplate="%{x}<br>Override steps: %{y}<extra></extra>",
        ))
        fig_ovr.update_layout(**{
            **PLOTLY_BASE,
            "height": 280,
            "title": dict(
                text="Emergency Override Steps per Intersection",
                font=dict(size=12, color=C_TEXT, family="'Space Mono', monospace"),
            ),
            "xaxis_title": "Intersection",
            "yaxis_title": "Steps in camera override",
            "showlegend": False,
        })
        st.plotly_chart(fig_ovr, use_container_width=True)

        t_vis   = col(vision, "sim_time")
        veh_vis = col(vision, "total_vehicles")
        wt_vis  = [a + b + c for a, b, c in zip(intA_v, intB_v, intC_v)]

        if t_vis and veh_vis:
            fig_cam = go.Figure()
            fig_cam.add_trace(go.Scatter(
                x=t_vis,
                y=rolling_mean([v if isinstance(v, (int,float)) else 0 for v in veh_vis], WINDOW),
                name="Total vehicles",
                line=dict(color=C_VISION, width=2),
                hovertemplate="t=%{x:.0f}s<br>vehicles=%{y:.1f}<extra></extra>",
            ))
            fig_cam.add_trace(go.Scatter(
                x=t_vis,
                y=rolling_mean([w if isinstance(w, (int,float)) else 0 for w in wt_vis], WINDOW),
                name="Total wait (3 nodes)",
                line=dict(color=C_WARN, width=2, dash="dash"),
                yaxis="y2",
                hovertemplate="t=%{x:.0f}s<br>wait=%{y:.1f}s<extra></extra>",
            ))
            fig_cam.update_layout(**{
                **PLOTLY_BASE,
                "height": 230,
                "title": dict(
                    text="Vehicle Density & Waiting (Vision)",
                    font=dict(size=11, color=C_TEXT, family="'Space Mono', monospace"),
                ),
                "xaxis_title": "Simulation time (s)",
                "yaxis":  {**PLOTLY_BASE["yaxis"], "title": "Vehicles"},
                "yaxis2": dict(
                    overlaying="y", side="right",
                    showgrid=False,
                    zerolinecolor="rgba(255,255,255,0.06)",
                    title=dict(text="Waiting (s)",
                               font=dict(color=C_WARN, family="'Space Mono', monospace")),
                    tickfont=dict(color=C_WARN, family="'Space Mono', monospace"),
                ),
                "legend": LEGEND_H,
            })
            st.plotly_chart(fig_cam, use_container_width=True)

st.html("<br>")

# ---------------------------------------------------------------------------
# ── SECTION 8 — Emergency vehicle activity
# ---------------------------------------------------------------------------
st.html('<div class="sec">Emergency Vehicle Activity</div>')

emg_left, emg_right = st.columns([3, 2])

with emg_left:
    fig_emg = go.Figure()
    datasets = [(fixed, "Fixed", C_FIXED), (smart, "Smart", C_SMART)]
    if vision_avail:
        datasets.append((vision, "Vision", C_VISION))

    for d, name, color in datasets:
        t_all   = col(d, "sim_time")
        emg_all = col(d, "emergency_count")
        t_emg   = [t for t, v in zip(t_all, emg_all) if isinstance(v, (int,float)) and v > 0]
        v_emg   = [v for v in emg_all if isinstance(v, (int,float)) and v > 0]
        fig_emg.add_trace(go.Scatter(
            x=t_emg, y=v_emg,
            mode="markers",
            name=name,
            marker=dict(color=color, size=10, symbol="diamond",
                        line=dict(color=C_WARN, width=1.5)),
            hovertemplate="t=%{x:.0f}s  |  %{y:.0f} lane(s)<extra>" + name + "</extra>",
        ))
    fig_emg.update_layout(**{
        **PLOTLY_BASE,
        "height": 260,
        "xaxis_title": "Simulation time (s)",
        "yaxis_title": "Lanes with emergency vehicle",
        "yaxis": {**PLOTLY_BASE["yaxis"], "dtick": 1},
        "legend": LEGEND_H,
    })
    st.plotly_chart(fig_emg, use_container_width=True)

with emg_right:
    def _first(times, vals):
        return next((int(t) for t, v in zip(times, vals)
                     if isinstance(v, (int,float)) and v > 0), None)
    def _last(times, vals):
        return next((int(t) for t, v in zip(reversed(list(times)),
                                             reversed(list(vals)))
                     if isinstance(v, (int,float)) and v > 0), None)

    emg_f = col(fixed, "emergency_count")
    emg_s = col(smart, "emergency_count")
    t_f2  = col(fixed, "sim_time")
    t_s2  = col(smart, "sim_time")

    rows_emg = [
        ("Total emergency steps",
         str(emg_steps_f), str(emg_steps_s),
         str(emg_steps_v) if vision_avail else "—"),
        ("Peak simultaneous lanes",
         str(int(safe_max(emg_f))), str(int(safe_max(emg_s))),
         str(int(safe_max(col(vision, "emergency_count")))) if vision_avail else "—"),
        ("First emergency at (s)",
         str(_first(t_f2, emg_f) or "—"), str(_first(t_s2, emg_s) or "—"),
         str(_first(col(vision,"sim_time"), col(vision,"emergency_count")) or "—")
         if vision_avail else "—"),
        ("Last emergency at (s)",
         str(_last(t_f2, emg_f) or "—"), str(_last(t_s2, emg_s) or "—"),
         str(_last(col(vision,"sim_time"), col(vision,"emergency_count")) or "—")
         if vision_avail else "—"),
    ]

    head_vision = f'<th><span class="badge bv">Vision</span></th>' if vision_avail else ""
    html = f"""<table class="emg-tbl">
      <thead><tr>
        <th>Metric</th>
        <th><span class="badge bf">Fixed</span></th>
        <th><span class="badge bs">Smart</span></th>
        {head_vision}
      </tr></thead><tbody>"""
    for row in rows_emg:
        metric = row[0]
        fv, sv = row[1], row[2]
        vv     = row[3] if vision_avail else None
        vis_td = f"<td style='color:{C_VISION};font-weight:700;font-family:\"Space Mono\",monospace;'>{vv}</td>" if vv is not None else ""
        html += (f"<tr><td style='color:#6b7a9e;'>{metric}</td>"
                 f"<td style='color:{C_FIXED};font-weight:700;font-family:\"Space Mono\",monospace;'>{fv}</td>"
                 f"<td style='color:{C_SMART};font-weight:700;font-family:\"Space Mono\",monospace;'>{sv}</td>"
                 f"{vis_td}</tr>")
    html += "</tbody></table>"
    st.html(html)

# ---------------------------------------------------------------------------
# ── FOOTER
# ---------------------------------------------------------------------------
csvs_note = (
    "<code style='color:#2a3a5a;font-family:\"Space Mono\",monospace;'>results_fixed.csv</code>, "
    "<code style='color:#2a3a5a;font-family:\"Space Mono\",monospace;'>results_smart.csv</code>"
    + (", <code style='color:#2a3a5a;font-family:\"Space Mono\",monospace;'>results_vision.csv</code>"
       if vision_avail else "")
)
st.html(f"""
<div class="footer">
  <div style="font-family:'Space Mono',monospace;font-size:0.9rem;font-weight:700;
              color:#1e2a3a;letter-spacing:0.14em;margin-bottom:8px;">
    INPT &nbsp;·&nbsp; INSTITUT NATIONAL DES POSTES ET TÉLÉCOMMUNICATIONS
  </div>
  <div style="margin-bottom:5px;font-family:'Inter',sans-serif;color:#1a2438;">
    <strong style="color:#2a3a5a;">AI Traffic Brain</strong> &nbsp;—&nbsp;
    Intelligent Adaptive Traffic Light Control Using AI
  </div>
  <div style="font-family:'Inter',sans-serif;color:#1a2438;">
    ACHAAR Mohammed Amine &nbsp;&amp;&nbsp; ZAKANE Mohamed &nbsp;·&nbsp;
    Supervised by Dr. EN-NOUAARY ABDESLAM
  </div>
  <div style="margin-top:10px;font-size:0.68rem;color:#111826;font-family:'Space Mono',monospace;">
    DATA: {csvs_note}
    &nbsp;·&nbsp; SUMO 1.26 &nbsp;·&nbsp; 2025–2026
  </div>
</div>
""")
