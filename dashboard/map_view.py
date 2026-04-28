"""
AI-Traffic-Brain — Smart City Map View
Interactive Folium map of Casablanca showing live traffic state at the
3 simulated intersections on Boulevard Mohammed V.

Can be run standalone:
    streamlit run dashboard/map_view.py

Or accessed as a page from the main dashboard:
    streamlit run dashboard/app.py   (pages/map_view.py re-exports this file)
"""

import csv
import time
from collections import defaultdict
from pathlib import Path

import folium
from folium.plugins import HeatMap
import streamlit as st
from streamlit_folium import st_folium

# ---------------------------------------------------------------------------
# Project root — works regardless of where this file lives in the tree
# ---------------------------------------------------------------------------
def _find_root() -> Path:
    here = Path(__file__).resolve().parent
    for candidate in [here, here.parent, here.parent.parent]:
        if (candidate / "data").is_dir():
            return candidate
    return here.parent

ROOT     = _find_root()
DATA_DIR = ROOT / "data"

FIXED_CSV  = DATA_DIR / "results_fixed.csv"
SMART_CSV  = DATA_DIR / "results_smart.csv"
VISION_CSV = DATA_DIR / "results_vision.csv"

CSV_MAP = {
    "smart":  SMART_CSV,
    "vision": VISION_CSV,
    "fixed":  FIXED_CSV,
}

# ---------------------------------------------------------------------------
# Intersection config — realistic positions on Boulevard Mohammed V
# ---------------------------------------------------------------------------
INTERSECTIONS: list[dict] = [
    {
        "id":       "int_A",
        "short":    "int_A (West)",
        "name":     "int_A — Blvd Mohammed V / Rue Galliéni",
        "lat":      33.5927,
        "lon":     -7.6115,
        "type":     "T-junction",
        "wait_col": "intA_wait",
    },
    {
        "id":       "int_B",
        "short":    "int_B (Centre)",
        "name":     "int_B — Blvd Mohammed V / Rue Moulay Abdallah",
        "lat":      33.5913,
        "lon":     -7.6048,
        "type":     "4-way intersection",
        "wait_col": "intB_wait",
    },
    {
        "id":       "int_C",
        "short":    "int_C (East)",
        "name":     "int_C — Blvd Mohammed V / Blvd Rachidi",
        "lat":      33.5899,
        "lon":     -7.5981,
        "type":     "T-junction",
        "wait_col": "intC_wait",
    },
]

# Waiting-time colour thresholds (seconds)
THRESH_GREEN  = 30.0   # < 30 s  → green  (flowing)
THRESH_ORANGE = 70.0   # < 70 s  → orange (moderate);  ≥ 70 s → red (congested)

_BADGE_HEX = {"green": "#16a34a", "orange": "#ea580c", "red": "#dc2626"}
_STATUS_LBL = {"green": "Flowing", "orange": "Moderate", "red": "Congested"}

# ---------------------------------------------------------------------------
# Page config  (must be first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Traffic Brain — City Map",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"] {
    background-color: #0E1117; color: #E0E0E0;
}
[data-testid="stHeader"]  { background: transparent; }
[data-testid="stSidebar"] { background-color: #12151E; border-right: 1px solid #2A3045; }

.stat-card {
    background: #1A1F2E; border: 1px solid #2A3045;
    border-radius: 10px; padding: 14px 16px; margin-bottom: 10px;
}
.stat-label {
    font-size: 0.72rem; color: #9AA0AF;
    text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px;
}
.stat-value { font-size: 1.3rem; font-weight: 700; }

.int-card {
    background: #1A1F2E; border: 1px solid #2A3045;
    border-radius: 12px; padding: 18px 20px;
}
.int-name {
    font-size: 0.78rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 10px;
}
.int-row {
    display: flex; justify-content: space-between;
    font-size: 0.85rem; margin: 5px 0;
}
.int-key { color: #9AA0AF; }
.int-val { font-weight: 600; color: #E0E0E0; }

.sec {
    font-size: 1rem; font-weight: 600; color: #E0E0E0;
    border-left: 3px solid #56CFB2;
    padding-left: 10px; margin: 20px 0 14px 0;
}
.sb-div { border: none; border-top: 1px solid #2A3045; margin: 14px 0; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

@st.cache_data(ttl=30)
def load_latest(path: Path) -> dict | None:
    """Last CSV row as a dict of floats/strings, or None if file missing."""
    if not path.exists():
        return None
    last: dict | None = None
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            last = row
    if last is None:
        return None
    out: dict = {}
    for k, v in last.items():
        try:
            out[k] = float(v)
        except (ValueError, TypeError):
            out[k] = v
    return out


@st.cache_data(ttl=30)
def load_all(path: Path) -> dict | None:
    """All CSV rows as column-wise lists, or None if file missing."""
    if not path.exists():
        return None
    cols: dict = defaultdict(list)
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            for k, v in row.items():
                try:
                    cols[k].append(float(v))
                except (ValueError, TypeError):
                    cols[k].append(v)
    return dict(cols)


def _status(wait: float) -> tuple[str, str]:
    if wait < THRESH_GREEN:
        return "green", "Flowing"
    if wait < THRESH_ORANGE:
        return "orange", "Moderate"
    return "red", "Congested"


def _last_emg(all_rows: dict | None) -> str:
    if not all_rows:
        return "—"
    times = all_rows.get("sim_time", [])
    emgs  = all_rows.get("emergency_count", [])
    last_t = None
    for t_val, e in zip(times, emgs):
        if isinstance(e, (int, float)) and e > 0:
            last_t = t_val
    return f"t = {last_t:.0f} s" if last_t is not None else "None detected"


def _mean_wait(all_rows: dict | None, col_name: str) -> float:
    if not all_rows:
        return 0.0
    vals = [v for v in all_rows.get(col_name, []) if isinstance(v, (int, float))]
    return sum(vals) / len(vals) if vals else 0.0


def _peak_queue_intB(latest: dict | None, all_rows: dict | None) -> str:
    """Peak (run-wide) queue for each int_B approach."""
    if not all_rows:
        return "—"
    def _peak(c: str) -> int:
        vals = [v for v in all_rows.get(c, []) if isinstance(v, (int, float))]
        return int(max(vals, default=0))
    return (f"N:{_peak('queue_north')}  S:{_peak('queue_south')}  "
            f"E:{_peak('queue_east')}  W:{_peak('queue_west')}")


def _current_queue_intB(latest: dict | None) -> str:
    if not latest:
        return "—"
    return (f"N:{int(latest.get('queue_north', 0))}  "
            f"S:{int(latest.get('queue_south', 0))}  "
            f"E:{int(latest.get('queue_east', 0))}  "
            f"W:{int(latest.get('queue_west', 0))}")


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div style="padding:10px 0 4px 0;">
      <div style="font-size:1.6rem;">🗺️</div>
      <div style="font-size:1.05rem;font-weight:700;color:#E0E0E0;">City Map View</div>
      <div style="font-size:0.8rem;color:#9AA0AF;margin-top:2px;">
        Smart City Traffic Monitor · Casablanca
      </div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<hr class="sb-div">', unsafe_allow_html=True)

    # ── Navigation ──────────────────────────────────────────────────────────
    st.page_link("app.py",            label="📊  Performance Dashboard")
    st.page_link("pages/map_view.py", label="🗺️  City Map View")

    st.markdown('<hr class="sb-div">', unsafe_allow_html=True)

    # ── Data source picker ──────────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:0.72rem;color:#9AA0AF;text-transform:uppercase;'
        'letter-spacing:0.06em;margin-bottom:6px;">Data Source</div>',
        unsafe_allow_html=True,
    )
    data_source: str = st.selectbox(
        "data_source",
        options=["smart", "vision", "fixed"],
        format_func=lambda x: {
            "smart":  "🧠  Smart Controller",
            "vision": "📷  Vision (Camera AI)",
            "fixed":  "⏱️  Fixed Cycle",
        }[x],
        label_visibility="collapsed",
    )

    st.markdown('<hr class="sb-div">', unsafe_allow_html=True)

    # ── Live stats panel ────────────────────────────────────────────────────
    csv_path = CSV_MAP[data_source]
    latest   = load_latest(csv_path)
    all_rows = load_all(csv_path)

    if latest:
        st.markdown(
            '<div style="font-size:0.72rem;color:#9AA0AF;text-transform:uppercase;'
            'letter-spacing:0.06em;margin-bottom:8px;">Live Snapshot</div>',
            unsafe_allow_html=True,
        )
        for label, value, color in [
            ("Simulation Time", f"{latest.get('sim_time', 0):.0f} s",          "#7B8CDE"),
            ("Total Vehicles",  f"{int(latest.get('total_vehicles', 0))}",       "#56CFB2"),
            ("Total Waiting",   f"{latest.get('total_waiting_time', 0):.1f} s", "#F97316"),
            ("Emergency Lanes", f"{int(latest.get('emergency_count', 0))}",     "#F4845F"),
        ]:
            st.markdown(
                f'<div class="stat-card">'
                f'<div class="stat-label">{label}</div>'
                f'<div class="stat-value" style="color:{color};">{value}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.warning(f"No data for **{data_source}** mode.\nRun the simulation first.")

    st.markdown('<hr class="sb-div">', unsafe_allow_html=True)

    col_btn, col_ts = st.columns([3, 2])
    if col_btn.button("🔄  Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    col_ts.caption(time.strftime("%H:%M:%S"))

    st.markdown('<hr class="sb-div">', unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:0.72rem;color:#3A4060;text-align:center;">'
        'Academic project · 2025–2026</div>',
        unsafe_allow_html=True,
    )

# Auto-refresh every 30 seconds via HTTP meta header
st.markdown('<meta http-equiv="refresh" content="30">', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
st.markdown("""
<div style="padding:6px 0 18px 0;">
  <h1 style="font-size:1.85rem;font-weight:800;margin:0;color:#E0E0E0;">
    🗺️ Smart City Map
    <span style="font-size:0.9rem;font-weight:400;color:#9AA0AF;margin-left:12px;">
      Casablanca — Boulevard Mohammed V
    </span>
  </h1>
  <p style="color:#9AA0AF;margin:5px 0 0 0;font-size:0.88rem;">
    Live traffic state at 3 simulated intersections &nbsp;·&nbsp;
    Coordinates: 33.5731° N, −7.5898° W &nbsp;·&nbsp; INPT Research Project
  </p>
</div>
""", unsafe_allow_html=True)

if latest is None:
    st.warning(
        f"No CSV data found for **{data_source}** mode. "
        "Run the simulation first from the Performance Dashboard."
    )
    st.stop()

# ---------------------------------------------------------------------------
# Build per-intersection state from latest CSV row
# ---------------------------------------------------------------------------
int_data: list[dict] = []
for cfg in INTERSECTIONS:
    wait        = latest.get(cfg["wait_col"], 0.0)
    color, lbl  = _status(wait)
    int_data.append({
        **cfg,
        "wait":        wait,
        "color":       color,
        "status":      lbl,
        "mean_wait":   _mean_wait(all_rows, cfg["wait_col"]),
        "queue_now":   _current_queue_intB(latest) if cfg["id"] == "int_B" else "— (int_B only)",
        "queue_peak":  _peak_queue_intB(latest, all_rows) if cfg["id"] == "int_B" else "— (int_B only)",
        "last_emg":    _last_emg(all_rows),
    })

# ---------------------------------------------------------------------------
# Build Folium map
# ---------------------------------------------------------------------------
center_lat = sum(d["lat"] for d in int_data) / len(int_data)
center_lon = sum(d["lon"] for d in int_data) / len(int_data)

m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=15,
    tiles="CartoDB dark_matter",
    prefer_canvas=True,
)

# ── Boulevard route polyline ────────────────────────────────────────────────
folium.PolyLine(
    locations=[(d["lat"], d["lon"]) for d in int_data],
    color="#F97316",
    weight=5,
    opacity=0.65,
    tooltip="Boulevard Mohammed V",
    dash_array="10 6",
).add_to(m)

# ── Heatmap layer ───────────────────────────────────────────────────────────
# 21 interpolated points per segment; weight = avg endpoint waiting / 100 s
heat_points: list[list[float]] = []
for i in range(len(int_data) - 1):
    a, b = int_data[i], int_data[i + 1]
    seg_wait = (a["wait"] + b["wait"]) / 2.0
    for step in range(21):
        t   = step / 20
        lat = a["lat"] + t * (b["lat"] - a["lat"])
        lon = a["lon"] + t * (b["lon"] - a["lon"])
        heat_points.append([lat, lon, max(min(seg_wait / 100.0, 1.0), 0.05)])

HeatMap(
    heat_points,
    name="Traffic Density",
    min_opacity=0.35,
    max_zoom=18,
    radius=28,
    blur=22,
    gradient={0.25: "#56CFB2", 0.55: "#F97316", 0.80: "#F4845F", 1.00: "#EF4444"},
).add_to(m)

# ── Intersection circle markers ─────────────────────────────────────────────
for d in int_data:
    badge_bg = _BADGE_HEX[d["color"]]

    popup_html = f"""
    <div style="font-family:Arial,sans-serif;min-width:255px;color:#1e293b;">
      <div style="background:{badge_bg};color:#fff;
                  padding:8px 12px;border-radius:6px 6px 0 0;
                  font-weight:700;font-size:0.9rem;">
        {d['short']} &nbsp;·&nbsp; {d['status'].upper()}
      </div>
      <div style="padding:10px 14px;background:#f8fafc;
                  border:1px solid #e2e8f0;border-top:none;
                  border-radius:0 0 6px 6px;">
        <table style="width:100%;font-size:0.82rem;border-collapse:collapse;">
          <tr>
            <td style="color:#64748b;padding:3px 0;width:46%;">Intersection type</td>
            <td style="font-weight:600;">{d['type']}</td>
          </tr>
          <tr>
            <td style="color:#64748b;padding:3px 0;">Current wait</td>
            <td style="font-weight:600;">{d['wait']:.1f} s</td>
          </tr>
          <tr>
            <td style="color:#64748b;padding:3px 0;">Avg wait (full run)</td>
            <td style="font-weight:600;">{d['mean_wait']:.1f} s</td>
          </tr>
          <tr>
            <td style="color:#64748b;padding:3px 0;">Current queue</td>
            <td style="font-weight:600;font-size:0.79rem;">{d['queue_now']}</td>
          </tr>
          <tr>
            <td style="color:#64748b;padding:3px 0;">Peak queue (run)</td>
            <td style="font-weight:600;font-size:0.79rem;">{d['queue_peak']}</td>
          </tr>
          <tr>
            <td style="color:#64748b;padding:3px 0;">Last emergency</td>
            <td style="font-weight:600;">{d['last_emg']}</td>
          </tr>
        </table>
      </div>
    </div>"""

    folium.CircleMarker(
        location=[d["lat"], d["lon"]],
        radius=18,
        color="white",
        weight=2.5,
        fill=True,
        fill_color=d["color"],
        fill_opacity=0.88,
        popup=folium.Popup(popup_html, max_width=295),
        tooltip=f"  {d['short']}  —  {d['status']}  |  wait: {d['wait']:.1f} s  ",
    ).add_to(m)

    # Floating label above the marker
    folium.Marker(
        location=[d["lat"] + 0.00015, d["lon"]],
        icon=folium.DivIcon(
            html=(
                f'<div style="font-family:Arial,sans-serif;font-size:0.67rem;'
                f'font-weight:700;color:#ffffff;'
                f'text-shadow:0 0 4px #000,0 0 4px #000;'
                f'white-space:nowrap;text-align:center;">'
                f'{d["short"]}</div>'
            ),
            icon_size=(120, 18),
            icon_anchor=(60, 0),
        ),
    ).add_to(m)

# ── Legend (injected as fixed HTML overlay) ─────────────────────────────────
legend_html = """
<div style="
    position:fixed; bottom:32px; right:14px; z-index:9999;
    background:rgba(14,17,23,0.93); border:1px solid #2A3045;
    border-radius:10px; padding:13px 17px;
    font-family:Arial,sans-serif; font-size:0.78rem;
    color:#C8CDD8; line-height:2.1; min-width:180px;
    box-shadow:0 4px 16px rgba(0,0,0,0.5);
">
  <div style="font-weight:700;color:#E0E0E0;margin-bottom:7px;font-size:0.83rem;">
    🚦 Traffic Status
  </div>
  <div>
    <span style="display:inline-block;width:13px;height:13px;border-radius:50%;
         background:#16a34a;margin-right:8px;vertical-align:middle;"></span>
    <strong>Flowing</strong> — &lt; 30 s wait
  </div>
  <div>
    <span style="display:inline-block;width:13px;height:13px;border-radius:50%;
         background:#ea580c;margin-right:8px;vertical-align:middle;"></span>
    <strong>Moderate</strong> — 30–70 s
  </div>
  <div>
    <span style="display:inline-block;width:13px;height:13px;border-radius:50%;
         background:#dc2626;margin-right:8px;vertical-align:middle;"></span>
    <strong>Congested</strong> — &gt; 70 s wait
  </div>
  <hr style="border:none;border-top:1px solid #2A3045;margin:8px 0 7px 0;">
  <div>
    <span style="display:inline-block;width:26px;height:4px;background:#F97316;
         border-radius:2px;margin-right:7px;vertical-align:middle;opacity:0.7;"></span>
    Boulevard Mohammed V
  </div>
  <div style="margin-top:4px;">
    <span style="display:inline-block;width:26px;height:10px;border-radius:2px;
         margin-right:7px;vertical-align:middle;
         background:linear-gradient(to right,#56CFB2,#F97316,#EF4444);"></span>
    Traffic density heat
  </div>
</div>"""
m.get_root().html.add_child(folium.Element(legend_html))

# ---------------------------------------------------------------------------
# Render map
# ---------------------------------------------------------------------------
st_folium(m, use_container_width=True, height=540, returned_objects=[])

# ---------------------------------------------------------------------------
# Per-intersection status cards
# ---------------------------------------------------------------------------
st.markdown('<div class="sec">Intersection Status</div>', unsafe_allow_html=True)

card_cols = st.columns(3)
for col_widget, d in zip(card_cols, int_data):
    bg = _BADGE_HEX[d["color"]]
    col_widget.markdown(
        f"""<div class="int-card" style="border-top:3px solid {bg};">
              <div class="int-name" style="color:{bg};">{d['short']}</div>
              <div style="margin-bottom:10px;">
                <span style="background:{bg}22;color:{bg};border:1px solid {bg}44;
                             border-radius:20px;padding:2px 10px;
                             font-size:0.72rem;font-weight:700;">
                  {d['status'].upper()}
                </span>
              </div>
              <div class="int-row">
                <span class="int-key">Type</span>
                <span class="int-val">{d['type']}</span>
              </div>
              <div class="int-row">
                <span class="int-key">Current wait</span>
                <span class="int-val">{d['wait']:.1f} s</span>
              </div>
              <div class="int-row">
                <span class="int-key">Avg wait (run)</span>
                <span class="int-val">{d['mean_wait']:.1f} s</span>
              </div>
              <div class="int-row">
                <span class="int-key">Current queue</span>
                <span class="int-val" style="font-size:0.8rem;">{d['queue_now']}</span>
              </div>
              <div class="int-row">
                <span class="int-key">Peak queue (run)</span>
                <span class="int-val" style="font-size:0.8rem;">{d['queue_peak']}</span>
              </div>
              <div class="int-row">
                <span class="int-key">Last emergency</span>
                <span class="int-val">{d['last_emg']}</span>
              </div>
            </div>""",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("""
<div style="text-align:center;color:#3A4060;font-size:0.76rem;
            padding:28px 0 12px 0;border-top:1px solid #1E2335;margin-top:32px;">
  <div style="font-size:1.1rem;font-weight:800;color:#4A5068;
              letter-spacing:0.08em;margin-bottom:6px;">
    INPT &nbsp;·&nbsp; Institut National des Postes et Télécommunications
  </div>
  <strong>AI Traffic Brain</strong> &nbsp;—&nbsp; Smart City Map View
  &nbsp;·&nbsp; Casablanca, Morocco &nbsp;·&nbsp; Academic Year 2025–2026
</div>
""", unsafe_allow_html=True)