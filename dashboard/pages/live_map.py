"""
AI-Traffic-Brain — Live Schematic Map Demo
==========================================
A fully animated, self-contained HTML/CSS/JS schematic of the 3-intersection
network rendered inside Streamlit via st.components.v1.html().

Architecture
------------
* All animation logic lives in a single HTML blob injected via html().
* A Python helper (_build_html) assembles the blob from a `sim_data` dict.
* In DEMO mode that dict is populated with mock values generated in JS.
* To connect real simulation data: replace the INJECT_DATA section at the
  top of the JS with values read from your CSV / TraCI / API call.

Real-data injection point (search for "REAL DATA INJECTION" in the JS):
  window.SIM_DATA = {
      intA_phase: 0,          // 0=NS_GREEN, 2=EW_GREEN, 1/3=yellow
      intA_vehicle_count: 12,
      intA_wait: 23.4,
      intB_phase: 2,
      intB_vehicle_count: 18,
      intB_wait: 41.1,
      intC_phase: 0,
      intC_vehicle_count: 9,
      intC_wait: 15.2,
      emergency_present: false,
      sim_time: 1234,
  };
Replace the mock JS generator with a Streamlit→JS bridge using
st.session_state + st.components query params, or poll an endpoint.
"""

import streamlit as st
import streamlit.components.v1 as components

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Traffic Brain — Live Map",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Inter:wght@400;500;600;700&display=swap');
    html,body,[data-testid="stAppViewContainer"]{
        background-color:#0a0e1a !important;
        background-image:
            linear-gradient(rgba(0,212,255,0.022) 1px,transparent 1px),
            linear-gradient(90deg,rgba(0,212,255,0.022) 1px,transparent 1px);
        background-size:48px 48px;
        color:#c8d4f0;font-family:'Inter',sans-serif;
    }
    [data-testid="stHeader"]{background:transparent !important;}
    [data-testid="stSidebar"]{
        background:linear-gradient(180deg,#060910 0%,#0b1020 45%,#080c1a 100%) !important;
        border-right:1px solid rgba(0,212,255,0.12) !important;
        box-shadow:4px 0 40px rgba(0,0,0,0.6);
    }
    [data-testid="stSidebar"] a{
        color:#3a4a6a !important;font-family:'Inter',sans-serif !important;
        font-size:0.84rem !important;text-decoration:none !important;transition:color 0.2s !important;
    }
    [data-testid="stSidebar"] a:hover{color:#00d4ff !important;}
    .sb-div{border:none;border-top:1px solid rgba(255,255,255,0.045);margin:18px 0;}
    @keyframes logoPulse{
        0%,100%{transform:scale(1) rotate(0deg);filter:drop-shadow(0 0 10px rgba(0,212,255,0.35));}
        30%{transform:scale(1.08) rotate(-4deg);filter:drop-shadow(0 0 18px rgba(0,212,255,0.6));}
        70%{transform:scale(1.08) rotate(4deg);filter:drop-shadow(0 0 18px rgba(139,92,246,0.6));}
    }
    @keyframes statusBlink{0%,100%{opacity:1;}50%{opacity:0.3;}}
    .stButton>button{
        background:linear-gradient(135deg,rgba(0,212,255,0.14),rgba(0,212,255,0.06)) !important;
        border:1px solid rgba(0,212,255,0.35) !important;color:#00d4ff !important;
        font-family:'Space Mono',monospace !important;font-size:0.72rem !important;
        font-weight:700 !important;letter-spacing:0.1em !important;
        border-radius:10px !important;text-transform:uppercase !important;
        transition:all 0.25s ease !important;
    }
    .stButton>button:hover{
        background:rgba(0,212,255,0.22) !important;
        box-shadow:0 0 28px rgba(0,212,255,0.22) !important;
        transform:translateY(-2px) !important;
    }
    div[data-baseweb="select"]>div{
        background:rgba(255,255,255,0.03) !important;
        border:1px solid rgba(255,255,255,0.08) !important;
        border-radius:10px !important;color:#c8d4f0 !important;
    }
    </style>
    <div style="padding:16px 0 10px 0;">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;">
        <div style="font-size:2rem;animation:logoPulse 5s ease-in-out infinite;">🎬</div>
        <div>
          <div style="font-family:'Space Mono',monospace;font-size:0.82rem;font-weight:700;
                      background:linear-gradient(130deg,#00d4ff,#8b5cf6);
                      -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                      background-clip:text;letter-spacing:0.04em;">
            LIVE MAP DEMO
          </div>
          <div style="font-family:'Inter',sans-serif;font-size:0.67rem;color:#2a3a5a;
                      margin-top:2px;letter-spacing:0.05em;">
            3-Intersection Network
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
                     letter-spacing:0.1em;">SIMULATION LIVE</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<hr class="sb-div">', unsafe_allow_html=True)
    st.page_link("app.py",            label="📊  Performance Dashboard")
    st.page_link("pages/live_map.py", label="🎬  Live Map Demo")

    st.markdown('<hr class="sb-div">', unsafe_allow_html=True)
    st.markdown(
        '<div style="font-family:\'Space Mono\',monospace;font-size:0.59rem;color:#2a3a5a;'
        'text-transform:uppercase;letter-spacing:0.12em;margin-bottom:8px;">Simulation Mode</div>',
        unsafe_allow_html=True,
    )
    mode = st.selectbox(
        "mode", ["NORMAL", "EMERGENCY", "ACCIDENT", "NIGHT"],
        format_func=lambda x: {
            "NORMAL":    "🟢  Normal Traffic",
            "EMERGENCY": "🚨  Emergency Override",
            "ACCIDENT":  "⚠️  Accident Detected",
            "NIGHT":     "🌙  Night Mode",
        }[x],
        label_visibility="collapsed",
    )

    st.markdown('<hr class="sb-div">', unsafe_allow_html=True)
    st.markdown(
        '<div style="font-family:\'Inter\',sans-serif;font-size:0.68rem;color:#1a2438;'
        'text-align:center;letter-spacing:0.04em;">Academic Project · 2025–2026</div>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
_MODE_COLOR = {
    "NORMAL":    "#10b981",
    "EMERGENCY": "#ff4757",
    "ACCIDENT":  "#ff9500",
    "NIGHT":     "#8b5cf6",
}
_mode_color = _MODE_COLOR.get(mode, "#00d4ff")

st.markdown(f"""
<style>
@keyframes gradientShift{{
    0%{{background-position:0% 50%;}}50%{{background-position:100% 50%;}}100%{{background-position:0% 50%;}}
}}
@keyframes fadeInUp{{
    from{{opacity:0;transform:translateY(16px);}}to{{opacity:1;transform:translateY(0);}}
}}
</style>
<div style="padding:10px 0 26px 0;position:relative;overflow:hidden;
            animation:fadeInUp 0.5s ease both;">
  <div style="position:absolute;top:-10px;right:-10px;width:240px;height:120px;
              background:radial-gradient(ellipse at top right,
                rgba(0,212,255,0.07) 0%,rgba(139,92,246,0.05) 40%,transparent 70%);
              pointer-events:none;border-radius:0 0 0 100px;"></div>
  <div style="display:flex;align-items:center;gap:18px;flex-wrap:wrap;">
    <div style="font-size:2.4rem;">🎬</div>
    <div style="flex:1;min-width:260px;">
      <h1 style="font-family:'Space Mono',monospace;font-size:1.7rem;font-weight:700;
                 margin:0 0 6px 0;line-height:1.1;
                 background:linear-gradient(130deg,#00d4ff 0%,#8b5cf6 55%,#00d4ff 100%);
                 background-size:200% auto;
                 -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                 background-clip:text;animation:gradientShift 5s ease infinite;">
        Live Schematic Map
      </h1>
      <p style="font-family:'Inter',sans-serif;color:#2a3a5a;margin:0;
                font-size:0.8rem;letter-spacing:0.06em;">
        ANIMATED SCHEMATIC &nbsp;·&nbsp; NOT GEOGRAPHICALLY ACCURATE &nbsp;·&nbsp;
        <span style="color:#00d4ff;font-weight:600;">SELECT A MODE IN THE SIDEBAR</span>
      </p>
    </div>
    <div style="flex-shrink:0;background:rgba({{}},0.08);
                background:rgba(0,0,0,0.3);
                border:1px solid {_mode_color}40;
                border-radius:10px;padding:8px 16px;text-align:center;">
      <div style="font-family:'Space Mono',monospace;font-size:0.62rem;
                  color:#2a3a5a;letter-spacing:0.1em;text-transform:uppercase;
                  margin-bottom:4px;">Active Mode</div>
      <div style="font-family:'Space Mono',monospace;font-size:0.95rem;
                  font-weight:700;color:{_mode_color};letter-spacing:0.08em;">
        {mode}
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# HTML / JS builder  (v2 — improved traffic behaviour)
# ---------------------------------------------------------------------------

def _build_html(mode: str) -> str:
    mode_js = mode.upper()
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Inter:wght@400;500;600;700&display=swap');
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    background: #0a0e1a;
    background-image:
      linear-gradient(rgba(0,212,255,0.018) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0,212,255,0.018) 1px, transparent 1px);
    background-size: 40px 40px;
    font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
    overflow: hidden;
    color: #c8d4f0;
  }}
  #wrapper {{
    display: flex;
    gap: 0;
    width: 100%;
    height: 520px;
    border: 1px solid rgba(125,211,252,0.13);
    border-radius: 18px;
    overflow: hidden;
    background:
      linear-gradient(135deg, rgba(15,23,42,0.96), rgba(2,6,23,0.98));
    box-shadow:
      0 24px 80px rgba(0,0,0,0.46),
      inset 0 1px 0 rgba(255,255,255,0.04);
  }}
  #canvas-col {{
    flex: 1 1 auto;
    position: relative;
    min-width: 0;
    overflow: hidden;
    cursor: grab;
    user-select: none;
    touch-action: none;
  }}
  #canvas-col.is-dragging {{ cursor: grabbing; }}
  canvas {{
    display: block;
    position: absolute;
    left: 0;
    top: 0;
    cursor: grab;
  }}
  #canvas-col.is-dragging canvas {{ cursor: grabbing; }}
  body.map-dragging, body.map-dragging * {{
    user-select: none !important;
    cursor: grabbing !important;
  }}
  #panel {{
    width: 288px;
    flex-shrink: 0;
    box-sizing: border-box;
    background:
      linear-gradient(180deg, rgba(8,13,24,0.98) 0%, rgba(5,8,16,0.99) 100%);
    border-left: 1px solid rgba(125,211,252,0.15);
    padding: 16px 14px;
    overflow-y: auto;
    display: block;
    backdrop-filter: blur(20px);
    box-shadow: inset 1px 0 0 rgba(255,255,255,0.035);
  }}
  #panel > * {{
    box-sizing: border-box;
    margin-bottom: 16px;
  }}
  #panel > *:last-child {{ margin-bottom: 0; }}
  #panel::-webkit-scrollbar,
  #log-box::-webkit-scrollbar {{ width: 7px; }}
  #panel::-webkit-scrollbar-thumb,
  #log-box::-webkit-scrollbar-thumb {{
    background: rgba(125,211,252,0.18);
    border-radius: 999px;
  }}
  @keyframes livePulse {{
    0%,100% {{ opacity: 1; box-shadow: 0 0 0 0 rgba(34,197,94,0.38); }}
    50% {{ opacity: 0.55; box-shadow: 0 0 0 7px rgba(34,197,94,0); }}
  }}
  @keyframes cardHalo {{
    0%,100% {{ box-shadow: 0 12px 30px rgba(0,0,0,0.18); }}
    50% {{ box-shadow: 0 14px 36px rgba(14,165,233,0.09); }}
  }}
  .int-card {{
    --status-color: rgba(125,211,252,0.45);
    --load-color: #22c55e;
    --load-width: 18%;
    position: static;
    overflow: visible;
    min-height: auto;
    background:
      radial-gradient(circle at 16% 0%, color-mix(in srgb, var(--status-color) 16%, transparent), transparent 38%),
      linear-gradient(145deg, rgba(15,23,42,0.82), rgba(4,8,18,0.94));
    border: 1px solid rgba(255,255,255,0.085);
    border-left: 3px solid var(--status-color);
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 16px;
    transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
    animation: cardHalo 6s ease-in-out infinite;
  }}
  .int-card::before {{
    content: none;
  }}
  .int-card > * {{
    position: static;
  }}
  .int-card:hover {{
    border-color: rgba(255,255,255,0.18);
    box-shadow: 0 18px 45px rgba(0,0,0,0.28), 0 0 28px color-mix(in srgb, var(--status-color) 18%, transparent);
    transform: translateY(-1px);
  }}
  .int-card-head {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 13px;
    min-width: 0;
  }}
  .int-card-title {{
    flex: 1 1 auto;
    min-width: 0;
    font-family: 'Space Mono', monospace;
    font-size: 0.66rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    line-height: 1.4;
  }}
  .signal-pill {{
    flex: 0 0 auto;
    border: 1px solid var(--status-color);
    border-radius: 999px;
    padding: 4px 8px;
    color: var(--status-color);
    background: color-mix(in srgb, var(--status-color) 13%, rgba(2,6,23,0.82));
    font-family: 'Space Mono', monospace;
    font-size: 0.52rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    line-height: 1.25;
    text-transform: uppercase;
    white-space: nowrap;
    box-shadow: 0 0 16px color-mix(in srgb, var(--status-color) 20%, transparent);
  }}
  .phase-readout {{
    display: grid;
    gap: 6px;
    padding: 11px 12px;
    border: 1px solid rgba(226,232,240,0.07);
    border-radius: 10px;
    background: rgba(255,255,255,0.032);
    margin-bottom: 12px;
    line-height: 1.4;
  }}
  .phase-readout span,
  .metric-tile span,
  .mini-stat span {{
    color: #7283a8;
    font-family: 'Inter', sans-serif;
    font-size: 0.58rem;
    font-weight: 700;
    letter-spacing: 0.07em;
    text-transform: uppercase;
  }}
  .phase-readout strong {{
    color: #eef5ff;
    font-family: 'Space Mono', monospace;
    font-size: 0.95rem;
    line-height: 1.18;
  }}
  .int-metrics {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-bottom: 12px;
  }}
  .mini-stat {{
    min-width: 0;
    min-height: 52px;
    padding: 10px;
    border: 1px solid rgba(226,232,240,0.065);
    border-radius: 10px;
    background: rgba(2,6,23,0.36);
  }}
  .mini-stat strong {{
    display: block;
    margin-top: 4px;
    color: #eef5ff;
    font-family: 'Space Mono', monospace;
    line-height: 1.18;
  }}
  .mini-stat .vehicle-value {{
    font-size: 1.25rem;
    letter-spacing: 0.02em;
  }}
  .mini-stat .wait-value {{
    font-size: 0.82rem;
    color: #d9e8ff;
  }}
  .int-row {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 12px;
    font-size: 0.72rem;
    margin: 5px 0;
    color: #7082a8;
    font-family: 'Inter', sans-serif;
  }}
  .int-row span:first-child {{
    white-space: nowrap;
  }}
  .int-row span:last-child {{
    color: #eef5ff;
    font-weight: 700;
    font-family: 'Space Mono', monospace;
    font-size: 0.68rem;
    text-align: right;
  }}
  .load-track {{
    height: 7px;
    border-radius: 999px;
    background: rgba(148,163,184,0.13);
    overflow: hidden;
    margin: 4px 0 12px;
  }}
  .load-track span {{
    display: block;
    width: var(--load-width);
    height: 100%;
    border-radius: inherit;
    background: linear-gradient(90deg, var(--load-color), color-mix(in srgb, var(--load-color) 62%, #ffffff));
    box-shadow: 0 0 14px color-mix(in srgb, var(--load-color) 32%, transparent);
    transition: width 0.35s ease, background 0.35s ease;
  }}
  .card-foot {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    flex-wrap: wrap;
    min-height: 28px;
  }}
  .badge {{
    display: inline-block;
    padding: 4px 10px;
    border-radius: 999px;
    font-family: 'Space Mono', monospace;
    font-size: 0.61rem;
    font-weight: 700;
    margin-top: 8px;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.08);
  }}
  .axis-chip {{
    color: #7dd3fc;
    border: 1px solid rgba(125,211,252,0.18);
    border-radius: 999px;
    padding: 4px 8px;
    background: rgba(125,211,252,0.055);
    font-family: 'Space Mono', monospace;
    font-size: 0.56rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }}
  .mode-card {{
    display: flex;
    flex-direction: column;
    gap: 5px;
    background:
      linear-gradient(145deg, rgba(34,197,94,0.10), rgba(14,165,233,0.045));
    border: 1px solid rgba(0,212,255,0.22);
    border-radius: 12px;
    padding: 14px;
    margin-bottom: 16px;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.06), 0 10px 28px rgba(0,0,0,0.2);
  }}
  .mode-main {{
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .mode-dot {{
    width: 8px;
    height: 8px;
    border-radius: 999px;
    background: #22c55e;
    animation: livePulse 2s ease-in-out infinite;
  }}
  #mode-badge {{
    font-family: 'Space Mono', monospace;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    color: #00d4ff;
  }}
  #mode-subtitle {{
    color: #8496ba;
    font-family: 'Inter', sans-serif;
    font-size: 0.68rem;
    font-weight: 600;
  }}
  .metric-grid {{
    display: grid;
    grid-template-columns: 0.85fr 1fr 1.35fr;
    gap: 9px;
    margin-bottom: 16px;
  }}
  .metric-tile {{
    min-width: 0;
    padding: 10px 8px;
    border: 1px solid rgba(125,211,252,0.12);
    border-radius: 11px;
    background: linear-gradient(160deg, rgba(255,255,255,0.045), rgba(255,255,255,0.018));
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.035);
  }}
  .metric-tile strong {{
    display: block;
    margin-top: 5px;
    color: #eef5ff;
    font-family: 'Space Mono', monospace;
    font-size: 0.70rem;
    line-height: 1.25;
    white-space: normal;
    overflow: visible;
  }}
  #log-box {{
    display: block;
    clear: both;
    background:
      linear-gradient(160deg, rgba(255,255,255,0.04), rgba(255,255,255,0.018));
    border: 1px solid rgba(255,255,255,0.075);
    border-radius: 12px;
    padding: 13px;
    min-height: 132px;
    margin-top: 18px;
    overflow-y: auto;
  }}
  .log-title {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-family: 'Space Mono', monospace;
    font-size: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #7dd3fc;
    margin-bottom: 9px;
    font-weight: 700;
  }}
  .log-title::after {{
    content: "LIVE";
    color: #a78bfa;
    border: 1px solid rgba(167,139,250,0.26);
    border-radius: 999px;
    padding: 2px 6px;
    font-size: 0.5rem;
    letter-spacing: 0.08em;
    background: rgba(167,139,250,0.08);
  }}
  #log-entries {{
    display: flex;
    flex-direction: column;
    gap: 9px;
  }}
  .log-entry {{
    --log-color: #7dd3fc;
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 8px;
    align-items: start;
    position: relative;
    font-family: 'Inter', sans-serif;
    font-size: 0.65rem;
    color: #b9c7e5;
    border: 1px solid rgba(255,255,255,0.065);
    border-left: 2px solid var(--log-color);
    border-radius: 10px;
    background: rgba(2,6,23,0.32);
    padding: 9px;
    line-height: 1.5;
  }}
  .log-entry:hover {{
    border-color: color-mix(in srgb, var(--log-color) 38%, rgba(255,255,255,0.08));
    box-shadow: 0 0 18px color-mix(in srgb, var(--log-color) 12%, transparent);
  }}
  .log-time {{
    color: var(--log-color);
    background: color-mix(in srgb, var(--log-color) 13%, rgba(2,6,23,0.72));
    border: 1px solid color-mix(in srgb, var(--log-color) 24%, transparent);
    border-radius: 999px;
    padding: 2px 5px;
    font-family: 'Space Mono', monospace;
    font-size: 0.53rem;
    font-weight: 700;
    white-space: nowrap;
  }}
  .log-copy {{
    min-width: 0;
    color: #aebcdb;
  }}
  #banner {{
    position: absolute;
    top: 12px; left: 50%; transform: translateX(-50%);
    z-index: 10;
    background: rgba(10,14,26,0.94);
    border-radius: 20px;
    padding: 6px 18px;
    font-family: 'Space Mono', monospace;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    white-space: nowrap;
    pointer-events: none;
    display: none;
    border: 1px solid rgba(0,212,255,0.3);
    box-shadow: 0 0 24px rgba(0,212,255,0.15);
  }}
  #decision-card {{
    position: absolute;
    top: 14px;
    left: 14px;
    z-index: 9;
    width: min(300px, calc(100% - 28px));
    pointer-events: none;
    background:
      linear-gradient(145deg, rgba(8,13,24,0.88), rgba(15,23,42,0.74));
    border: 1px solid rgba(125,211,252,0.18);
    border-radius: 14px;
    padding: 13px 14px 12px;
    backdrop-filter: blur(18px);
    box-shadow:
      0 18px 50px rgba(0,0,0,0.35),
      inset 0 1px 0 rgba(255,255,255,0.08);
  }}
  .decision-kicker {{
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: 'Space Mono', monospace;
    font-size: 0.58rem;
    font-weight: 700;
    letter-spacing: 0.13em;
    text-transform: uppercase;
    color: #7dd3fc;
    margin-bottom: 9px;
  }}
  .live-dot {{
    width: 8px;
    height: 8px;
    border-radius: 999px;
    background: #22c55e;
    animation: livePulse 1.8s ease-in-out infinite;
  }}
  .decision-line {{
    display: grid;
    grid-template-columns: 74px 1fr;
    gap: 10px;
    align-items: start;
    margin: 6px 0;
    font-size: 0.72rem;
    line-height: 1.35;
  }}
  .decision-line span {{
    color: #7788aa;
    font-family: 'Inter', sans-serif;
  }}
  .decision-line strong {{
    color: #eef5ff;
    font-family: 'Space Mono', monospace;
    font-size: 0.68rem;
    letter-spacing: 0.01em;
  }}
  .confidence-bar {{
    height: 5px;
    margin-top: 10px;
    border-radius: 999px;
    background: rgba(255,255,255,0.08);
    overflow: hidden;
  }}
  #confidence-fill {{
    display: block;
    height: 100%;
    width: 84%;
    border-radius: inherit;
    background: linear-gradient(90deg,#22c55e,#f59e0b);
    box-shadow: 0 0 16px rgba(34,197,94,0.3);
    transition: width 0.35s ease;
  }}
  #map-zoom-controls {{
    position: absolute;
    top: 14px;
    right: 14px;
    z-index: 11;
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px;
    border-radius: 12px;
    background: rgba(8,13,24,0.78);
    border: 1px solid rgba(125,211,252,0.18);
    backdrop-filter: blur(16px);
    box-shadow: 0 14px 38px rgba(0,0,0,0.34), inset 0 1px 0 rgba(255,255,255,0.08);
  }}
  .zoom-btn {{
    min-width: 30px;
    height: 30px;
    border: 1px solid rgba(226,232,240,0.14);
    border-radius: 8px;
    background: rgba(255,255,255,0.055);
    color: #eaf6ff;
    font-family: 'Space Mono', monospace;
    font-size: 0.78rem;
    font-weight: 700;
    cursor: pointer;
    transition: background 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
  }}
  canvas {{
    transform-origin: center center;
    will-change: transform;
  }}
  .zoom-btn:hover {{
    background: rgba(125,211,252,0.14);
    border-color: rgba(125,211,252,0.36);
    box-shadow: 0 0 18px rgba(125,211,252,0.16);
  }}
  .zoom-reset {{
    min-width: 58px;
    padding: 0 10px;
    font-size: 0.66rem;
    letter-spacing: 0.04em;
  }}
  #zoom-label {{
    min-width: 38px;
    text-align: center;
    color: #7d8eb2;
    font-family: 'Space Mono', monospace;
    font-size: 0.62rem;
  }}
</style>
</head>
<body>
<div id="wrapper">
  <div id="canvas-col">
    <canvas id="c"></canvas>
    <div id="decision-card">
      <div class="decision-kicker"><span class="live-dot"></span>AI Signal Decision</div>
      <div class="decision-line"><span>Decision</span><strong id="decision-current">—</strong></div>
      <div class="decision-line"><span>Reason</span><strong id="decision-reason">—</strong></div>
      <div class="decision-line"><span>Confidence</span><strong id="decision-confidence">—</strong></div>
      <div class="confidence-bar"><span id="confidence-fill"></span></div>
    </div>
    <div id="map-zoom-controls" aria-label="Map zoom controls">
      <button class="zoom-btn" id="zoom-out" type="button" aria-label="Zoom out">&minus;</button>
      <span id="zoom-label">100%</span>
      <button class="zoom-btn" id="zoom-in" type="button" aria-label="Zoom in">+</button>
      <button class="zoom-btn zoom-reset" id="zoom-reset" type="button">Reset</button>
    </div>
    <div id="banner"></div>
  </div>
  <div id="panel">
    <div class="mode-card">
      <div class="mode-main">
        <span class="mode-dot" id="mode-dot"></span>
        <span id="mode-badge">— MODE —</span>
      </div>
      <div id="mode-subtitle">Simulation running</div>
    </div>
    <div class="metric-grid">
      <div class="metric-tile"><span>Total</span><strong id="metric-total">—</strong></div>
      <div class="metric-tile"><span>Avg wait</span><strong id="metric-wait">—</strong></div>
      <div class="metric-tile"><span>Control</span><strong id="metric-controller">—</strong></div>
    </div>
    <div class="int-card" id="card-a">
      <div class="int-card-head">
        <div class="int-card-title" style="color:#ff9500;">int_A — West T-jct</div>
        <span class="signal-pill" id="a-signal">—</span>
      </div>
      <div class="phase-readout"><span>Phase</span><strong id="a-phase">—</strong></div>
      <div class="int-metrics">
        <div class="mini-stat"><span>Vehicles</span><strong class="vehicle-value" id="a-count">—</strong></div>
        <div class="mini-stat"><span>Avg wait</span><strong class="wait-value" id="a-wait">—</strong></div>
      </div>
      <div class="load-track"><span id="a-load"></span></div>
      <div class="card-foot"><span class="badge" id="a-badge">—</span><span class="axis-chip" id="a-axis">—</span></div>
    </div>
    <div class="int-card" id="card-b">
      <div class="int-card-head">
        <div class="int-card-title" style="color:#00d4ff;">int_B — 4-Way Crossing</div>
        <span class="signal-pill" id="b-signal">—</span>
      </div>
      <div class="phase-readout"><span>Phase</span><strong id="b-phase">—</strong></div>
      <div class="int-metrics">
        <div class="mini-stat"><span>Vehicles</span><strong class="vehicle-value" id="b-count">—</strong></div>
        <div class="mini-stat"><span>Avg wait</span><strong class="wait-value" id="b-wait">—</strong></div>
      </div>
      <div class="load-track"><span id="b-load"></span></div>
      <div class="card-foot"><span class="badge" id="b-badge">—</span><span class="axis-chip" id="b-axis">—</span></div>
    </div>
    <div class="int-card" id="card-c">
      <div class="int-card-head">
        <div class="int-card-title" style="color:#8b5cf6;">int_C — East T-jct</div>
        <span class="signal-pill" id="c-signal">—</span>
      </div>
      <div class="phase-readout"><span>Phase</span><strong id="c-phase">—</strong></div>
      <div class="int-metrics">
        <div class="mini-stat"><span>Vehicles</span><strong class="vehicle-value" id="c-count">—</strong></div>
        <div class="mini-stat"><span>Avg wait</span><strong class="wait-value" id="c-wait">—</strong></div>
      </div>
      <div class="load-track"><span id="c-load"></span></div>
      <div class="card-foot"><span class="badge" id="c-badge">—</span><span class="axis-chip" id="c-axis">—</span></div>
    </div>
    <div id="log-box">
      <div class="log-title">AI Decision Log</div>
      <div id="log-entries"></div>
    </div>
  </div>
</div>

<script>
// ============================================================
// REAL DATA INJECTION POINT
// Replace window.SIM_DATA with live values from your backend.
// In demo mode this object is overwritten by the mock generator
// every simulation tick (see updateMockData below).
//
// Format:
//   window.SIM_DATA = {{
//       intA_phase: 0,          // 0=NS_GREEN, 2=EW_GREEN, 1/3=yellow
//       intA_vehicle_count: 12,
//       intA_wait: 23.4,        // seconds
//       intB_phase: 2,
//       intB_vehicle_count: 18,
//       intB_wait: 41.1,
//       intC_phase: 0,
//       intC_vehicle_count: 9,
//       intC_wait: 15.2,
//       emergency_present: false,
//       sim_time: 1234,
//   }};
// ============================================================
window.SIM_DATA = null;  // null = use mock/demo generator

const MODE = "{mode_js}";

// ── Canvas setup ──────────────────────────────────────────────────────────
const canvas = document.getElementById('c');
const canvasCol = document.getElementById('canvas-col');
const ctx    = canvas.getContext('2d');
const banner = document.getElementById('banner');
const zoomLabel = document.getElementById('zoom-label');

let mapZoom = 1.0;
let panX = 0;
let panY = 0;
let isDragging = false;
let dragStartX = 0;
let dragStartY = 0;
let dragStartPanX = 0;
let dragStartPanY = 0;
const ZOOM_MIN = 0.25;
const ZOOM_MAX = 1.75;
const ZOOM_STEP = 0.25;
const WORLD_EDGE_PAD = 0.40;
const WORLD_SCALE = (1 / ZOOM_MIN) + (WORLD_EDGE_PAD * 2);
const MIN_SCHEMATIC_WIDTH = 1300;
const MIN_INTERSECTION_GAP = 390;
const ROAD_END_MARGIN = 260;

function updateMapTransform() {{
  canvas.style.transform = `translate(${{panX}}px, ${{panY}}px) scale(${{mapZoom}})`;
  zoomLabel.textContent = Math.round(mapZoom * 100) + '%';
}}

function setMapZoom(nextZoom) {{
  const snapped = Math.round(nextZoom / ZOOM_STEP) * ZOOM_STEP;
  mapZoom = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, snapped));
  updateMapTransform();
}}

function resetMapView() {{
  panX = 0;
  panY = 0;
  setMapZoom(1.0);
}}

document.getElementById('zoom-in').addEventListener('click', () => setMapZoom(mapZoom + ZOOM_STEP));
document.getElementById('zoom-out').addEventListener('click', () => setMapZoom(mapZoom - ZOOM_STEP));
document.getElementById('zoom-reset').addEventListener('click', resetMapView);

function startPan(e) {{
  if (e.target.closest('#map-zoom-controls')) return;
  isDragging = true;
  dragStartX = e.clientX;
  dragStartY = e.clientY;
  dragStartPanX = panX;
  dragStartPanY = panY;
  canvasCol.classList.add('is-dragging');
  document.body.classList.add('map-dragging');
  canvasCol.setPointerCapture?.(e.pointerId);
  e.preventDefault();
}}

function movePan(e) {{
  if (!isDragging) return;
  panX = dragStartPanX + (e.clientX - dragStartX);
  panY = dragStartPanY + (e.clientY - dragStartY);
  updateMapTransform();
  e.preventDefault();
}}

function endPan(e) {{
  if (!isDragging) return;
  isDragging = false;
  canvasCol.classList.remove('is-dragging');
  document.body.classList.remove('map-dragging');
  try {{ canvasCol.releasePointerCapture?.(e.pointerId); }} catch (_) {{}}
}}

canvasCol.addEventListener('pointerdown', startPan);
window.addEventListener('pointermove', movePan);
window.addEventListener('pointerup', endPan);
window.addEventListener('pointercancel', endPan);

let W, H, worldW, worldH;
function resize() {{
  const col = document.getElementById('canvas-col');
  W = col.clientWidth;
  H = col.clientHeight;
  worldW = Math.ceil(W * WORLD_SCALE);
  worldH = Math.ceil(H * WORLD_SCALE);
  canvas.width  = worldW;
  canvas.height = worldH;
  canvas.style.width = worldW + 'px';
  canvas.style.height = worldH + 'px';
  canvas.style.left = -((worldW - W) / 2) + 'px';
  canvas.style.top = -((worldH - H) / 2) + 'px';
  updateMapTransform();
}}
resize();
window.addEventListener('resize', () => {{
  resize();
  vehicles.forEach(v => v.resetPath());
}});

// ── Geometry (recomputed each frame — scales with canvas) ─────────────────
function geo() {{
  const cy    = H * 0.5;
  const laneW = Math.max(14, W * 0.032);   // width of one traffic lane
  const mapWidth = Math.max(MIN_SCHEMATIC_WIDTH, W);
  const intersectionGap = Math.max(MIN_INTERSECTION_GAP, W * 0.36);
  const axB   = W * 0.50;
  const axA   = axB - intersectionGap;
  const axC   = axB + intersectionGap;
  const roadY = cy;
  const rbR   = laneW * 3.2;               // center-intersection visual scale
  const sideNy = cy - H * 0.42;
  const sideSy = cy + H * 0.43;
  const halfMapW = Math.max(mapWidth * 0.5, intersectionGap + ROAD_END_MARGIN);
  const halfMapH = Math.max(H * 0.5, 460);
  const mapLeft = axB - halfMapW;
  const mapRight = axB + halfMapW;
  const mapTop = cy - halfMapH;
  const mapBottom = cy + halfMapH;
  return {{ laneW, axA, axB, axC, roadY, rbR, sideNy, sideSy, mapLeft, mapRight, mapTop, mapBottom, mapWidth, intersectionGap }};
}}

function mapExtent(g=null) {{
  const gg = g || geo();
  const worldHalfW = W / (2 * ZOOM_MIN);
  const worldHalfH = H / (2 * ZOOM_MIN);
  return {{
    left: Math.min(W / 2 - worldHalfW - W * WORLD_EDGE_PAD, gg.mapLeft),
    right: Math.max(W / 2 + worldHalfW + W * WORLD_EDGE_PAD, gg.mapRight),
    top: Math.min(H / 2 - worldHalfH - H * WORLD_EDGE_PAD, gg.mapTop),
    bottom: Math.max(H / 2 + worldHalfH + H * WORLD_EDGE_PAD, gg.mapBottom),
  }};
}}

// ── Traffic light state ────────────────────────────────────────────────────
// phase: 0=NS_GREEN  1=NS_YELLOW  2=EW_GREEN  3=EW_YELLOW
const TL = {{
  A: {{ phase:0, timer:0,  durations:[18,3,18,3] }},
  B: {{ phase:2, timer:8,  durations:[20,3,20,3] }},
  C: {{ phase:0, timer:4,  durations:[18,3,18,3] }},
}};

function normalizePhase(value, fallback=0) {{
  const n = Number(value);
  return Number.isInteger(n) && n >= 0 && n <= 3 ? n : fallback;
}}

function signalState(tl, axis) {{
  const p = normalizePhase(tl.phase, 0);
  if (axis === 'ns') {{
    if (p===0) return 'green';
    if (p===1) return 'yellow';
    return 'red';
  }}
  if (p===2) return 'green';
  if (p===3) return 'yellow';
  return 'red';
}}

function tlColor(tl, axis) {{
  const state = signalState(tl, axis);
  if (state === 'green') return '#22c55e';
  if (state === 'yellow') return '#fbbf24';
  return '#ef4444';
}}

function tlAllowsEntry(tl, axis) {{
  return signalState(tl, axis) === 'green';
}}

function tlIsGreen(tl, axis) {{
  return tlAllowsEntry(tl, axis);
}}

let tlDt = 0;
function updateTL(dt) {{
  if (window.SIM_DATA) {{
    TL.A.phase = normalizePhase(window.SIM_DATA.intA_phase, TL.A.phase);
    TL.B.phase = normalizePhase(window.SIM_DATA.intB_phase, TL.B.phase);
    TL.C.phase = normalizePhase(window.SIM_DATA.intC_phase, TL.C.phase);
    return;
  }}
  tlDt += dt;
  if (tlDt < 0.05) return;
  const step = tlDt; tlDt = 0;

  ['A','B','C'].forEach(k => {{
    const tl = TL[k];
    tl.timer += step;
    if (tl.timer >= tl.durations[tl.phase]) {{
      tl.timer -= tl.durations[tl.phase];
      tl.phase  = (tl.phase + 1) % 4;
    }}
  }});

  if (MODE === 'EMERGENCY') {{ TL.A.phase=2; TL.B.phase=2; TL.C.phase=2; }}
  if (MODE === 'NIGHT')     {{ TL.A.durations=[28,2,28,2]; TL.B.durations=[30,2,30,2]; TL.C.durations=[28,2,28,2]; }}
}}

// ── Simulation stats ──────────────────────────────────────────────────────
// Smoothed wait accumulators so night mode always shows meaningful numbers.
const simStats = {{
  A: {{vc:0, wait:0, rawWait:0}},
  B: {{vc:0, wait:0, rawWait:0}},
  C: {{vc:0, wait:0, rawWait:0}},
  time: 0,
}};

function updateMockData(dt) {{
  simStats.time += dt;
  if (window.SIM_DATA) {{
    // ── REAL DATA path ────────────────────────────────────────────────
    simStats.A.vc   = window.SIM_DATA.intA_vehicle_count || 0;
    simStats.A.wait = window.SIM_DATA.intA_wait || 0;
    simStats.B.vc   = window.SIM_DATA.intB_vehicle_count || 0;
    simStats.B.wait = window.SIM_DATA.intB_wait || 0;
    simStats.C.vc   = window.SIM_DATA.intC_vehicle_count || 0;
    simStats.C.wait = window.SIM_DATA.intC_wait || 0;
    return;
  }}
  // ── Demo path: derive stats from live vehicle positions ──────────────
  const g = geo();

  // Count vehicles near each intersection
  const vcA = vehicles.filter(v => !v.done && Math.abs(v.x-g.axA)<100).length;
  const vcB = vehicles.filter(v => !v.done && Math.abs(v.x-g.axB)<110).length;
  const vcC = vehicles.filter(v => !v.done && Math.abs(v.x-g.axC)<100).length;

  // Accumulate wait time when signal is red for the dominant approach
  const waitFactor = {{ NORMAL:1.0, EMERGENCY:0.2, ACCIDENT:1.8, NIGHT:0.6 }}[MODE] || 1.0;
  if (!tlIsGreen(TL.A,'ew')) simStats.A.rawWait += dt * vcA * 1.4 * waitFactor;
  else simStats.A.rawWait = Math.max(0, simStats.A.rawWait - dt * 3.0);
  if (!tlIsGreen(TL.B,'ew')) simStats.B.rawWait += dt * vcB * 1.2 * waitFactor;
  else simStats.B.rawWait = Math.max(0, simStats.B.rawWait - dt * 2.5);
  if (!tlIsGreen(TL.C,'ew')) simStats.C.rawWait += dt * vcC * 1.4 * waitFactor;
  else simStats.C.rawWait = Math.max(0, simStats.C.rawWait - dt * 3.0);

  // Cap and apply a minimum baseline so night mode shows non-zero wait
  const minWait = {{ NORMAL:4, EMERGENCY:1, ACCIDENT:12, NIGHT:3 }}[MODE] || 4;
  const cap     = {{ NORMAL:55, EMERGENCY:8, ACCIDENT:90, NIGHT:22 }}[MODE] || 55;

  // Night mode: always show at least 1 vehicle per node so panel is never blank
  const minVc = MODE === 'NIGHT' ? 1 : 0;
  simStats.A.vc   = Math.max(minVc, vcA);
  simStats.B.vc   = Math.max(minVc, vcB);
  simStats.C.vc   = Math.max(minVc, vcC);
  simStats.A.wait = Math.min(cap, Math.max(minWait, simStats.A.rawWait));
  simStats.B.wait = Math.min(cap, Math.max(minWait, simStats.B.rawWait));
  simStats.C.wait = Math.min(cap, Math.max(minWait, simStats.C.rawWait));
}}

// ── AI decision log ────────────────────────────────────────────────────────
const LOG_MAX = 7;
const logMessages = [];
let logTimer = 0;

// Mode-aware log pool with realistic messages
const LOG_POOLS = {{
  NORMAL: [
    n => `int_${{n}}: EW demand +${{2+Math.floor(Math.random()*4)}} veh — extending green 3 s`,
    n => `int_${{n}}: NS queue cleared — switching to EW phase`,
    n => `int_${{n}}: cycle balanced, avg wait ${{(8+Math.random()*12).toFixed(1)}} s`,
    n => `int_${{n}}: throughput ${{(18+Math.floor(Math.random()*8))}} veh/min`,
    n => `int_${{n}}: phase sync with int_${{n==='B'?'C':'B'}} — green wave active`,
  ],
  EMERGENCY: [
    n => `int_${{n}}: 🚨 OVERRIDE — EW corridor held green`,
    n => `int_${{n}}: cross-traffic suspended for emergency pass`,
    n => `int_${{n}}: ambulance ETA ${{(2+Math.random()*4).toFixed(0)}} s — holding signal`,
    n => `int_${{n}}: emergency cleared — resuming normal cycle`,
    n => `int_B: center crossing cleared, priority path open`,
  ],
  ACCIDENT: [
    n => `int_${{n}}: ⚠ upstream queue ${{3+Math.floor(Math.random()*6)}} veh — rerouting`,
    n => `int_B: W-entry blocked — diverting to alt path`,
    n => `int_${{n}}: incident detected at t=${{simStats.time.toFixed(0)}} s`,
    n => `int_${{n}}: NS phase extended — absorbing diverted flow`,
    n => `int_${{n}}: queue dissipating — ${{(60+Math.random()*30).toFixed(0)}} s wait`,
  ],
  NIGHT: [
    n => `int_${{n}}: 🌙 demand low — skipping idle EW phase`,
    n => `int_${{n}}: actuated mode: green on demand`,
    n => `int_${{n}}: avg wait ${{(3+Math.random()*8).toFixed(1)}} s — optimal timing`,
    n => `int_${{n}}: ${{1+Math.floor(Math.random()*3)}} veh/min — extending green 8 s`,
    n => `int_${{n}}: night offset sync with corridor`,
  ],
}};

function classifyLogEvent(message) {{
  const m = message.toLowerCase();
  if (m.includes('cleared') || m.includes('optimal') || m.includes('throughput')) {{
    return {{ label:'clear', color:'#22c55e' }};
  }}
  if (m.includes('switch') || m.includes('phase') || m.includes('sync') || m.includes('extending')) {{
    return {{ label:'switch', color:'#22d3ee' }};
  }}
  if (m.includes('queue') || m.includes('blocked') || m.includes('incident') || m.includes('wait') || m.includes('rerout')) {{
    return {{ label:'load', color:'#f97316' }};
  }}
  if (m.includes('emergency') || m.includes('override')) {{
    return {{ label:'priority', color:'#ef4444' }};
  }}
  return {{ label:'info', color:'#a78bfa' }};
}}

function cleanLogMessage(message) {{
  return message.replace(/[🚨⚠️🌙]/g, '').replace(/\\s+/g, ' ').trim();
}}

function renderLog() {{
  const box = document.getElementById('log-entries');
  box.replaceChildren(...logMessages.map(entry => {{
    const meta = entry.meta || classifyLogEvent(entry.message || String(entry));
    const row = document.createElement('div');
    row.className = 'log-entry';
    row.style.setProperty('--log-color', meta.color);

    const time = document.createElement('span');
    time.className = 'log-time';
    time.textContent = 't+' + entry.ts + 's';

    const copy = document.createElement('span');
    copy.className = 'log-copy';
    copy.textContent = cleanLogMessage(entry.message || String(entry));

    row.append(time, copy);
    return row;
  }}));
}}

function maybeLog(dt) {{
  logTimer += dt;
  const interval = MODE==='NIGHT' ? 3.5 : 2.0;
  if (logTimer < interval) return;
  logTimer = 0;
  const ids   = ['A','B','C'];
  const id    = ids[Math.floor(Math.random()*ids.length)];
  const pool  = LOG_POOLS[MODE] || LOG_POOLS.NORMAL;
  const fn    = pool[Math.floor(Math.random()*pool.length)];
  const ts    = simStats.time.toFixed(0);
  const message = fn(id);
  logMessages.unshift({{ ts, message, meta: classifyLogEvent(message) }});
  if (logMessages.length > LOG_MAX) logMessages.pop();
  renderLog();
}}

// ── Vehicle type definitions ────────────────────────────────────────────────
const ROUTE_DEFS = [
  {{ id:'W-E',  weight:4 }},
  {{ id:'E-W',  weight:4 }},
  {{ id:'NA-S', weight:2 }},
  {{ id:'S-NA', weight:2 }},
  {{ id:'SC-N', weight:2 }},
  {{ id:'N-SC', weight:2 }},
];

const TYPE_DEFS = [
  {{ type:'car',       color:'#4a9eff', w:10, h:6,  spd:1.05, weight:6 }},
  {{ type:'car',       color:'#7b8cde', w:10, h:6,  spd:0.95, weight:4 }},
  {{ type:'car',       color:'#56cfb2', w:10, h:6,  spd:1.00, weight:4 }},
  {{ type:'truck',     color:'#8b6914', w:16, h:8,  spd:0.60, weight:2 }},
  {{ type:'moto',      color:'#a78bfa', w:7,  h:4,  spd:1.40, weight:3 }},
  {{ type:'emergency', color:'#ef4444', w:12, h:7,  spd:1.70, weight:1 }},
];

function pickRandom(arr) {{
  const total = arr.reduce((s,a) => s+(a.weight||1), 0);
  let r = Math.random() * total;
  for (const a of arr) {{ r -= (a.weight||1); if (r<=0) return a; }}
  return arr[arr.length-1];
}}

function pickManeuver(isEmergency=false) {{
  if (isEmergency && MODE==='EMERGENCY') return 'straight';
  const r = Math.random();
  if (r < 0.60) return 'straight';
  if (r < 0.80) return 'right';
  return 'left';
}}

// ── PATH HELPERS ─────────────────────────────────────────────────────────────
// Each route has a canonical lane-centre coordinate so all vehicles on the
// same route travel on exactly the same pixel track.

function canonicalY(route, g) {{
  // Default visible lane center for helpers: inner lane of the right-hand carriageway.
  if (route==='W-E') return laneCoordForDir({{x:0,y:g.roadY}}, {{x:1,y:0}}, g, 1).y;
  if (route==='E-W') return laneCoordForDir({{x:0,y:g.roadY}}, {{x:-1,y:0}}, g, 1).y;
  return g.roadY;
}}

function canonicalX(route, g) {{
  // Default visible lane center for helpers: inner lane of the right-hand carriageway.
  if (route==='NA-S') return laneCoordForDir({{x:g.axA,y:g.roadY}}, {{x:0,y:1}}, g, 1).x;
  if (route==='S-NA') return laneCoordForDir({{x:g.axA,y:g.roadY}}, {{x:0,y:-1}}, g, 1).x;
  if (route==='SC-N') return laneCoordForDir({{x:g.axC,y:g.roadY}}, {{x:0,y:-1}}, g, 1).x;
  if (route==='N-SC') return laneCoordForDir({{x:g.axC,y:g.roadY}}, {{x:0,y:1}}, g, 1).x;
  return 0;
}}

function routeDirection(route) {{
  return {{
    'W-E':  {{x:1,  y:0}},
    'E-W':  {{x:-1, y:0}},
    'NA-S': {{x:0,  y:1}},
    'S-NA': {{x:0,  y:-1}},
    'N-SC': {{x:0,  y:1}},
    'SC-N': {{x:0,  y:-1}},
  }}[route] || {{x:1,y:0}};
}}

function turnDirection(dir, maneuver) {{
  if (maneuver === 'right') return {{x:-dir.y, y:dir.x}};
  if (maneuver === 'left')  return {{x:dir.y, y:-dir.x}};
  return {{...dir}};
}}

function rightNormal(dir) {{
  return {{x:-dir.y, y:dir.x}};
}}

function laneForManeuver(maneuver, isEmergency=false) {{
  if (isEmergency) return 1;
  if (maneuver === 'right') return 2;  // outer/rightmost lane
  if (maneuver === 'left') return 1;   // inner/median-side lane
  return Math.random() < 0.5 ? 1 : 2;  // straight can use either lane
}}

function outboundLaneForManeuver(maneuver, inboundLane) {{
  if (maneuver === 'right') return 2;
  if (maneuver === 'left') return 1;
  return inboundLane;
}}

function laneOffset(laneIndex, g) {{
  return g.laneW * (laneIndex === 2 ? 1.5 : 0.5);
}}

function routeTurnNode(route, g) {{
  if (route === 'W-E' || route === 'E-W') return {{key:'B', x:g.axB, y:g.roadY}};
  if (route === 'NA-S' || route === 'S-NA') return {{key:'A', x:g.axA, y:g.roadY}};
  return {{key:'C', x:g.axC, y:g.roadY}};
}}

function laneIdForDir(nodeKey, dir, laneIndex=1) {{
  if (Math.abs(dir.x) > 0) return `H:${{dir.x > 0 ? 'E' : 'W'}}:L${{laneIndex}}`;
  return `V:${{nodeKey}}:${{dir.y > 0 ? 'S' : 'N'}}:L${{laneIndex}}`;
}}

function laneCoordForDir(node, dir, g, laneIndex=1) {{
  const rn = rightNormal(dir);
  const off = laneOffset(laneIndex, g);
  return {{ x: node.x + rn.x * off, y: node.y + rn.y * off }};
}}

function routeStart(route, g, startOffset=0, laneIndex=1) {{
  const dir = routeDirection(route);
  const node = routeTurnNode(route, g);
  const lane = laneCoordForDir(node, dir, g, laneIndex);
  const pad = g.laneW * 2 + startOffset;
  switch(route) {{
    case 'W-E':  return {{x:g.mapLeft - pad,  y:lane.y}};
    case 'E-W':  return {{x:g.mapRight + pad, y:lane.y}};
    case 'NA-S':
    case 'N-SC': return {{x:lane.x, y:g.mapTop - pad}};
    case 'S-NA':
    case 'SC-N': return {{x:lane.x, y:g.mapBottom + pad}};
    default:     return {{x:g.mapLeft - pad, y:lane.y}};
  }}
}}

function laneEndForDir(node, dir, g, laneIndex=1) {{
  const lane = laneCoordForDir(node, dir, g, laneIndex);
  if (dir.x > 0) return {{x:g.mapRight + g.laneW*2, y:lane.y}};
  if (dir.x < 0) return {{x:g.mapLeft - g.laneW*2, y:lane.y}};
  if (dir.y > 0) return {{x:lane.x, y:g.mapBottom + g.laneW*2}};
  return {{x:lane.x, y:g.mapTop - g.laneW*2}};
}}

function dist(a,b) {{
  return Math.hypot(b.x-a.x, b.y-a.y);
}}

function lineSegment(p0,p1,laneId) {{
  return {{type:'line', p0, p1, laneId, len:Math.max(1, dist(p0,p1))}};
}}

function quadPoint(p0,p1,p2,t) {{
  const u = 1-t;
  return {{
    x: u*u*p0.x + 2*u*t*p1.x + t*t*p2.x,
    y: u*u*p0.y + 2*u*t*p1.y + t*t*p2.y,
  }};
}}

function quadTangent(p0,p1,p2,t) {{
  const x = 2*(1-t)*(p1.x-p0.x) + 2*t*(p2.x-p1.x);
  const y = 2*(1-t)*(p1.y-p0.y) + 2*t*(p2.y-p1.y);
  const mag = Math.hypot(x,y) || 1;
  return {{x:x/mag, y:y/mag}};
}}

function estimateQuadLength(p0,p1,p2) {{
  let len = 0, prev = p0;
  for (let i=1; i<=12; i++) {{
    const pt = quadPoint(p0,p1,p2,i/12);
    len += dist(prev,pt);
    prev = pt;
  }}
  return Math.max(1,len);
}}

function curveSegment(p0,p1,p2,laneId) {{
  return {{type:'curve', p0, p1, p2, laneId, len:estimateQuadLength(p0,p1,p2)}};
}}

function segmentPoint(seg,t) {{
  if (seg.type === 'curve') return quadPoint(seg.p0,seg.p1,seg.p2,t);
  return {{x:seg.p0.x + (seg.p1.x-seg.p0.x)*t, y:seg.p0.y + (seg.p1.y-seg.p0.y)*t}};
}}

function segmentTangent(seg,t) {{
  if (seg.type === 'curve') return quadTangent(seg.p0,seg.p1,seg.p2,t);
  const dx = seg.p1.x-seg.p0.x, dy = seg.p1.y-seg.p0.y;
  const mag = Math.hypot(dx,dy) || 1;
  return {{x:dx/mag, y:dy/mag}};
}}

function gatePoint(node, dir, axis, g, laneIndex=1) {{
  const lane = laneCoordForDir(node, dir, g, laneIndex);
  const off = g.laneW * 3.0;
  if (axis === 'ew') return {{x:node.x - Math.sign(dir.x)*off, y:lane.y}};
  return {{x:lane.x, y:node.y - Math.sign(dir.y)*off}};
}}

function gateTOnLine(seg, pt) {{
  if (seg.type !== 'line') return null;
  const dx = seg.p1.x-seg.p0.x, dy = seg.p1.y-seg.p0.y;
  const denom = dx*dx + dy*dy;
  if (denom <= 0) return null;
  const t = ((pt.x-seg.p0.x)*dx + (pt.y-seg.p0.y)*dy) / denom;
  return t >= 0 && t <= 1 ? t : null;
}}

function addGate(gates, segments, segIdx, node, dir, axis, g, laneIndex=1, blockLaneId=null) {{
  const pt = gatePoint(node, dir, axis, g, laneIndex);
  const t = gateTOnLine(segments[segIdx], pt);
  if (t === null) return;
  gates.push({{segIdx, t, intKey:node.key, axis, node, blockLaneId}});
}}

function axisForDir(dir) {{
  return Math.abs(dir.x) > 0 ? 'ew' : 'ns';
}}

function turnWaypoints(node, dir, outDir, g, inLaneIndex, outLaneIndex, maneuver) {{
  const axis = axisForDir(dir);
  const stopLine = gatePoint(node, dir, axis, g, inLaneIndex);
  const entryLen = g.laneW * (maneuver === 'right' ? 1.35 : 2.05);
  const exitLen = g.laneW * (maneuver === 'right' ? 1.35 : 2.05);
  const approachPoint = {{
    x: stopLine.x + dir.x * entryLen,
    y: stopLine.y + dir.y * entryLen,
  }};
  const outLaneCoord = laneCoordForDir(node, outDir, g, outLaneIndex);
  const exitLaneAlignmentPoint = {{
    x: outLaneCoord.x + outDir.x * exitLen,
    y: outLaneCoord.y + outDir.y * exitLen,
  }};
  const cornerPivotPoint = Math.abs(dir.x) > 0
    ? {{x: exitLaneAlignmentPoint.x, y: approachPoint.y}}
    : {{x: approachPoint.x, y: exitLaneAlignmentPoint.y}};
  return {{
    approachPoint,
    stopLinePoint: stopLine,
    cornerPivotPoint,
    exitLaneAlignmentPoint,
    exitPoint: laneEndForDir(node, outDir, g, outLaneIndex),
  }};
}}

function buildVehiclePath(route, maneuver, g, startOffset=0, inboundLane=1, outboundLane=null) {{
  const dir = routeDirection(route);
  const node = routeTurnNode(route, g);
  const axis = axisForDir(dir);
  const inLaneIndex = inboundLane;
  const outLaneIndex = outboundLane ?? outboundLaneForManeuver(maneuver, inLaneIndex);
  const start = routeStart(route, g, startOffset, inLaneIndex);
  const inLane = laneIdForDir(node.key, dir, inLaneIndex);
  const gates = [];
  const segments = [];

  if (maneuver === 'straight') {{
    const endNode = {{key: node.key, x: node.x, y: node.y}};
    const end = laneEndForDir(endNode, dir, g, inLaneIndex);
    segments.push(lineSegment(start, end, inLane));

    if (route === 'W-E') {{
      addGate(gates, segments, 0, {{key:'A',x:g.axA,y:g.roadY}}, dir, 'ew', g, inLaneIndex, inLane);
      addGate(gates, segments, 0, {{key:'B',x:g.axB,y:g.roadY}}, dir, 'ew', g, inLaneIndex, inLane);
      addGate(gates, segments, 0, {{key:'C',x:g.axC,y:g.roadY}}, dir, 'ew', g, inLaneIndex, inLane);
    }} else if (route === 'E-W') {{
      addGate(gates, segments, 0, {{key:'C',x:g.axC,y:g.roadY}}, dir, 'ew', g, inLaneIndex, inLane);
      addGate(gates, segments, 0, {{key:'B',x:g.axB,y:g.roadY}}, dir, 'ew', g, inLaneIndex, inLane);
      addGate(gates, segments, 0, {{key:'A',x:g.axA,y:g.roadY}}, dir, 'ew', g, inLaneIndex, inLane);
    }} else {{
      addGate(gates, segments, 0, node, dir, axis, g, inLaneIndex, inLane);
    }}
    return {{segments, gates}};
  }}

  const outDir = turnDirection(dir, maneuver);
  const outLane = laneIdForDir(node.key, outDir, outLaneIndex);
  const turn = turnWaypoints(node, dir, outDir, g, inLaneIndex, outLaneIndex, maneuver);

  segments.push(lineSegment(start, turn.stopLinePoint, inLane));
  if (route === 'W-E') {{
    addGate(gates, segments, 0, {{key:'A',x:g.axA,y:g.roadY}}, dir, 'ew', g, inLaneIndex, inLane);
    addGate(gates, segments, 0, node, dir, axis, g, inLaneIndex, outLane);
  }} else if (route === 'E-W') {{
    addGate(gates, segments, 0, {{key:'C',x:g.axC,y:g.roadY}}, dir, 'ew', g, inLaneIndex, inLane);
    addGate(gates, segments, 0, node, dir, axis, g, inLaneIndex, outLane);
  }} else {{
    addGate(gates, segments, 0, node, dir, axis, g, inLaneIndex, outLane);
  }}
  segments.push(lineSegment(turn.stopLinePoint, turn.approachPoint, inLane));
  segments.push(curveSegment(
    turn.approachPoint,
    turn.cornerPivotPoint,
    turn.exitLaneAlignmentPoint,
    `${{inLane}}>corner:${{maneuver}}:${{node.key}}`
  ));
  segments.push(lineSegment(turn.exitLaneAlignmentPoint, turn.exitPoint, outLane));
  return {{segments, gates}};
}}

// ── SPACING HELPERS ───────────────────────────────────────────────────────────
// Minimum following distance = vehicle length + safety buffer
const MIN_FOLLOW_GAP = 25;   // px below which target speed = 0
const DECEL_DIST     = 72;   // px — begin decelerating when gap < this

// Each signalized junction admits one committed vehicle movement at a time.
// This keeps the schematic animation readable without a heavyweight simulator.
const intersectionLocks = {{
  A: {{ occupiedBy:null, axis:null, route:null, maneuver:null }},
  B: {{ occupiedBy:null, axis:null, route:null, maneuver:null }},
  C: {{ occupiedBy:null, axis:null, route:null, maneuver:null }},
}};

/**
 * gapAhead: distance to nearest vehicle in the same lane/segment direction.
 * Lane IDs make car-following cheap while preventing same-lane overlap.
 */
function gapAhead(v, allVehicles) {{
  let minGap = Infinity;
  const seg = v.currentSegment();
  if (!seg) return minGap;
  const tangent = segmentTangent(seg, v.segT);
  for (const other of allVehicles) {{
    if (other === v || other.done) continue;
    if (other.currentLaneId() !== v.currentLaneId()) continue;

    const dx = other.x - v.x;
    const dy = other.y - v.y;
    const ahead = dx * tangent.x + dy * tangent.y;
    if (ahead <= 0) continue;

    const lateral = Math.abs(dx * tangent.y - dy * tangent.x);
    if (lateral > 18) continue;

    const dist = Math.sqrt(dx*dx + dy*dy);
    if (dist < minGap) minGap = dist;
  }}
  return minGap;
}}

function lockForIntersection(key) {{
  return intersectionLocks[key] || null;
}}

function vehicleHasIntersectionLock(v, key) {{
  return Boolean(v.intersectionLocks && v.intersectionLocks.has(key));
}}

function acquireIntersectionLock(v, gate) {{
  const lock = lockForIntersection(gate.intKey);
  if (!lock) return true;
  if (lock.occupiedBy !== null && lock.occupiedBy !== v.id) return false;
  lock.occupiedBy = v.id;
  lock.axis = gate.axis;
  lock.route = v.route;
  lock.maneuver = v.maneuver;
  if (v.intersectionLocks) v.intersectionLocks.set(gate.intKey, gate);
  return true;
}}

function releaseIntersectionLock(v, key) {{
  const lock = lockForIntersection(key);
  if (lock && lock.occupiedBy === v.id) {{
    lock.occupiedBy = null;
    lock.axis = null;
    lock.route = null;
    lock.maneuver = null;
  }}
  if (v.intersectionLocks) v.intersectionLocks.delete(key);
}}

function releaseAllIntersectionLocks(v) {{
  if (!v.intersectionLocks) return;
  Array.from(v.intersectionLocks.keys()).forEach(key => releaseIntersectionLock(v, key));
}}

function hasPassedGate(v, gate) {{
  if (v.segIdx > gate.segIdx) return true;
  if (v.segIdx < gate.segIdx) return false;
  return v.segT >= gate.t;
}}

function releasePassedIntersectionLocks(v, g) {{
  if (!v.intersectionLocks || v.intersectionLocks.size === 0) return;
  const clearDistance = g.laneW * 3.45;
  Array.from(v.intersectionLocks.entries()).forEach(([key, gate]) => {{
    if (v.done) {{
      releaseIntersectionLock(v, key);
      return;
    }}
    const awayFromCenter = Math.hypot(v.x - gate.node.x, v.y - gate.node.y);
    if (hasPassedGate(v, gate) && awayFromCenter > clearDistance) {{
      releaseIntersectionLock(v, key);
    }}
  }});
}}

function nextUpcomingGate(v) {{
  const seg = v.currentSegment();
  if (!seg) return null;
  let best = null;
  for (const gate of v.gates) {{
    if (gate.segIdx !== v.segIdx || gate.t <= v.segT) continue;
    const distance = (gate.t - v.segT) * seg.len;
    if (!best || distance < best.distance) best = {{ gate, distance }};
  }}
  return best;
}}

function conflictZoneOccupied(v, gate, g) {{
  const radius = g.laneW * 2.45;
  return vehicles.some(o => {{
    if (o === v || o.done) return false;
    return Math.abs(o.x - gate.node.x) < radius && Math.abs(o.y - gate.node.y) < radius;
  }});
}}

function exitLaneBlocked(v, gate, g) {{
  if (!gate.blockLaneId) return false;
  const clearDistance = g.laneW * 4.9;
  return vehicles.some(o => {{
    if (o === v || o.done) return false;
    if (o.currentLaneId() !== gate.blockLaneId) return false;
    return Math.hypot(o.x - gate.node.x, o.y - gate.node.y) < clearDistance;
  }});
}}

/**
 * Vehicles stop at red signal gates and also avoid entering an occupied
 * intersection box.
 */
function intersectionBlocked(v, gate, g) {{
  const lock = lockForIntersection(gate.intKey);
  const lockedByOther = lock && lock.occupiedBy !== null && lock.occupiedBy !== v.id;
  return lockedByOther || conflictZoneOccupied(v, gate, g) || exitLaneBlocked(v, gate, g);
}}

function reserveUpcomingIntersection(v, g) {{
  const upcoming = nextUpcomingGate(v);
  if (!upcoming) return;
  const {{ gate, distance }} = upcoming;
  if (vehicleHasIntersectionLock(v, gate.intKey)) return;
  if (distance > Math.max(18, g.laneW * 0.95)) return;
  if (!tlAllowsEntry(TL[gate.intKey], gate.axis)) return;
  if (intersectionBlocked(v, gate, g)) return;
  acquireIntersectionLock(v, gate);
}}

function distToStopLine(v, g) {{
  const seg = v.currentSegment();
  if (!seg) return Infinity;
  let minStop = Infinity;
  v.currentGate = null;
  for (const gate of v.gates) {{
    if (gate.segIdx !== v.segIdx || gate.t <= v.segT) continue;
    const distToGate = (gate.t - v.segT) * seg.len;
    const entered = hasPassedGate(v, gate);
    let hasLock = vehicleHasIntersectionLock(v, gate.intKey);
    const green = tlAllowsEntry(TL[gate.intKey], gate.axis);
    if (!green && hasLock && !entered) {{
      releaseIntersectionLock(v, gate.intKey);
      hasLock = false;
    }}
    const stopForSignal = !green && !entered;
    const blocked = !hasLock && intersectionBlocked(v, gate, g);
    if ((stopForSignal || blocked) && distToGate < minStop) {{
      minStop = distToGate;
      v.currentGate = gate;
    }}
  }}

  // ACCIDENT: blockage acts as permanent stop line in W-E lane.
  if (MODE==='ACCIDENT' && v.route === 'W-E' && v.currentLaneId().startsWith('H:E')) {{
    const accX = g.axB - g.rbR * 2.3;
    if (v.x < accX) minStop = Math.min(minStop, Math.max(0, accX - v.x - g.laneW*0.5));
  }}
  return minStop;
}}

/**
 * targetSpeed: desired speed based on gap to leader and distance to stop line.
 * Returns a value in [0 .. baseSpd].
 */
function targetSpeed(v, g, allVehicles) {{
  // Nearest hard constraint (stop line, occupied intersection, or gap)
  const gap  = gapAhead(v, allVehicles);
  const stop = distToStopLine(v, g);
  const dist = Math.min(gap - v.vw, stop);  // subtract own length from gap

  if (dist <= 2)           return 0;
  if (dist < MIN_FOLLOW_GAP) return 0;
  if (dist < DECEL_DIST)   return v.baseSpd * ((dist - MIN_FOLLOW_GAP) / (DECEL_DIST - MIN_FOLLOW_GAP));
  return v.baseSpd;
}}

// ── ROUNDABOUT ENTRY GATE ─────────────────────────────────────────────────────
// Prevents vehicles from entering when another vehicle is too close to the
// entry point on the orbit. Returns true if entry is safe.
const MIN_ENTRY_GAP_RAD = 0.75;  // radians (~43°) — gap needed before entry

function canEnterRoundabout(v) {{
  const rbVehicles = vehicles.filter(o => o !== v && o.phase === 'roundabout');
  if (rbVehicles.length === 0) return true;

  const entryAng = v.route === 'W-E' ? Math.PI : 0;
  const TWO_PI   = Math.PI * 2;
  const norm = a => ((a % TWO_PI) + TWO_PI) % TWO_PI;

  for (const rv of rbVehicles) {{
    const myN    = norm(entryAng);
    const otherN = norm(rv.rbAngle);
    let diff     = Math.abs(myN - otherN);
    if (diff > Math.PI) diff = TWO_PI - diff;
    if (diff < MIN_ENTRY_GAP_RAD) return false;
  }}
  return true;
}}

/**
 * rbGapAhead: angular gap (radians) to the nearest vehicle clockwise ahead
 * in the roundabout. Used to slow down orbiting vehicles that are catching up.
 */
function rbGapAhead(v) {{
  const TWO_PI = Math.PI * 2;
  const norm = a => ((a % TWO_PI) + TWO_PI) % TWO_PI;
  let minGap = Infinity;
  const myN = norm(v.rbAngle);

  for (const other of vehicles) {{
    if (other === v || other.phase !== 'roundabout') continue;
    const otherN = norm(other.rbAngle);
    // Angular gap clockwise ahead: how far is `other` ahead of `v`?
    // Since angle increases = clockwise, "ahead" means otherN > myN (mod 2π)
    let gap = otherN - myN;
    if (gap < 0) gap += TWO_PI;
    // Only consider vehicles within half the circle ahead
    if (gap < Math.PI && gap < minGap) minGap = gap;
  }}
  return minGap;
}}

function vehicleVisualState(v) {{
  if (v.isEmergency) {{
    return {{ body:'#ef4444', accent:'#ffffff', glow:'#ef4444' }};
  }}
  const ratio = v.baseSpd > 0 ? v.spd / v.baseSpd : 0;
  if (ratio > 0.66) {{
    return {{ body:'#22c55e', accent:'#bbf7d0', glow:'#22c55e' }};
  }}
  if (ratio > 0.22) {{
    return {{ body:'#f59e0b', accent:'#ffedd5', glow:'#f59e0b' }};
  }}
  return {{ body:'#ef4444', accent:'#fecaca', glow:'#ef4444' }};
}}

// ── Vehicle class ─────────────────────────────────────────────────────────────
let vehicleIdCounter = 0;

class Vehicle {{
  constructor(routeDef, typeDef, g, startOffset=0) {{
    this.id           = vehicleIdCounter++;
    this.route        = routeDef.id;
    this.maneuver     = routeDef.maneuver || pickManeuver(typeDef.type === 'emergency');
    this.laneIndex    = routeDef.laneIndex || laneForManeuver(this.maneuver, typeDef.type === 'emergency');
    this.outLaneIndex = routeDef.outLaneIndex || outboundLaneForManeuver(this.maneuver, this.laneIndex);
    this.type         = typeDef.type;
    this.color        = typeDef.color;
    this.vw           = typeDef.w;
    this.vh           = typeDef.h;
    this.baseSpd      = typeDef.spd * (MODE==='NIGHT' ? 0.75 : 1.0);
    this.spd          = this.baseSpd * 0.5;  // start slow to prevent initial overlap
    this.phase        = 'travel';
    this.done         = false;
    this.flashTimer   = 0;
    this.isEmergency  = (this.type === 'emergency');
    this.startOffset  = startOffset;  // initial position offset along route
    this.segments     = [];
    this.gates        = [];
    this.segIdx       = 0;
    this.segT         = 0;
    this.angle        = 0;
    this.currentGate  = null;
    this.intersectionLocks = new Map();
    this._initPath(g);
  }}

  _initPath(g) {{
    releaseAllIntersectionLocks(this);
    const path = buildVehiclePath(this.route, this.maneuver, g, this.startOffset, this.laneIndex, this.outLaneIndex);
    this.segments = path.segments;
    this.gates = path.gates;
    this.segIdx = 0;
    this.segT = 0;
    this.done = this.segments.length === 0;
    this._applySegmentPosition();
  }}

  resetPath() {{
    const g = geo();
    this._initPath(g);
  }}

  currentSegment() {{
    return this.segments[this.segIdx] || null;
  }}

  currentLaneId() {{
    const seg = this.currentSegment();
    return seg ? seg.laneId : '';
  }}

  _applySegmentPosition() {{
    const seg = this.currentSegment();
    if (!seg) {{ this.done = true; return; }}
    const p = segmentPoint(seg, this.segT);
    const t = segmentTangent(seg, this.segT);
    this.x = p.x; this.y = p.y;
    this.dx = t.x; this.dy = t.y;
    this.angle = Math.atan2(t.y, t.x);
  }}

  _advanceBy(distance) {{
    let remaining = distance;
    while (remaining > 0 && !this.done) {{
      const seg = this.currentSegment();
      if (!seg) {{ this.done = true; releaseAllIntersectionLocks(this); break; }}
      const segRemaining = (1 - this.segT) * seg.len;
      if (remaining < segRemaining) {{
        this.segT += remaining / seg.len;
        remaining = 0;
      }} else {{
        remaining -= segRemaining;
        this.segIdx += 1;
        this.segT = 0;
        if (this.segIdx >= this.segments.length) {{
          this.done = true;
          releaseAllIntersectionLocks(this);
          break;
        }}
      }}
    }}
    if (!this.done) this._applySegmentPosition();
  }}

  setRoutePosition(x,y) {{
    let best = {{idx:0, t:0, d:Infinity}};
    this.segments.forEach((seg, idx) => {{
      if (seg.type !== 'line') return;
      const dx = seg.p1.x-seg.p0.x, dy = seg.p1.y-seg.p0.y;
      const denom = dx*dx + dy*dy;
      if (denom <= 0) return;
      const t = Math.max(0, Math.min(1, ((x-seg.p0.x)*dx + (y-seg.p0.y)*dy) / denom));
      const p = segmentPoint(seg,t);
      const d = Math.hypot(p.x-x,p.y-y);
      if (d < best.d) best = {{idx,t,d}};
    }});
    this.segIdx = best.idx;
    this.segT = best.t;
    this._applySegmentPosition();
  }}

  // ── update ────────────────────────────────────────────────────────────────
  update(dt, g) {{
    if (this.done) return;
    this.flashTimer += dt;
    releasePassedIntersectionLocks(this, g);
    reserveUpcomingIntersection(this, g);

    // ── Straight-line travel ──────────────────────────────────────────────
    // Smooth car-following speed control
    const tSpd = targetSpeed(this, g, vehicles);
    const ACCEL = 2.8, DECEL = 6.0;
    if (tSpd < this.spd) {{
      this.spd = Math.max(tSpd, this.spd - dt * DECEL);
    }} else {{
      this.spd = Math.min(tSpd, this.spd + dt * ACCEL);
    }}

    // Emergency: yield to ambulance — all traffic slows; same-lane vehicles
    // directly ahead of the ambulance stop completely to clear the path.
    if (!this.isEmergency && MODE==='EMERGENCY') {{
      const amb = vehicles.find(v => v.isEmergency && !v.done);
      if (amb) {{
        this.spd = Math.min(this.spd, this.baseSpd * 0.28);
        // Same route + travel phase + vehicle is ahead of ambulance → full stop
        if (this.route === amb.route &&
            this.phase === 'travel' && amb.phase === 'travel') {{
          const ahead = (amb.dx > 0 && this.x > amb.x) ||
                        (amb.dx < 0 && this.x < amb.x);
          if (ahead && Math.abs(this.x - amb.x) < 240) this.spd = 0;
        }}
      }}
    }}

    this._advanceBy(this.spd * 60 * dt);
    releasePassedIntersectionLocks(this, g);
  }}

  // ── draw ──────────────────────────────────────────────────────────────────
  draw(ctx, g) {{
    if (this.done) return;
    ctx.save();
    ctx.translate(this.x, this.y);

    ctx.rotate(this.angle);

    const visual = vehicleVisualState(this);
    const bodyW = Math.max(this.vw * 1.42, this.type==='truck' ? 22 : (this.type==='moto' ? 12 : 15));
    const bodyH = Math.max(this.vh * 1.45, this.type==='moto' ? 7 : 9);

    ctx.shadowColor = visual.glow;
    ctx.shadowBlur = this.isEmergency ? (Math.sin(this.flashTimer * 10) > 0 ? 18 : 10) : 7;

    // Vehicle body: compact pill with direction marker.
    ctx.fillStyle = visual.body;
    ctx.beginPath();
    ctx.roundRect(-bodyW/2, -bodyH/2, bodyW, bodyH, bodyH/2);
    ctx.fill();
    ctx.shadowBlur = 0;

    ctx.strokeStyle = 'rgba(2,6,23,0.78)';
    ctx.lineWidth = 1.3;
    ctx.stroke();

    // Direction nose.
    ctx.fillStyle = 'rgba(255,255,255,0.82)';
    ctx.beginPath();
    ctx.moveTo(bodyW/2 - 2.5, 0);
    ctx.lineTo(bodyW/2 - 7.2, -bodyH*0.27);
    ctx.lineTo(bodyW/2 - 7.2, bodyH*0.27);
    ctx.closePath();
    ctx.fill();

    // Windscreen highlight
    ctx.fillStyle = visual.accent;
    ctx.globalAlpha = 0.46;
    ctx.beginPath();
    ctx.roundRect(bodyW*0.03, -bodyH*0.34, bodyW*0.22, bodyH*0.68, 2);
    ctx.fill();
    ctx.globalAlpha = 1;

    // Emergency cross
    if (this.isEmergency) {{
      ctx.fillStyle = '#fff';
      ctx.fillRect(-2, -bodyH*0.42, 4, bodyH*0.84);
      ctx.fillRect(-bodyW*0.28, -2, bodyW*0.56, 4);
    }}

    ctx.restore();
  }}
}}

// ── Vehicle pool & spawning ───────────────────────────────────────────────────
const vehicles = [];

const MAX_VEHICLES = {{ NORMAL:30, EMERGENCY:26, ACCIDENT:28, NIGHT:16 }}[MODE] || 28;
const SPAWN_INTERVAL = {{ NORMAL:0.85, EMERGENCY:1.2, ACCIDENT:1.0, NIGHT:2.2 }}[MODE] || 1.0;
let spawnTimer = 0;

/**
 * spawnBlocked: returns true if the spawn point for the given route is
 * occupied by an existing vehicle (prevents back-to-back spawning overlap).
 */
function spawnBlocked(routeDef, g) {{
  const CLEAR = 28;
  const rid = typeof routeDef === 'string' ? routeDef : routeDef.id;
  const laneIndex = typeof routeDef === 'string' ? 1 : (routeDef.laneIndex || 1);
  const start = routeStart(rid, g, 0, laneIndex);
  const sx = start.x, sy = start.y;
  const spawnLane = laneIdForDir(routeTurnNode(rid, g).key, routeDirection(rid), laneIndex);
  return vehicles.some(v => !v.done && v.currentLaneId() === spawnLane && Math.hypot(v.x-sx, v.y-sy) < CLEAR);
}}

function makeRouteDef(routeId, typeDef, preferredManeuver=null, preferredLane=null) {{
  const maneuver = preferredManeuver || pickManeuver(typeDef.type === 'emergency');
  const laneIndex = preferredLane || laneForManeuver(maneuver, typeDef.type === 'emergency');
  return {{
    id: routeId,
    maneuver,
    laneIndex,
    outLaneIndex: outboundLaneForManeuver(maneuver, laneIndex),
  }};
}}

function spawnVehicle() {{
  const g = geo();

  // EMERGENCY: ensure exactly one ambulance exists, spawn it first
  if (MODE==='EMERGENCY' && !vehicles.some(v=>v.isEmergency)) {{
    const td = TYPE_DEFS.find(t=>t.type==='emergency');
    const emergencyRoute = makeRouteDef('W-E', td, 'straight', 1);
    if (!spawnBlocked(emergencyRoute, g)) {{
      vehicles.push(new Vehicle(emergencyRoute, td, g, 0));
    }}
    return;
  }}

  const routeBase = pickRandom(ROUTE_DEFS);
  const typeDef  = pickRandom(TYPE_DEFS.filter(t => t.type !== 'emergency'));
  const routeDef = makeRouteDef(routeBase.id, typeDef);
  if (spawnBlocked(routeDef, g)) return;  // entry point occupied — skip

  vehicles.push(new Vehicle(routeDef, typeDef, g, 0));
}}

// Pre-populate with staggered starting positions so vehicles don't stack
(function prepopulate() {{
  const g   = geo();
  const gap = 55;   // px between pre-placed vehicles on same route
  const routes = ['W-E','E-W','NA-S','S-NA','SC-N','N-SC'];

  routes.forEach(rid => {{
    const mainRoad = (rid==='W-E' || rid==='E-W');
    const base  = mainRoad ? 4 : 2;
    // Night mode starts sparser; other modes use full base count
    const count = MODE === 'NIGHT' ? Math.max(1, Math.floor(base * 0.5)) : base;
    for (let i=0; i<count; i++) {{
      const tDef  = pickRandom(TYPE_DEFS.filter(t=>t.type!=='emergency'));
      vehicles.push(new Vehicle(makeRouteDef(rid, tDef), tDef, g, i * gap));
    }}
  }});

  // EMERGENCY: always seed with an ambulance well behind so it has room to accelerate
  if (MODE==='EMERGENCY') {{
    const td = TYPE_DEFS.find(t=>t.type==='emergency');
    vehicles.push(new Vehicle(makeRouteDef('W-E', td, 'straight', 1), td, g, gap * 7));
  }}

  // ACCIDENT: pre-queue several W-E vehicles behind the blockage so the queue
  // is already visible from the start of the simulation.
  if (MODE==='ACCIDENT') {{
    const accX = g.axB - g.rbR * 2.3;
    for (let i=0; i<4; i++) {{
      const tDef2 = pickRandom(TYPE_DEFS.filter(t=>t.type!=='emergency'));
      const v2 = new Vehicle(makeRouteDef('W-E', tDef2, 'straight', 1), tDef2, g, 0);
      v2.setRoutePosition(accX - 32 - i * 32, canonicalY('W-E', g));   // queue behind accident stop line
      v2.spd = 0;
      vehicles.push(v2);
    }}
  }}
}})();

// ── Drawing helpers ───────────────────────────────────────────────────────────
function drawRoad(x1,y1,x2,y2,laneW,color='#1a1a2e',edge='rgba(226,232,240,0.12)',glow=null) {{
  const ang = Math.atan2(y2-y1, x2-x1);
  const px  = Math.sin(ang)*laneW*2;
  const py  = Math.cos(ang)*laneW*2;
  ctx.save();
  if (glow) {{
    ctx.shadowColor = glow;
    ctx.shadowBlur = 16;
  }}
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.moveTo(x1-px,y1+py); ctx.lineTo(x2-px,y2+py);
  ctx.lineTo(x2+px,y2-py); ctx.lineTo(x1+px,y1-py);
  ctx.closePath(); ctx.fill();
  ctx.shadowBlur = 0;
  ctx.strokeStyle = edge;
  ctx.lineWidth = Math.max(1.25, laneW*0.08);
  ctx.stroke();
  ctx.restore();
}}

function drawDash(x1,y1,x2,y2,color='rgba(226,232,240,0.28)',width=1.7,dash=[14,12]) {{
  ctx.save();
  ctx.setLineDash(dash);
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.lineCap = 'round';
  ctx.beginPath(); ctx.moveTo(x1,y1); ctx.lineTo(x2,y2); ctx.stroke();
  ctx.restore();
}}

function drawTLDot(x,y,color) {{
  const active = color==='#22c55e' || color==='#ef4444';
  const pulse = active ? 0.72 + Math.sin(simStats.time*5.2) * 0.28 : 0.75;
  const r = 8.4;
  ctx.save();
  ctx.beginPath(); ctx.arc(x,y,r+4,0,Math.PI*2);
  ctx.fillStyle = 'rgba(2,6,23,0.92)';
  ctx.fill();
  ctx.strokeStyle = 'rgba(148,163,184,0.24)';
  ctx.lineWidth = 1;
  ctx.stroke();
  if (active) {{
    ctx.shadowBlur = (color==='#22c55e' ? 19 : 13) * pulse;
    ctx.shadowColor = color;
  }}
  ctx.beginPath(); ctx.arc(x,y,r,0,Math.PI*2);
  ctx.fillStyle  = color;
  ctx.fill();
  ctx.shadowBlur = 0;
  ctx.strokeStyle = 'rgba(255,255,255,0.38)';
  ctx.lineWidth = 1.2;
  ctx.stroke();
  ctx.beginPath(); ctx.arc(x-r*0.28,y-r*0.28,r*0.22,0,Math.PI*2);
  ctx.fillStyle = 'rgba(255,255,255,0.72)';
  ctx.fill();
  ctx.restore();
}}

function drawArrow(x,y,angle,color,len=16) {{
  ctx.save(); ctx.translate(x,y); ctx.rotate(angle);
  ctx.strokeStyle=color; ctx.lineWidth=2;
  ctx.beginPath();
  ctx.moveTo(-len/2,0); ctx.lineTo(len/2,0);
  ctx.moveTo(len/2-5,-4); ctx.lineTo(len/2,0); ctx.lineTo(len/2-5,4);
  ctx.stroke(); ctx.restore();
}}

function drawStopLine(x1,y1,x2,y2,width=3) {{
  ctx.save();
  ctx.setLineDash([]);
  ctx.lineCap='butt';
  ctx.strokeStyle='rgba(248,250,252,0.56)';
  ctx.lineWidth=width;
  ctx.beginPath();
  ctx.moveTo(x1,y1);
  ctx.lineTo(x2,y2);
  ctx.stroke();
  ctx.restore();
}}

function drawStraightArrow(x,y,rotation,scale) {{
  const len = scale;
  const head = len * 0.22;
  ctx.save();
  ctx.translate(x,y);
  ctx.rotate(rotation);
  ctx.globalAlpha = 0.76;
  ctx.strokeStyle='rgba(248,250,252,0.92)';
  ctx.fillStyle='rgba(248,250,252,0.92)';
  ctx.lineWidth=Math.max(2.4, len * 0.09);
  ctx.lineCap='round';
  ctx.lineJoin='round';
  ctx.beginPath();
  ctx.moveTo(-len*0.45, 0);
  ctx.lineTo(len*0.28, 0);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(len*0.44, 0);
  ctx.lineTo(len*0.22, -head);
  ctx.lineTo(len*0.22, head);
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}}

function drawTurnArrow(x,y,rotation,direction='right',scale) {{
  const len = scale;
  const sign = direction === 'left' ? -1 : 1;
  const head = len * 0.18;
  const tipY = sign * len * 0.42;
  ctx.save();
  ctx.translate(x,y);
  ctx.rotate(rotation);
  ctx.globalAlpha = 0.76;
  ctx.strokeStyle='rgba(248,250,252,0.92)';
  ctx.fillStyle='rgba(248,250,252,0.92)';
  ctx.lineWidth=Math.max(2.4, len * 0.09);
  ctx.lineCap='round';
  ctx.lineJoin='round';
  ctx.beginPath();
  ctx.moveTo(-len*0.45, 0);
  ctx.lineTo(-len*0.12, 0);
  ctx.quadraticCurveTo(len*0.10, 0, len*0.10, sign*len*0.22);
  ctx.lineTo(len*0.10, tipY - sign*head*0.55);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(len*0.10, tipY);
  ctx.lineTo(len*0.10 - head, tipY - sign*head);
  ctx.lineTo(len*0.10 + head, tipY - sign*head);
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}}

function hexToRgb(hex) {{
  const r=parseInt(hex.slice(1,3),16), g=parseInt(hex.slice(3,5),16), b=parseInt(hex.slice(5,7),16);
  return r+','+g+','+b;
}}

function phaseVisual(tl) {{
  const p = normalizePhase(tl.phase, 0);
  if (p === 0) return ['ns', '#22c55e'];
  if (p === 1) return ['ns', '#fbbf24'];
  if (p === 2) return ['ew', '#22c55e'];
  return ['ew', '#fbbf24'];
}}

function drawActivePhase(x,y,axis,laneW,len,color='#22c55e') {{
  const alpha = color==='#22c55e'
    ? 0.32 + Math.sin(simStats.time*4.0) * 0.10
    : 0.22 + Math.sin(simStats.time*5.0) * 0.08;
  ctx.save();
  ctx.lineCap = 'round';
  ctx.setLineDash([laneW*0.42, laneW*0.28]);
  ctx.strokeStyle = 'rgba('+hexToRgb(color)+','+alpha+')';
  ctx.lineWidth = Math.max(5, laneW*0.26);
  ctx.shadowColor = color;
  ctx.shadowBlur = color==='#22c55e' ? 14 : 9;
  ctx.beginPath();
  if (axis === 'ew') {{
    ctx.moveTo(x-len, y); ctx.lineTo(x+len, y);
  }} else {{
    ctx.moveTo(x, y-len); ctx.lineTo(x, y+len);
  }}
  ctx.stroke();
  ctx.restore();
}}

// ── ACCIDENT scene: static crashed vehicle rendered in scene (not in vehicles[]) ──
function drawAccidentScene(g) {{
  const {{ laneW, axB, roadY, rbR }} = g;
  const bx = axB - rbR * 2.3;
  const by = canonicalY('W-E', g);

  // Hazard zone highlight
  ctx.fillStyle = 'rgba(251,191,36,0.12)';
  ctx.fillRect(bx - 60, by - laneW*1.8, 120, laneW*2.5);

  // Crashed vehicle body (sideways, blocking lane)
  ctx.save();
  ctx.translate(bx, by);
  ctx.rotate(0.25);   // slightly angled as if crashed
  ctx.fillStyle = '#dc2626';
  ctx.beginPath(); ctx.roundRect(-8, -5, 16, 10, 2); ctx.fill();
  // cracked windscreen
  ctx.strokeStyle='rgba(255,255,255,0.3)'; ctx.lineWidth=1;
  ctx.beginPath(); ctx.moveTo(-3,-4); ctx.lineTo(2,2); ctx.stroke();
  ctx.restore();

  // Warning triangle ahead of crash
  ctx.save();
  ctx.translate(bx - 28, by);
  ctx.fillStyle = '#fbbf24';
  ctx.strokeStyle = '#fbbf24';
  ctx.beginPath();
  ctx.moveTo(0,-9); ctx.lineTo(8,6); ctx.lineTo(-8,6); ctx.closePath();
  ctx.fill();
  ctx.fillStyle = '#1a1f2e';
  ctx.font='bold 7px Arial'; ctx.textAlign='center'; ctx.textBaseline='middle';
  ctx.fillText('!',0,2);
  ctx.restore();

  // "BLOCKED" text
  ctx.font = '8px Arial';
  ctx.fillStyle = '#fbbf24';
  ctx.textAlign = 'center';
  ctx.fillText('BLOCKED', bx, by - laneW*1.5);
}}

function drawIntersectionB(g) {{
  const {{ laneW, axB, roadY }} = g;
  const ext = mapExtent(g);
  const half = laneW * 2.55;

  // North-south road through B, kept darker than the main boulevard.
  drawRoad(axB, ext.top, axB, ext.bottom, laneW, '#151b2a', 'rgba(226,232,240,0.11)', 'rgba(86,207,178,0.06)');
  ctx.strokeStyle='rgba(226,232,240,0.13)'; ctx.lineWidth=1.5;
  ctx.beginPath();ctx.moveTo(axB-laneW*2,ext.top);ctx.lineTo(axB-laneW*2,ext.bottom);ctx.stroke();
  ctx.beginPath();ctx.moveTo(axB+laneW*2,ext.top);ctx.lineTo(axB+laneW*2,ext.bottom);ctx.stroke();
  drawDash(axB, ext.top, axB, ext.bottom, 'rgba(226,232,240,0.20)', 1.45, [12,12]);
  drawDash(axB-laneW, ext.top, axB-laneW, ext.bottom, 'rgba(226,232,240,0.12)', 1.15, [9,14]);
  drawDash(axB+laneW, ext.top, axB+laneW, ext.bottom, 'rgba(226,232,240,0.12)', 1.15, [9,14]);

  // Open square crossing box where the two roads meet.
  ctx.fillStyle='#252c3d';
  ctx.fillRect(axB-half, roadY-half, half*2, half*2);
  ctx.strokeStyle='rgba(226,232,240,0.20)';
  ctx.lineWidth=1.4;
  ctx.strokeRect(axB-half, roadY-half, half*2, half*2);

  // Lane markings continue straight through the crossing.
  drawDash(axB-half, roadY, axB+half, roadY, 'rgba(248,250,252,0.32)', 1.8, [10,9]);
  drawDash(axB, roadY-half, axB, roadY+half, 'rgba(248,250,252,0.24)', 1.6, [9,9]);
  drawDash(axB-half, roadY-laneW, axB+half, roadY-laneW, 'rgba(226,232,240,0.13)', 1.1, [8,10]);
  drawDash(axB-half, roadY+laneW, axB+half, roadY+laneW, 'rgba(226,232,240,0.13)', 1.1, [8,10]);

  // Stop bars give B a classic signalized-intersection read.
  ctx.setLineDash([]);
  ctx.strokeStyle='rgba(248,250,252,0.36)';
  ctx.lineWidth=2;
  ctx.beginPath();ctx.moveTo(axB-half-laneW*0.5, roadY-laneW*2);ctx.lineTo(axB-half-laneW*0.5, roadY+laneW*2);ctx.stroke();
  ctx.beginPath();ctx.moveTo(axB+half+laneW*0.5, roadY-laneW*2);ctx.lineTo(axB+half+laneW*0.5, roadY+laneW*2);ctx.stroke();
  ctx.beginPath();ctx.moveTo(axB-laneW*2, roadY-half-laneW*0.5);ctx.lineTo(axB+laneW*2, roadY-half-laneW*0.5);ctx.stroke();
  ctx.beginPath();ctx.moveTo(axB-laneW*2, roadY+half+laneW*0.5);ctx.lineTo(axB+laneW*2, roadY+half+laneW*0.5);ctx.stroke();
}}

function drawIntersectionBLabel(g) {{
  const {{ laneW, axB, roadY }} = g;
  const box = laneW * 1.55;
  ctx.fillStyle='rgba(2,6,23,0.50)';
  ctx.fillRect(axB-box/2, roadY-box/2, box, box);
  ctx.strokeStyle='rgba(86,207,178,0.44)';
  ctx.lineWidth=1.2;
  ctx.strokeRect(axB-box/2, roadY-box/2, box, box);
  ctx.font=`bold ${{Math.floor(laneW*0.9)}}px Arial`;
  ctx.fillStyle='#56cfb2';
  ctx.textAlign='center';
  ctx.textBaseline='middle';
  ctx.fillText('B', axB, roadY);
}}

function drawIntersectionAStopMarkings(g) {{
  const {{ laneW, axA, roadY }} = g;
  const boxHalf = laneW * 2.2;
  const stopOffset = boxHalf + laneW * 0.55;
  const stopWidth = Math.max(2.4, laneW * 0.13);
  const arrowScale = laneW * 1.12;
  const westStopX = axA - stopOffset;
  const northStopY = roadY - stopOffset;
  const arrowTipClearance = Math.max(5, Math.min(15, laneW * 0.32));
  const arrowForwardReach = arrowScale * 0.44;
  const westArrowX = westStopX - arrowForwardReach - arrowTipClearance;
  const northArrowY = northStopY - arrowForwardReach - arrowTipClearance;
  const westThroughLaneY = roadY + laneW * 0.50;
  const westTurnLaneY = roadY + laneW * 1.50;
  const northThroughLaneX = axA - laneW * 0.50;
  const northTurnLaneX = axA - laneW * 1.50;

  // Proper stop bars only cover the two incoming lanes.
  drawStopLine(westStopX, roadY + laneW*0.18, westStopX, roadY + laneW*1.88, stopWidth);
  drawStopLine(axA - laneW*1.88, northStopY, axA - laneW*0.18, northStopY, stopWidth);

  // Direction arrows are placed upstream of the stop lines on the asphalt lanes.
  drawStraightArrow(westArrowX, westThroughLaneY, 0, arrowScale);
  drawTurnArrow(westArrowX, westTurnLaneY, 0, 'right', arrowScale);
  drawStraightArrow(northThroughLaneX, northArrowY, Math.PI/2, arrowScale);
  drawTurnArrow(northTurnLaneX, northArrowY, Math.PI/2, 'right', arrowScale);
}}

// ── Scene draw ────────────────────────────────────────────────────────────────
function drawScene() {{
  const g = geo();
  const originX = (worldW - W) / 2;
  const originY = (worldH - H) / 2;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0,0,worldW,worldH);

  const bgColor = MODE==='NIGHT' ? '#060810' : '#0e1117';
  ctx.fillStyle = bgColor;
  ctx.fillRect(0,0,worldW,worldH);

  const {{ laneW, axA, axB, axC, roadY, rbR, sideNy, sideSy }} = g;
  const ext = mapExtent(g);

  ctx.save();
  ctx.translate(originX, originY);

  // Grid
  ctx.strokeStyle='rgba(255,255,255,0.03)'; ctx.lineWidth=1;
  for (let gx=ext.left;gx<ext.right;gx+=60){{ ctx.beginPath();ctx.moveTo(gx,ext.top);ctx.lineTo(gx,ext.bottom);ctx.stroke(); }}
  for (let gy=ext.top;gy<ext.bottom;gy+=60){{ ctx.beginPath();ctx.moveTo(ext.left,gy);ctx.lineTo(ext.right,gy);ctx.stroke(); }}

  // Boulevard highlight
  const blvdHL = MODE==='EMERGENCY' ? 'rgba(34,197,94,0.16)' : 'rgba(125,211,252,0.11)';
  const boulevardGrad = ctx.createLinearGradient(0, roadY-laneW*3, 0, roadY+laneW*3);
  boulevardGrad.addColorStop(0, 'rgba(125,211,252,0.02)');
  boulevardGrad.addColorStop(0.5, blvdHL);
  boulevardGrad.addColorStop(1, 'rgba(125,211,252,0.02)');
  ctx.fillStyle=boulevardGrad; ctx.fillRect(ext.left, roadY-laneW*3.0, ext.right-ext.left, laneW*6.0);

  // Road surface
  drawRoad(ext.left, roadY, ext.right, roadY, laneW, '#252c3d', 'rgba(226,232,240,0.20)', 'rgba(125,211,252,0.10)');

  // Lane edge markings
  ctx.strokeStyle='rgba(226,232,240,0.24)'; ctx.lineWidth=2.3;
  ctx.beginPath();ctx.moveTo(ext.left,roadY-laneW*2);ctx.lineTo(ext.right,roadY-laneW*2);ctx.stroke();
  ctx.beginPath();ctx.moveTo(ext.left,roadY+laneW*2);ctx.lineTo(ext.right,roadY+laneW*2);ctx.stroke();
  drawDash(ext.left,roadY,ext.right,roadY,'rgba(248,250,252,0.38)',2.2,[18,12]);
  drawDash(ext.left,roadY-laneW,ext.right,roadY-laneW,'rgba(226,232,240,0.16)',1.25,[10,13]);
  drawDash(ext.left,roadY+laneW,ext.right,roadY+laneW,'rgba(226,232,240,0.16)',1.25,[10,13]);

  // Vertical road — int_A continuous north/south corridor
  drawRoad(axA, ext.top, axA, ext.bottom, laneW, '#151b2a', 'rgba(226,232,240,0.11)');
  ctx.strokeStyle='rgba(226,232,240,0.13)'; ctx.lineWidth=1.5;
  ctx.beginPath();ctx.moveTo(axA-laneW*2,ext.top);ctx.lineTo(axA-laneW*2,ext.bottom);ctx.stroke();
  ctx.beginPath();ctx.moveTo(axA+laneW*2,ext.top);ctx.lineTo(axA+laneW*2,ext.bottom);ctx.stroke();
  drawDash(axA, ext.top, axA, ext.bottom,'rgba(226,232,240,0.20)',1.45,[12,12]);
  drawDash(axA-laneW, ext.top, axA-laneW, ext.bottom,'rgba(226,232,240,0.12)',1.15,[9,14]);
  drawDash(axA+laneW, ext.top, axA+laneW, ext.bottom,'rgba(226,232,240,0.12)',1.15,[9,14]);

  // Vertical road — int_C continuous north/south corridor
  drawRoad(axC, ext.top, axC, ext.bottom, laneW, '#151b2a', 'rgba(226,232,240,0.11)');
  ctx.strokeStyle='rgba(226,232,240,0.13)'; ctx.lineWidth=1.5;
  ctx.beginPath();ctx.moveTo(axC-laneW*2,ext.top);ctx.lineTo(axC-laneW*2,ext.bottom);ctx.stroke();
  ctx.beginPath();ctx.moveTo(axC+laneW*2,ext.top);ctx.lineTo(axC+laneW*2,ext.bottom);ctx.stroke();
  drawDash(axC, ext.top, axC, ext.bottom,'rgba(226,232,240,0.20)',1.45,[12,12]);
  drawDash(axC-laneW, ext.top, axC-laneW, ext.bottom,'rgba(226,232,240,0.12)',1.15,[9,14]);
  drawDash(axC+laneW, ext.top, axC+laneW, ext.bottom,'rgba(226,232,240,0.12)',1.15,[9,14]);

  drawIntersectionB(g);

  // Active signal phase ribbons
  const [axisA, phaseColorA] = phaseVisual(TL.A);
  const [axisB, phaseColorB] = phaseVisual(TL.B);
  const [axisC, phaseColorC] = phaseVisual(TL.C);
  drawActivePhase(axA, roadY, axisA, laneW, laneW*3.7, phaseColorA);
  drawActivePhase(axB, roadY, axisB, laneW, laneW*4.25, phaseColorB);
  drawActivePhase(axC, roadY, axisC, laneW, laneW*3.7, phaseColorC);
  drawIntersectionBLabel(g);

  // Intersection pads A and C
  [[axA,roadY,'#7b8cde','A'],[axC,roadY,'#f97316','C']].forEach(([ix,iy,ic,il]) => {{
    ctx.fillStyle='#202739';
    ctx.fillRect(ix-laneW*2.2, iy-laneW*2.2, laneW*4.4, laneW*4.4);
    ctx.strokeStyle='rgba(226,232,240,0.16)';
    ctx.lineWidth=1.2;
    ctx.strokeRect(ix-laneW*2.2, iy-laneW*2.2, laneW*4.4, laneW*4.4);
    ctx.font=`bold ${{Math.floor(laneW*0.85)}}px Arial`;
    ctx.fillStyle=ic; ctx.textAlign='center'; ctx.textBaseline='middle';
    ctx.fillText(il, ix, iy);
  }});
  drawIntersectionAStopMarkings(g);

  // Traffic light dots
  const tlOff = laneW*2.9;
  drawTLDot(axA-tlOff, roadY-laneW, tlColor(TL.A,'ew'));
  drawTLDot(axA+laneW, roadY-tlOff, tlColor(TL.A,'ns'));
  const bLightOff = laneW*3.85;
  drawTLDot(axB-bLightOff, roadY-laneW*1.3, tlColor(TL.B,'ew'));
  drawTLDot(axB+bLightOff, roadY+laneW*1.3, tlColor(TL.B,'ew'));
  drawTLDot(axB+laneW*1.3, roadY-bLightOff, tlColor(TL.B,'ns'));
  drawTLDot(axB-laneW*1.3, roadY+bLightOff, tlColor(TL.B,'ns'));
  drawTLDot(axC+tlOff, roadY+laneW, tlColor(TL.C,'ew'));
  drawTLDot(axC-laneW, roadY+tlOff, tlColor(TL.C,'ns'));

  // Labels
  ctx.textAlign='center';
  ctx.font=`${{Math.floor(laneW*0.7)}}px Arial`; ctx.fillStyle='rgba(255,255,255,0.28)';
  ctx.fillText('← WEST', laneW*3.5, roadY-laneW*3.2);
  ctx.fillText('EAST →', W-laneW*3.5, roadY-laneW*3.2);
  ctx.fillStyle='#7b8cde'; ctx.fillText('int_A', axA, Math.max(laneW*1.6, sideNy-laneW*1.25));
  ctx.fillStyle='#f97316'; ctx.fillText('int_C', axC, Math.min(H-laneW*1.05, sideSy+laneW*1.15));
  ctx.fillStyle='rgba(255,255,255,0.14)';
  ctx.font=`${{Math.floor(laneW*0.62)}}px Arial`;
  ctx.fillText('BOULEVARD PRINCIPAL', axB, roadY+laneW*3.8);

  // EMERGENCY: dashed ambulance path
  if (MODE==='EMERGENCY') {{
    ctx.strokeStyle='rgba(34,197,94,0.5)'; ctx.lineWidth=3; ctx.setLineDash([14,7]);
    ctx.beginPath();
    ctx.moveTo(0, canonicalY('W-E',g));
    ctx.lineTo(W, canonicalY('W-E',g));
    ctx.stroke(); ctx.setLineDash([]);
  }}

  // ACCIDENT: draw static crashed vehicle scene
  if (MODE==='ACCIDENT') drawAccidentScene(g);

  // Vehicles (draw after road markings so they appear on top)
  vehicles.forEach(v => v.draw(ctx, g));

  // NIGHT: subtle intersection glow
  if (MODE==='NIGHT') {{
    [[axA,roadY,'#7b8cde'],[axC,roadY,'#f97316']].forEach(([x,y,c]) => {{
      ctx.beginPath(); ctx.arc(x,y,rbR*1.6,0,Math.PI*2);
      ctx.fillStyle='rgba('+hexToRgb(c)+',0.04)'; ctx.fill();
    }});
    ctx.fillStyle='rgba(86,207,178,0.035)';
    ctx.fillRect(axB-laneW*4.6, roadY-laneW*4.6, laneW*9.2, laneW*9.2);
  }}
  ctx.restore();
}}

// ── Status panel ──────────────────────────────────────────────────────────────
function statusColor(wait) {{
  if (wait < 30) return ['#22c55e','Flowing',   '#22c55e22'];
  if (wait < 70) return ['#f97316','Moderate',  '#f9731622'];
  return               ['#ef4444','Congested', '#ef444422'];
}}

function phaseColor(p) {{
  const phase = normalizePhase(p, 0);
  if (phase === 0 || phase === 2) return '#22c55e';
  return '#fbbf24';
}}

function phaseAxisLabel(p) {{
  const phase = normalizePhase(p, 0);
  return phase < 2 ? 'NS' : 'EW';
}}

function phaseName(p) {{
  return ['NS Green','NS Yellow','EW Green','EW Yellow'][normalizePhase(p, 0)] ?? '—';
}}

function clampValue(n, min, max) {{
  return Math.min(max, Math.max(min, n));
}}

function vehicleLoadStyle(count) {{
  const pct = clampValue((count / 18) * 100, 8, 100);
  if (count >= 13) return {{ pct, color:'#ef4444' }};
  if (count >= 7) return {{ pct, color:'#f97316' }};
  return {{ pct, color:'#22c55e' }};
}}

function cardSignalStatus(tl, wait) {{
  const phase = normalizePhase(tl.phase, 0);
  if (phase === 1 || phase === 3) return {{ label:'Transition', color:'#fbbf24' }};
  if (wait >= 70) return {{ label:'Stopped', color:'#ef4444' }};
  if (wait >= 30) return {{ label:'Moderate', color:'#f97316' }};
  return {{ label:'Active', color:'#22c55e' }};
}}

function controllerLabel() {{
  return {{
    NORMAL:'RL Adaptive',
    EMERGENCY:'Priority',
    ACCIDENT:'Incident',
    NIGHT:'Actuated',
  }}[MODE] || 'Adaptive';
}}

function updateSummaryMetrics() {{
  const total = simStats.A.vc + simStats.B.vc + simStats.C.vc;
  const avgWait = (simStats.A.wait + simStats.B.wait + simStats.C.wait) / 3;
  document.getElementById('metric-total').textContent = total;
  document.getElementById('metric-wait').textContent = (isFinite(avgWait) ? avgWait : 0).toFixed(1) + 's';
  document.getElementById('metric-controller').textContent = controllerLabel();
}}

function deriveDecision() {{
  const ewCount = vehicles.filter(v => !v.done && (v.route==='W-E' || v.route==='E-W')).length;
  const nsCount = vehicles.filter(v => !v.done && !(v.route==='W-E' || v.route==='E-W')).length;
  const avgWait = (simStats.A.wait + simStats.B.wait + simStats.C.wait) / 3;

  if (MODE === 'EMERGENCY') {{
    return {{
      decision: 'Hold East-West Priority',
      reason: 'Emergency corridor is being cleared end-to-end',
      confidence: 96,
    }};
  }}
  if (MODE === 'ACCIDENT') {{
    const conf = Math.round(clampValue(82 + simStats.B.wait * 0.12, 84, 95));
    return {{
      decision: 'Relieve int_B Queue',
      reason: 'Incident pressure is highest around the B crossing',
      confidence: conf,
    }};
  }}
  if (MODE === 'NIGHT') {{
    return {{
      decision: 'Use Actuated Low-Demand Cycle',
      reason: 'Sparse arrivals allow shorter idle phases',
      confidence: 88,
    }};
  }}

  const ewFavored = ewCount >= nsCount;
  const gap = Math.abs(ewCount - nsCount);
  const conf = Math.round(clampValue(78 + gap * 4 + avgWait * 0.12, 80, 94));
  return {{
    decision: ewFavored ? 'Keep East-West Green' : 'Serve North-South Green',
    reason: ewFavored
      ? `EW queue is higher than NS (${{ewCount}} vs ${{nsCount}})`
      : `NS queue is higher than EW (${{nsCount}} vs ${{ewCount}})`,
    confidence: conf,
  }};
}}

function updateDecisionCard() {{
  const d = deriveDecision();
  document.getElementById('decision-current').textContent = d.decision;
  document.getElementById('decision-reason').textContent = d.reason;
  document.getElementById('decision-confidence').textContent = d.confidence + '%';
  const fill = document.getElementById('confidence-fill');
  fill.style.width = d.confidence + '%';
  fill.style.background = d.confidence >= 90
    ? 'linear-gradient(90deg,#22c55e,#14b8a6)'
    : 'linear-gradient(90deg,#22c55e,#f59e0b)';
}}

function updatePanel() {{
  const modeLabels = {{ NORMAL:'NORMAL', EMERGENCY:'EMERGENCY', ACCIDENT:'ACCIDENT', NIGHT:'NIGHT MODE' }};
  const modeSubtitles = {{
    NORMAL:'Simulation running',
    EMERGENCY:'Priority corridor active',
    ACCIDENT:'Incident response active',
    NIGHT:'Low-demand controller',
  }};
  const modeColors = {{ NORMAL:'#22c55e', EMERGENCY:'#ef4444', ACCIDENT:'#fbbf24', NIGHT:'#a78bfa' }};
  const mb = document.getElementById('mode-badge');
  mb.textContent = modeLabels[MODE]||MODE;
  mb.style.color = modeColors[MODE]||'#e0e0e0';
  document.getElementById('mode-subtitle').textContent = modeSubtitles[MODE] || 'Simulation running';
  const modeDot = document.getElementById('mode-dot');
  modeDot.style.background = modeColors[MODE] || '#22c55e';
  modeDot.style.boxShadow = '0 0 16px ' + (modeColors[MODE] || '#22c55e');
  mb.closest('.mode-card').style.borderColor = (modeColors[MODE]||'#2a3045')+'55';
  updateSummaryMetrics();

  [['A',TL.A,'a'],['B',TL.B,'b'],['C',TL.C,'c']].forEach(([k,tl,id]) => {{
    const s = simStats[k];
    // Ensure wait is always a finite number for display
    const displayWait = isFinite(s.wait) ? s.wait : 0;
    const [sc,sl,sbg] = statusColor(displayWait);
    const phaseEl = document.getElementById(id+'-phase');
    phaseEl.textContent = phaseName(tl.phase);
    phaseEl.style.color = phaseColor(tl.phase);
    document.getElementById(id+'-count').textContent = s.vc;
    document.getElementById(id+'-wait').textContent  = displayWait.toFixed(1)+' s';
    const signal = cardSignalStatus(tl, displayWait);
    const signalPill = document.getElementById(id+'-signal');
    signalPill.textContent = signal.label;
    signalPill.style.color = signal.color;
    signalPill.style.borderColor = signal.color + '88';
    signalPill.style.background = signal.color + '18';
    const load = vehicleLoadStyle(s.vc);
    document.getElementById(id+'-load').style.background =
      'linear-gradient(90deg,' + load.color + ',' + load.color + 'aa)';
    document.getElementById(id+'-axis').textContent = phaseAxisLabel(tl.phase) + ' phase';
    const badge = document.getElementById(id+'-badge');
    badge.textContent      = sl;
    badge.style.color      = sc;
    badge.style.background = sbg;
    badge.style.border     = '1px solid '+sc+'66';
    badge.style.boxShadow  = '0 0 18px '+sc+'22';
    const card = document.getElementById('card-'+id);
    card.style.setProperty('--status-color', signal.color);
    card.style.setProperty('--load-color', load.color);
    card.style.setProperty('--load-width', load.pct.toFixed(0) + '%');
    card.style.borderColor = signal.color+'55';
  }});
  updateDecisionCard();
}}

// ── Banner ─────────────────────────────────────────────────────────────────────
const BANNERS = {{
  NORMAL:    null,
  EMERGENCY: {{ text:'🚨 EMERGENCY OVERRIDE ACTIVE — AI clearing path', color:'#ef4444' }},
  ACCIDENT:  {{ text:'⚠️ ACCIDENT DETECTED — AI rerouting traffic',      color:'#fbbf24' }},
  NIGHT:     {{ text:'🌙 NIGHT MODE — Smart timing active',               color:'#7b8cde' }},
}};
(function() {{
  const b = BANNERS[MODE];
  if (!b) {{ banner.style.display='none'; return; }}
  banner.style.display='block'; banner.textContent=b.text;
  banner.style.color=b.color; banner.style.borderColor=b.color+'55';
}})();

// ── Main loop ─────────────────────────────────────────────────────────────────
let last = null, panelTimer = 0;

function frame(ts) {{
  if (!last) last = ts;
  const dt = Math.min((ts-last)/1000, 0.05);
  last = ts;

  const g = geo();

  updateTL(dt);
  updateMockData(dt);

  spawnTimer += dt;
  if (spawnTimer >= SPAWN_INTERVAL && vehicles.length < MAX_VEHICLES) {{
    spawnTimer = 0;
    spawnVehicle();
  }}

  // Update, then cull done vehicles
  vehicles.forEach(v => {{ v.update(dt, g); }});
  for (let i=vehicles.length-1; i>=0; i--) {{
    if (vehicles[i].done) vehicles.splice(i,1);
  }}

  drawScene();
  maybeLog(dt);

  panelTimer += dt;
  if (panelTimer > 0.3) {{ panelTimer=0; updatePanel(); }}

  requestAnimationFrame(frame);
}}

requestAnimationFrame(frame);
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
html_content = _build_html(mode)
components.html(html_content, height=540, scrolling=False)

# ---------------------------------------------------------------------------
# Integration note (shown below the canvas)
# ---------------------------------------------------------------------------
with st.expander("ℹ️  How to connect real simulation data", expanded=False):
    st.markdown("""
**Demo mode** (current): all vehicle movement and signal timing is simulated
entirely in JavaScript using a mock generator. No backend required.

**To inject real simulation data** from your SUMO/TraCI run:

1. After each `env.step()` call in `main.py`, write a small JSON snapshot:
   ```python
   import json, pathlib
   pathlib.Path("data/live_state.json").write_text(json.dumps({
       "intA_phase": state.intersections["int_A"].phase_index,
       "intA_vehicle_count": ...,
       "intA_wait": ...,
       "intB_phase": state.intersections["int_B"].phase_index,
       "intB_vehicle_count": ...,
       "intB_wait": ...,
       "intC_phase": state.intersections["int_C"].phase_index,
       "intC_vehicle_count": ...,
       "intC_wait": ...,
       "emergency_present": bool(state.intersections["int_B"].approaches["north_in"]["has_emergency"]),
       "sim_time": state.sim_time,
   }))
   ```

2. In `live_map.py`, read that file and pass it into `_build_html()` as a
   `sim_data` argument:
   ```python
   import json
   live_path = ROOT / "data" / "live_state.json"
   sim_data = json.loads(live_path.read_text()) if live_path.exists() else None
   ```

3. In `_build_html()`, replace `window.SIM_DATA = null;` with the injected
   values serialised as a JS literal (use `json.dumps(sim_data)`).

4. The JS already has both code paths:
   - `if (window.SIM_DATA)` → reads the real values
   - `else` → runs the mock generator

**Search for `REAL DATA INJECTION POINT`** in the JS source for the exact
location to replace.
""")
