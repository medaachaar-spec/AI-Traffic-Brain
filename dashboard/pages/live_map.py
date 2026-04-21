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
  }}
  #canvas-col {{
    flex: 1 1 auto;
    position: relative;
  }}
  canvas {{
    display: block;
    width: 100%;
    height: 100%;
  }}
  #panel {{
    width: 228px;
    flex-shrink: 0;
    background: rgba(6,9,16,0.97);
    border-left: 1px solid rgba(0,212,255,0.1);
    padding: 12px 10px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 8px;
    backdrop-filter: blur(20px);
  }}
  .int-card {{
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 10px;
    padding: 10px 12px;
    transition: border-color 0.2s;
  }}
  .int-card:hover {{ border-color: rgba(255,255,255,0.13); }}
  .int-card-title {{
    font-family: 'Space Mono', monospace;
    font-size: 0.63rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 7px;
  }}
  .int-row {{
    display: flex;
    justify-content: space-between;
    font-size: 0.7rem;
    margin: 4px 0;
    color: #3a4a6a;
    font-family: 'Inter', sans-serif;
  }}
  .int-row span:last-child {{
    color: #c8d4f0;
    font-weight: 700;
    font-family: 'Space Mono', monospace;
    font-size: 0.66rem;
  }}
  .badge {{
    display: inline-block;
    padding: 2px 9px;
    border-radius: 12px;
    font-family: 'Space Mono', monospace;
    font-size: 0.6rem;
    font-weight: 700;
    margin-top: 6px;
    letter-spacing: 0.06em;
  }}
  #mode-badge {{
    background: rgba(0,212,255,0.06);
    border: 1px solid rgba(0,212,255,0.18);
    border-radius: 10px;
    padding: 9px 12px;
    font-family: 'Space Mono', monospace;
    font-size: 0.68rem;
    font-weight: 700;
    text-align: center;
    letter-spacing: 0.1em;
    color: #00d4ff;
  }}
  #log-box {{
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
    padding: 9px 10px;
    flex: 1 1 auto;
    overflow-y: auto;
  }}
  .log-title {{
    font-family: 'Space Mono', monospace;
    font-size: 0.58rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #00d4ff;
    margin-bottom: 7px;
    font-weight: 700;
  }}
  .log-entry {{
    font-family: 'Inter', sans-serif;
    font-size: 0.63rem;
    color: #3a4a6a;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    padding: 4px 0;
    line-height: 1.45;
  }}
  .log-entry:last-child {{ border-bottom: none; }}
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
</style>
</head>
<body>
<div id="wrapper">
  <div id="canvas-col">
    <canvas id="c"></canvas>
    <div id="banner"></div>
  </div>
  <div id="panel">
    <div id="mode-badge">— MODE —</div>
    <div class="int-card" id="card-a">
      <div class="int-card-title" style="color:#ff9500;">int_A — West T-jct</div>
      <div class="int-row"><span>Phase</span><span id="a-phase">—</span></div>
      <div class="int-row"><span>Vehicles</span><span id="a-count">—</span></div>
      <div class="int-row"><span>Avg wait</span><span id="a-wait">—</span></div>
      <div><span class="badge" id="a-badge">—</span></div>
    </div>
    <div class="int-card" id="card-b">
      <div class="int-card-title" style="color:#00d4ff;">int_B — Roundabout</div>
      <div class="int-row"><span>Phase</span><span id="b-phase">—</span></div>
      <div class="int-row"><span>Vehicles</span><span id="b-count">—</span></div>
      <div class="int-row"><span>Avg wait</span><span id="b-wait">—</span></div>
      <div><span class="badge" id="b-badge">—</span></div>
    </div>
    <div class="int-card" id="card-c">
      <div class="int-card-title" style="color:#8b5cf6;">int_C — East T-jct</div>
      <div class="int-row"><span>Phase</span><span id="c-phase">—</span></div>
      <div class="int-row"><span>Vehicles</span><span id="c-count">—</span></div>
      <div class="int-row"><span>Avg wait</span><span id="c-wait">—</span></div>
      <div><span class="badge" id="c-badge">—</span></div>
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
const ctx    = canvas.getContext('2d');
const banner = document.getElementById('banner');

let W, H;
function resize() {{
  const col = document.getElementById('canvas-col');
  W = col.clientWidth;
  H = col.clientHeight;
  canvas.width  = W;
  canvas.height = H;
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
  const axA   = W * 0.18;
  const axB   = W * 0.50;
  const axC   = W * 0.82;
  const roadY = cy;
  const rbR   = laneW * 3.2;               // roundabout orbit radius
  const sideNy = cy - H * 0.28;
  const sideSy = cy + H * 0.28;
  return {{ laneW, axA, axB, axC, roadY, rbR, sideNy, sideSy }};
}}

// ── Traffic light state ────────────────────────────────────────────────────
// phase: 0=NS_GREEN  1=NS_YELLOW  2=EW_GREEN  3=EW_YELLOW
const TL = {{
  A: {{ phase:0, timer:0,  durations:[18,3,18,3] }},
  B: {{ phase:2, timer:8,  durations:[20,3,20,3] }},
  C: {{ phase:0, timer:4,  durations:[18,3,18,3] }},
}};

function tlColor(tl, axis) {{
  const p = tl.phase;
  if (axis === 'ns') {{
    if (p===0) return '#22c55e';
    if (p===1) return '#fbbf24';
    return '#ef4444';
  }}
  if (p===2) return '#22c55e';
  if (p===3) return '#fbbf24';
  return '#ef4444';
}}

function tlIsGreen(tl, axis) {{
  if (axis==='ns') return tl.phase===0;
  return tl.phase===2;
}}

let tlDt = 0;
function updateTL(dt) {{
  if (window.SIM_DATA) {{
    TL.A.phase = window.SIM_DATA.intA_phase || 0;
    TL.B.phase = window.SIM_DATA.intB_phase || 2;
    TL.C.phase = window.SIM_DATA.intC_phase || 0;
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
  const vcB = vehicles.filter(v => !v.done && (Math.abs(v.x-g.axB)<110 || v.phase==='roundabout')).length;
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
    n => `int_B: roundabout entry cleared, priority path open`,
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
  logMessages.unshift(`[t=${{ts}}s] ${{fn(id)}}`);
  if (logMessages.length > LOG_MAX) logMessages.pop();
  document.getElementById('log-entries').innerHTML =
    logMessages.map(m => `<div class="log-entry">${{m}}</div>`).join('');
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

// ── PATH HELPERS ─────────────────────────────────────────────────────────────
// Each route has a canonical lane-centre coordinate so all vehicles on the
// same route travel on exactly the same pixel track.

function canonicalY(route, g) {{
  // Returns the fixed Y coordinate for horizontal routes
  if (route==='W-E') return g.roadY - g.laneW * 0.75;
  if (route==='E-W') return g.roadY + g.laneW * 0.75;
  return g.roadY;
}}

function canonicalX(route, g) {{
  // Returns the fixed X coordinate for vertical routes
  if (route==='NA-S') return g.axA + g.laneW * 0.65;
  if (route==='S-NA') return g.axA - g.laneW * 0.65;
  if (route==='SC-N') return g.axC - g.laneW * 0.65;
  if (route==='N-SC') return g.axC + g.laneW * 0.65;
  return 0;
}}

// ── SPACING HELPERS ───────────────────────────────────────────────────────────
// Minimum following distance = vehicle length + safety buffer
const MIN_FOLLOW_GAP = 22;   // px below which target speed = 0
const DECEL_DIST     = 60;   // px — begin decelerating when gap < this

/**
 * gapAhead: distance to nearest vehicle on the same route that is
 * directly ahead (positive travel direction). Returns Infinity if clear.
 */
function gapAhead(v, allVehicles) {{
  let minGap = Infinity;
  for (const other of allVehicles) {{
    if (other === v || other.done) continue;
    if (other.route !== v.route)  continue;
    if (other.phase === 'roundabout') continue;

    const dx = other.x - v.x;
    const dy = other.y - v.y;
    // Signed projection onto travel direction (positive = ahead)
    const ahead = dx * v.dx + dy * v.dy;
    if (ahead <= 0) continue;

    // Lateral separation must be within one lane width (same lane check)
    const lateral = Math.abs(dx * v.dy - dy * v.dx);
    if (lateral > 14) continue;

    const dist = Math.sqrt(dx*dx + dy*dy);
    if (dist < minGap) minGap = dist;
  }}
  return minGap;
}}

/**
 * distToStopLine: distance from vehicle to nearest active (red) stop line
 * that this vehicle is approaching. Returns Infinity if none applies.
 */
function distToStopLine(v, g) {{
  if (v.isEmergency && MODE==='EMERGENCY') return Infinity;

  const lw = g.laneW;
  const APPROACH = 90;   // px — stop awareness zone

  switch (v.route) {{
    case 'W-E': {{
      // int_A EW stop line
      const s1 = g.axA - lw * 2.7;
      if (!tlIsGreen(TL.A,'ew') && v.x < s1 && s1-v.x < APPROACH) return s1-v.x;
      // int_B roundabout entry stop line
      const s2 = g.axB - g.rbR - lw * 1.5;
      if (v.x > g.axA && v.x < s2) {{
        if (!tlIsGreen(TL.B,'ew') && s2-v.x < APPROACH) return s2-v.x;
      }}
      // ACCIDENT: blockage acts as permanent stop line in W-E lane
      if (MODE==='ACCIDENT') {{
        const accX = g.axB - g.rbR * 2.3;
        if (v.x < accX && accX-v.x < APPROACH) return accX - v.x - lw*0.5;
      }}
      // Roundabout entry yield gate — hold just outside orbit entry when occupied
      if (v.phase === 'travel' && v.usesRb) {{
        const rbGateW = g.axB - g.rbR * 1.05;
        if (v.x < rbGateW && rbGateW - v.x < APPROACH && !canEnterRoundabout(v)) {{
          return Math.max(1, rbGateW - v.x - 4);
        }}
      }}
      return Infinity;
    }}
    case 'E-W': {{
      const s1 = g.axC + lw * 2.7;
      if (!tlIsGreen(TL.C,'ew') && v.x > s1 && v.x-s1 < APPROACH) return v.x-s1;
      const s2 = g.axB + g.rbR + lw * 1.5;
      if (v.x < g.axC && v.x > s2) {{
        if (!tlIsGreen(TL.B,'ew') && v.x-s2 < APPROACH) return v.x-s2;
      }}
      // Roundabout entry yield gate — hold just outside orbit entry when occupied
      if (v.phase === 'travel' && v.usesRb) {{
        const rbGateE = g.axB + g.rbR * 1.05;
        if (v.x > rbGateE && v.x - rbGateE < APPROACH && !canEnterRoundabout(v)) {{
          return Math.max(1, v.x - rbGateE - 4);
        }}
      }}
      return Infinity;
    }}
    case 'NA-S': {{
      // Stop before int_A crossing (approaching from north, dy=+1)
      const sl = g.roadY - lw * 2.7;
      if (!tlIsGreen(TL.A,'ns') && v.y < sl && sl-v.y < APPROACH) return sl-v.y;
      return Infinity;
    }}
    case 'S-NA': {{
      // Stop south of int_A (approaching from south, dy=-1)
      const sl = g.roadY + lw * 2.7;
      if (!tlIsGreen(TL.A,'ns') && v.y > sl && v.y-sl < APPROACH) return v.y-sl;
      return Infinity;
    }}
    case 'N-SC': {{
      const sl = g.roadY - lw * 2.7;
      if (!tlIsGreen(TL.C,'ns') && v.y < sl && sl-v.y < APPROACH) return sl-v.y;
      return Infinity;
    }}
    case 'SC-N': {{
      const sl = g.roadY + lw * 2.7;
      if (!tlIsGreen(TL.C,'ns') && v.y > sl && v.y-sl < APPROACH) return v.y-sl;
      return Infinity;
    }}
  }}
  return Infinity;
}}

/**
 * targetSpeed: desired speed based on gap to leader and distance to stop line.
 * Returns a value in [0 .. baseSpd].
 */
function targetSpeed(v, g, allVehicles) {{
  // Emergency vehicles in emergency mode ignore all limits
  if (v.isEmergency && MODE==='EMERGENCY') return v.baseSpd;

  // Nearest hard constraint (stop line or gap)
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

// ── Vehicle class ─────────────────────────────────────────────────────────────
let vehicleIdCounter = 0;

class Vehicle {{
  constructor(routeDef, typeDef, g, startOffset=0) {{
    this.id           = vehicleIdCounter++;
    this.route        = routeDef.id;
    this.type         = typeDef.type;
    this.color        = typeDef.color;
    this.vw           = typeDef.w;
    this.vh           = typeDef.h;
    this.baseSpd      = typeDef.spd * (MODE==='NIGHT' ? 0.75 : 1.0);
    this.spd          = this.baseSpd * 0.5;  // start slow to prevent initial overlap
    this.phase        = 'travel';   // 'travel' | 'roundabout'
    this.rbAngle      = 0;
    this.rbStartAngle = 0;
    this.done         = false;
    this.flashTimer   = 0;
    this.isEmergency  = (this.type === 'emergency');
    this.startOffset  = startOffset;  // initial position offset along route
    this._initPath(g);
  }}

  _initPath(g) {{
    const lw = g.laneW;
    this.dx = 0; this.dy = 0;

    switch(this.route) {{
      case 'W-E':
        this.y     = canonicalY('W-E', g);
        this.x     = -this.vw - this.startOffset;
        this.dx    = 1; this.dy = 0;
        this.destX = W + this.vw + 10;
        this.usesRb = true;
        break;
      case 'E-W':
        this.y     = canonicalY('E-W', g);
        this.x     = W + this.vw + this.startOffset;
        this.dx    = -1; this.dy = 0;
        this.destX = -this.vw - 10;
        this.usesRb = true;
        break;
      case 'NA-S':
        this.x     = canonicalX('NA-S', g);
        this.y     = g.sideNy - this.startOffset;
        this.dx    = 0; this.dy = 1;
        this.destY = H + this.vw + 10;
        this.usesRb = false;
        break;
      case 'S-NA':
        this.x     = canonicalX('S-NA', g);
        this.y     = H + this.vw + this.startOffset;
        this.dx    = 0; this.dy = -1;
        this.destY = g.sideNy - 10;
        this.usesRb = false;
        break;
      case 'SC-N':
        this.x     = canonicalX('SC-N', g);
        this.y     = g.sideSy + this.startOffset;
        this.dx    = 0; this.dy = -1;
        this.destY = -this.vw - 10;
        this.usesRb = false;
        break;
      case 'N-SC':
        this.x     = canonicalX('N-SC', g);
        this.y     = -this.vw - this.startOffset;
        this.dx    = 0; this.dy = 1;
        this.destY = g.sideSy + 10;
        this.usesRb = false;
        break;
      default:
        this.done = true;
    }}
  }}

  resetPath() {{
    const g = geo();
    this._initPath(g);
  }}

  // ── update ────────────────────────────────────────────────────────────────
  update(dt, g) {{
    if (this.done) return;
    this.flashTimer += dt;

    // ── Roundabout orbit ──────────────────────────────────────────────────
    if (this.phase === 'roundabout') {{
      const orbitR    = g.rbR * 0.78;
      const baseAngSpd = this.baseSpd / orbitR;   // rad/s at base speed

      // Slow down if another vehicle is too close ahead in orbit
      const angGap = rbGapAhead(this);
      const MIN_ANG_GAP = 0.55;   // ~31° — minimum following gap on orbit
      let angSpd;
      if (angGap < MIN_ANG_GAP) {{
        angSpd = 0;
      }} else if (angGap < MIN_ANG_GAP * 2) {{
        angSpd = baseAngSpd * ((angGap - MIN_ANG_GAP) / MIN_ANG_GAP);
      }} else {{
        angSpd = baseAngSpd;
      }}

      // Emergency vehicles in emergency mode pass everyone
      if (this.isEmergency && MODE==='EMERGENCY') angSpd = baseAngSpd * 1.3;

      this.rbAngle += angSpd * dt * 55;  // clockwise (angle increases)

      this.x = g.axB   + Math.cos(this.rbAngle) * orbitR;
      this.y = g.roadY + Math.sin(this.rbAngle) * orbitR;

      // Compute how many radians we've turned since entering
      const turned = this.rbAngle - this.rbStartAngle;

      // Exit after ~162° — at this arc position the orbit geometry naturally
      // places the vehicle at canonicalY (within ~1 px), so no y-snap needed.
      if (turned >= Math.PI * 0.90) {{
        this.phase = 'travel';
        // Keep current x,y from orbit position — already on correct lane Y
        if (this.route === 'W-E') {{
          this.dx = 1; this.dy = 0;
        }} else {{
          this.dx = -1; this.dy = 0;
        }}
        this.spd = this.baseSpd * 0.6;  // exit at reduced speed
      }}
      return;
    }}

    // ── Enter roundabout check ────────────────────────────────────────────
    if (this.usesRb && this.phase === 'travel') {{
      const dxB = this.x - g.axB;

      // W-E: approach from west, entry at left edge of roundabout
      if (this.route==='W-E' && dxB > -g.rbR*1.5 && dxB < -g.rbR*0.95) {{
        if (canEnterRoundabout(this)) {{
          this.phase        = 'roundabout';
          this.rbAngle      = Math.PI;   // west side of roundabout
          this.rbStartAngle = Math.PI;
          this.spd          = this.baseSpd * 0.7;
        }}
        // else: wait at entry (distToStopLine handles red-gate stop)
      }}

      // E-W: approach from east, entry at right edge
      if (this.route==='E-W' && dxB < g.rbR*1.5 && dxB > g.rbR*0.95) {{
        if (canEnterRoundabout(this)) {{
          this.phase        = 'roundabout';
          this.rbAngle      = 0;   // east side
          this.rbStartAngle = 0;
          this.spd          = this.baseSpd * 0.7;
        }}
      }}
    }}

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

    const step = this.spd * 60 * dt;
    this.x += this.dx * step;
    this.y += this.dy * step;

    // Check destination
    const arrived = (
      (this.dx > 0 && this.x  >= this.destX) ||
      (this.dx < 0 && this.x  <= this.destX) ||
      (this.dy > 0 && this.y  >= this.destY) ||
      (this.dy < 0 && this.y  <= this.destY)
    );
    if (arrived) this.done = true;
  }}

  // ── draw ──────────────────────────────────────────────────────────────────
  draw(ctx, g) {{
    if (this.done) return;
    ctx.save();
    ctx.translate(this.x, this.y);

    // Rotation: for roundabout, face tangentially; else face travel direction
    let angle;
    if (this.phase === 'roundabout') {{
      angle = this.rbAngle + Math.PI / 2;  // tangent to orbit (clockwise)
    }} else {{
      angle = Math.atan2(this.dy, this.dx);
    }}
    ctx.rotate(angle);

    // Emergency glow
    if (this.isEmergency) {{
      const flash = Math.sin(this.flashTimer * 10) > 0;
      ctx.shadowColor = flash ? '#ef4444' : '#ff9900';
      ctx.shadowBlur  = 14;
    }}

    // Vehicle body
    ctx.fillStyle = this.color;
    ctx.beginPath();
    ctx.roundRect(-this.vw/2, -this.vh/2, this.vw, this.vh, 2);
    ctx.fill();

    // Windscreen highlight
    ctx.fillStyle = 'rgba(255,255,255,0.22)';
    ctx.fillRect(this.vw*0.08, -this.vh*0.38, this.vw*0.22, this.vh*0.76);

    // Emergency cross
    if (this.isEmergency) {{
      ctx.fillStyle = '#fff';
      ctx.fillRect(-2, -this.vh*0.45+1, 4, this.vh-2);
      ctx.fillRect(-this.vw*0.32, -2, this.vw*0.64, 4);
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
function spawnBlocked(routeId, g) {{
  const CLEAR = 28;
  let sx, sy;
  const lw = g.laneW;
  switch(routeId) {{
    case 'W-E':  sx=-lw;    sy=canonicalY('W-E',g); break;
    case 'E-W':  sx=W+lw;   sy=canonicalY('E-W',g); break;
    case 'NA-S': sx=canonicalX('NA-S',g); sy=g.sideNy-lw; break;
    case 'S-NA': sx=canonicalX('S-NA',g); sy=H+lw; break;
    case 'SC-N': sx=canonicalX('SC-N',g); sy=g.sideSy+lw; break;
    case 'N-SC': sx=canonicalX('N-SC',g); sy=-lw; break;
    default: return false;
  }}
  return vehicles.some(v => !v.done && Math.hypot(v.x-sx, v.y-sy) < CLEAR);
}}

function spawnVehicle() {{
  const g = geo();

  // EMERGENCY: ensure exactly one ambulance exists, spawn it first
  if (MODE==='EMERGENCY' && !vehicles.some(v=>v.isEmergency)) {{
    const td = TYPE_DEFS.find(t=>t.type==='emergency');
    if (!spawnBlocked('W-E', g)) {{
      vehicles.push(new Vehicle({{id:'W-E'}}, td, g, 0));
    }}
    return;
  }}

  const routeDef = pickRandom(ROUTE_DEFS);
  if (spawnBlocked(routeDef.id, g)) return;  // entry point occupied — skip

  const typeDef  = pickRandom(TYPE_DEFS.filter(t => t.type !== 'emergency'));
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
    const tDef  = pickRandom(TYPE_DEFS.filter(t=>t.type!=='emergency'));
    for (let i=0; i<count; i++) {{
      vehicles.push(new Vehicle({{id:rid}}, tDef, g, i * gap));
    }}
  }});

  // EMERGENCY: always seed with an ambulance well behind so it has room to accelerate
  if (MODE==='EMERGENCY') {{
    const td = TYPE_DEFS.find(t=>t.type==='emergency');
    vehicles.push(new Vehicle({{id:'W-E'}}, td, g, gap * 7));
  }}

  // ACCIDENT: pre-queue several W-E vehicles behind the blockage so the queue
  // is already visible from the start of the simulation.
  if (MODE==='ACCIDENT') {{
    const accX = g.axB - g.rbR * 2.3;
    for (let i=0; i<4; i++) {{
      const tDef2 = pickRandom(TYPE_DEFS.filter(t=>t.type!=='emergency'));
      const v2 = new Vehicle({{id:'W-E'}}, tDef2, g, 0);
      v2.x   = accX - 32 - i * 32;   // queue behind accident stop line
      v2.y   = canonicalY('W-E', g);
      v2.spd = 0;
      vehicles.push(v2);
    }}
  }}
}})();

// ── Drawing helpers ───────────────────────────────────────────────────────────
function drawRoad(x1,y1,x2,y2,laneW,color='#1a1a2e') {{
  const ang = Math.atan2(y2-y1, x2-x1);
  const px  = Math.sin(ang)*laneW*2;
  const py  = Math.cos(ang)*laneW*2;
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.moveTo(x1-px,y1+py); ctx.lineTo(x2-px,y2+py);
  ctx.lineTo(x2+px,y2-py); ctx.lineTo(x1+px,y1-py);
  ctx.closePath(); ctx.fill();
}}

function drawDash(x1,y1,x2,y2) {{
  ctx.setLineDash([12,10]);
  ctx.strokeStyle = 'rgba(200,200,200,0.2)';
  ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(x1,y1); ctx.lineTo(x2,y2); ctx.stroke();
  ctx.setLineDash([]);
}}

function drawTLDot(x,y,color) {{
  ctx.beginPath(); ctx.arc(x,y,5,0,Math.PI*2);
  ctx.fillStyle  = color;
  ctx.shadowBlur = color==='#22c55e' ? 9 : 4;
  ctx.shadowColor= color;
  ctx.fill();
  ctx.shadowBlur = 0;
}}

function drawArrow(x,y,angle,color,len=16) {{
  ctx.save(); ctx.translate(x,y); ctx.rotate(angle);
  ctx.strokeStyle=color; ctx.lineWidth=2;
  ctx.beginPath();
  ctx.moveTo(-len/2,0); ctx.lineTo(len/2,0);
  ctx.moveTo(len/2-5,-4); ctx.lineTo(len/2,0); ctx.lineTo(len/2-5,4);
  ctx.stroke(); ctx.restore();
}}

function hexToRgb(hex) {{
  const r=parseInt(hex.slice(1,3),16), g=parseInt(hex.slice(3,5),16), b=parseInt(hex.slice(5,7),16);
  return r+','+g+','+b;
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

// ── Scene draw ────────────────────────────────────────────────────────────────
function drawScene() {{
  const g = geo();
  ctx.clearRect(0,0,W,H);

  const bgColor = MODE==='NIGHT' ? '#060810' : '#0e1117';
  ctx.fillStyle = bgColor;
  ctx.fillRect(0,0,W,H);

  const {{ laneW, axA, axB, axC, roadY, rbR, sideNy, sideSy }} = g;

  // Grid
  ctx.strokeStyle='rgba(255,255,255,0.03)'; ctx.lineWidth=1;
  for (let gx=0;gx<W;gx+=60){{ ctx.beginPath();ctx.moveTo(gx,0);ctx.lineTo(gx,H);ctx.stroke(); }}
  for (let gy=0;gy<H;gy+=60){{ ctx.beginPath();ctx.moveTo(0,gy);ctx.lineTo(W,gy);ctx.stroke(); }}

  // Boulevard highlight
  const blvdHL = MODE==='EMERGENCY' ? 'rgba(34,197,94,0.14)' : 'rgba(123,140,222,0.10)';
  ctx.fillStyle=blvdHL; ctx.fillRect(0, roadY-laneW*2.5, W, laneW*5);

  // Road surface
  drawRoad(0, roadY, W, roadY, laneW, '#1a1a2e');

  // Lane edge markings
  ctx.strokeStyle='rgba(255,255,255,0.14)'; ctx.lineWidth=2;
  ctx.beginPath();ctx.moveTo(0,roadY-laneW*2);ctx.lineTo(W,roadY-laneW*2);ctx.stroke();
  ctx.beginPath();ctx.moveTo(0,roadY+laneW*2);ctx.lineTo(W,roadY+laneW*2);ctx.stroke();
  drawDash(0,roadY,W,roadY);

  // Side street — int_A north
  drawRoad(axA, roadY, axA, sideNy, laneW, '#1a1a2e');
  ctx.strokeStyle='rgba(255,255,255,0.09)'; ctx.lineWidth=1.5;
  ctx.beginPath();ctx.moveTo(axA-laneW*2,roadY);ctx.lineTo(axA-laneW*2,sideNy);ctx.stroke();
  ctx.beginPath();ctx.moveTo(axA+laneW*2,roadY);ctx.lineTo(axA+laneW*2,sideNy);ctx.stroke();
  drawDash(axA, roadY, axA, sideNy);

  // Side street — int_C south
  drawRoad(axC, roadY, axC, sideSy, laneW, '#1a1a2e');
  ctx.strokeStyle='rgba(255,255,255,0.09)'; ctx.lineWidth=1.5;
  ctx.beginPath();ctx.moveTo(axC-laneW*2,roadY);ctx.lineTo(axC-laneW*2,sideSy);ctx.stroke();
  ctx.beginPath();ctx.moveTo(axC+laneW*2,roadY);ctx.lineTo(axC+laneW*2,sideSy);ctx.stroke();
  drawDash(axC, roadY, axC, sideSy);

  // Roundabout — outer ring
  ctx.beginPath(); ctx.arc(axB, roadY, rbR+laneW, 0, Math.PI*2);
  ctx.fillStyle='#1a1a2e'; ctx.fill();
  // Inner island
  ctx.beginPath(); ctx.arc(axB, roadY, rbR-laneW*1.6, 0, Math.PI*2);
  ctx.fillStyle=bgColor; ctx.fill();
  // Island centre
  ctx.beginPath(); ctx.arc(axB, roadY, laneW*1.3, 0, Math.PI*2);
  ctx.fillStyle='#2a3045'; ctx.fill();
  ctx.font=`bold ${{Math.floor(laneW*0.9)}}px Arial`;
  ctx.fillStyle='#56cfb2'; ctx.textAlign='center'; ctx.textBaseline='middle';
  ctx.fillText('B', axB, roadY);
  // Clockwise direction arrows on ring
  const arrowR = rbR - laneW*0.65;
  for (let a=0; a<Math.PI*2; a+=Math.PI/3) {{
    const ax2 = axB + Math.cos(a)*arrowR;
    const ay2 = roadY + Math.sin(a)*arrowR;
    drawArrow(ax2, ay2, a + Math.PI/2, 'rgba(255,255,255,0.22)', 10);
  }}
  // Outer border glow
  ctx.beginPath(); ctx.arc(axB, roadY, rbR+laneW, 0, Math.PI*2);
  ctx.strokeStyle='rgba(86,207,178,0.28)'; ctx.lineWidth=1.5; ctx.stroke();

  // Intersection pads A and C
  [[axA,roadY,'#7b8cde','A'],[axC,roadY,'#f97316','C']].forEach(([ix,iy,ic,il]) => {{
    ctx.fillStyle='#1a1a2e';
    ctx.fillRect(ix-laneW*2.2, iy-laneW*2.2, laneW*4.4, laneW*4.4);
    ctx.font=`bold ${{Math.floor(laneW*0.85)}}px Arial`;
    ctx.fillStyle=ic; ctx.textAlign='center'; ctx.textBaseline='middle';
    ctx.fillText(il, ix, iy);
  }});

  // Traffic light dots
  const tlOff = laneW*2.9;
  drawTLDot(axA-tlOff, roadY-laneW, tlColor(TL.A,'ew'));
  drawTLDot(axA+laneW, roadY-tlOff, tlColor(TL.A,'ns'));
  drawTLDot(axB-rbR-laneW*1.2, roadY, tlColor(TL.B,'ew'));
  drawTLDot(axB+rbR+laneW*1.2, roadY, tlColor(TL.B,'ew'));
  drawTLDot(axB, roadY-rbR-laneW*1.2, tlColor(TL.B,'ns'));
  drawTLDot(axB, roadY+rbR+laneW*1.2, tlColor(TL.B,'ns'));
  drawTLDot(axC+tlOff, roadY+laneW, tlColor(TL.C,'ew'));
  drawTLDot(axC-laneW, roadY+tlOff, tlColor(TL.C,'ns'));

  // Labels
  ctx.textAlign='center';
  ctx.font=`${{Math.floor(laneW*0.7)}}px Arial`; ctx.fillStyle='rgba(255,255,255,0.28)';
  ctx.fillText('← WEST', laneW*3.5, roadY-laneW*3.2);
  ctx.fillText('EAST →', W-laneW*3.5, roadY-laneW*3.2);
  ctx.fillStyle='#7b8cde'; ctx.fillText('int_A', axA, sideNy-laneW*2);
  ctx.fillStyle='#f97316'; ctx.fillText('int_C', axC, sideSy+laneW*2);
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
    [[axA,roadY,'#7b8cde'],[axB,roadY,'#56cfb2'],[axC,roadY,'#f97316']].forEach(([x,y,c]) => {{
      ctx.beginPath(); ctx.arc(x,y,rbR*1.6,0,Math.PI*2);
      ctx.fillStyle='rgba('+hexToRgb(c)+',0.04)'; ctx.fill();
    }});
  }}
}}

// ── Status panel ──────────────────────────────────────────────────────────────
function statusColor(wait) {{
  if (wait < 30) return ['#22c55e','Flowing',   '#22c55e22'];
  if (wait < 70) return ['#f97316','Moderate',  '#f9731622'];
  return               ['#ef4444','Congested', '#ef444422'];
}}

function phaseName(p) {{
  return ['NS Green','NS Yellow','EW Green','EW Yellow'][p] ?? '—';
}}

function updatePanel() {{
  const modeLabels = {{ NORMAL:'🟢 NORMAL', EMERGENCY:'🚨 EMERGENCY', ACCIDENT:'⚠️ ACCIDENT', NIGHT:'🌙 NIGHT MODE' }};
  const modeColors = {{ NORMAL:'#22c55e', EMERGENCY:'#ef4444', ACCIDENT:'#fbbf24', NIGHT:'#7b8cde' }};
  const mb = document.getElementById('mode-badge');
  mb.textContent = modeLabels[MODE]||MODE;
  mb.style.color = modeColors[MODE]||'#e0e0e0';
  mb.style.borderColor = (modeColors[MODE]||'#2a3045')+'44';

  [['A',TL.A,'a'],['B',TL.B,'b'],['C',TL.C,'c']].forEach(([k,tl,id]) => {{
    const s = simStats[k];
    // Ensure wait is always a finite number for display
    const displayWait = isFinite(s.wait) ? s.wait : 0;
    const [sc,sl,sbg] = statusColor(displayWait);
    document.getElementById(id+'-phase').textContent = phaseName(tl.phase);
    document.getElementById(id+'-count').textContent = s.vc;
    document.getElementById(id+'-wait').textContent  = displayWait.toFixed(1)+' s';
    const badge = document.getElementById(id+'-badge');
    badge.textContent      = sl;
    badge.style.color      = sc;
    badge.style.background = sbg;
    badge.style.border     = '1px solid '+sc+'66';
  }});
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
