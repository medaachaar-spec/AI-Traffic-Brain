"""
dashboard/intersection_diagram.py

Reusable top-down 4-way intersection SVG component.

Usage:
    from dashboard.intersection_diagram import render_intersection
    render_intersection(phase="NS", north_wait=42.3, south_wait=38.1)
"""

import streamlit as st


def render_intersection(
    *,
    width: int = 460,
    v_lanes: int = 4,        # total lanes on vertical road   (must be even)
    h_lanes: int = 2,        # total lanes on horizontal road (must be even)
    lane_px: int = 28,       # pixels per lane — scales both roads
    phase: str | None = None,          # "NS" → N/S green | "EW" → E/W green | None → all red
    north_wait: float | None = None,   # optional approach wait-time labels (seconds)
    south_wait: float | None = None,
    east_wait: float | None = None,
    west_wait: float | None = None,
    bg: str = "#0a0e1a",
    road: str = "#1c2333",
    mark: str = "rgba(255,255,255,0.28)",
    divider: str = "#f59e0b",
    stopline: str = "#e2e8f0",
) -> None:
    """
    Render a top-down 4-way intersection using inline SVG via st.html().

    Tweak guide
    -----------
    width     – overall canvas pixels (square).
    v_lanes   – lanes on vertical road; increase to 6 for 3-lane-each-way.
    h_lanes   – lanes on horizontal road; increase to 4 for equal-width roads.
    lane_px   – single lane width in px; raise to 32–36 for a roomier look.
    phase     – "NS" lights north/south green, "EW" lights east/west green.
    bg / road – background and asphalt colors.
    divider   – center-line color (default amber).
    stopline  – stop-line color (default near-white).
    """
    h = width                           # square canvas
    cx, cy = width // 2, h // 2

    vw = v_lanes * lane_px              # vertical road width   e.g. 4×28 = 112 px
    hw = h_lanes * lane_px              # horizontal road width e.g. 2×28 =  56 px

    vl = cx - vw // 2                   # vertical road: left edge
    vr = cx + vw // 2                   # vertical road: right edge
    ht = cy - hw // 2                   # horizontal road: top edge
    hb = cy + hw // 2                   # horizontal road: bottom edge

    # Intersection bounding box
    ix, iy, iw, ih = vl, ht, vw, hw

    # Corner radius & stop-line setback (px)
    cr = 10
    SL = cr + 6

    # ── Signal colors ─────────────────────────────────────────────────────
    ns_col = "#22c55e" if phase == "NS" else "#ef4444"
    ew_col = "#22c55e" if phase == "EW" else "#ef4444"

    # ── SVG defs: arrowhead marker ────────────────────────────────────────
    defs = (
        '<defs>'
        '<marker id="arr" markerWidth="7" markerHeight="7"'
        ' refX="4" refY="3.5" orient="auto">'
        '<path d="M0,0.5 L0,6.5 L7,3.5 Z" fill="rgba(255,255,255,0.55)"/>'
        '</marker>'
        '</defs>'
    )

    # ── Road base rectangles ──────────────────────────────────────────────
    roads = (
        f'<rect x="{vl}" y="0" width="{vw}" height="{h}" fill="{road}"/>'
        f'<rect x="0" y="{ht}" width="{width}" height="{hw}" fill="{road}"/>'
    )

    # ── Corner rounding: pie-slice extensions + curb arc strokes ─────────
    #
    # Each pie slice fills the road color into the background corner area,
    # creating the illusion of a rounded curb. Curb arcs add a subtle stroke.
    #
    # Convention: SVG y increases downward.
    #   NW corner = (vl, iy)  → upper-left  → CW arc
    #   NE corner = (vr, iy)  → upper-right → CCW arc
    #   SW corner = (vl, iy+ih) → lower-left  → CCW arc
    #   SE corner = (vr, iy+ih) → lower-right → CW arc

    def _pie(ox, oy, dx, dy, sw):
        """Quarter-circle pie slice centered at (ox,oy), sweep sw (0=CCW,1=CW)."""
        return (
            f'<path d="M{ox},{oy} L{ox},{oy+dy} A{cr},{cr} 0 0,{sw} {ox+dx},{oy} Z"'
            f' fill="{road}"/>'
        )

    def _curb(x1, y1, x2, y2, sw):
        return (
            f'<path d="M{x1},{y1} A{cr},{cr} 0 0,{sw} {x2},{y2}"'
            f' fill="none" stroke="#475569" stroke-width="1.5"/>'
        )

    corners = (
        _pie(vl,  iy,      0,  -cr,  1) +  # NW: line up → arc to left
        _pie(vr,  iy,      cr, -cr,  0) +  # NE: line up → arc to right
        _pie(vl,  iy + ih, -cr, cr,  0) +  # SW: line down → arc to left
        _pie(vr,  iy + ih,  cr,  cr, 1)    # SE: line down → arc to right
    )
    curbs = (
        _curb(vl,       iy - cr, vl - cr, iy,       1) +
        _curb(vr,       iy - cr, vr + cr, iy,       0) +
        _curb(vl,  iy + ih + cr, vl - cr, iy + ih,  0) +
        _curb(vr,  iy + ih + cr, vr + cr, iy + ih,  1)
    )

    # ── Lane separators (drawn outside the intersection box only) ─────────
    lane_marks = []

    def _vsep(lx, is_center):
        col_ = divider if is_center else mark
        dash = "none" if is_center else "8,5"
        sw   = 2      if is_center else 1
        lane_marks.append(
            f'<line x1="{lx}" y1="0" x2="{lx}" y2="{iy - SL}"'
            f' stroke="{col_}" stroke-width="{sw}" stroke-dasharray="{dash}"/>'
            f'<line x1="{lx}" y1="{iy + ih + SL}" x2="{lx}" y2="{h}"'
            f' stroke="{col_}" stroke-width="{sw}" stroke-dasharray="{dash}"/>'
        )

    def _hsep(ly, is_center):
        col_ = divider if is_center else mark
        dash = "none" if is_center else "8,5"
        sw   = 2      if is_center else 1
        lane_marks.append(
            f'<line x1="0" y1="{ly}" x2="{ix - SL}" y2="{ly}"'
            f' stroke="{col_}" stroke-width="{sw}" stroke-dasharray="{dash}"/>'
            f'<line x1="{ix + iw + SL}" y1="{ly}" x2="{width}" y2="{ly}"'
            f' stroke="{col_}" stroke-width="{sw}" stroke-dasharray="{dash}"/>'
        )

    for i in range(1, v_lanes):
        _vsep(vl + i * lane_px, i == v_lanes // 2)
    for i in range(1, h_lanes):
        _hsep(ht + i * lane_px, i == h_lanes // 2)

    # ── Stop lines ────────────────────────────────────────────────────────
    # Right-hand traffic convention:
    #   Southbound (coming from N): stops at y = iy-SL, on the WEST half (x: vl..cx)
    #   Northbound (coming from S): stops at y = iy+ih+SL, on the EAST half (x: cx..vr)
    #   Eastbound  (coming from W): stops at x = ix-SL, on the SOUTH half (y: cy..hb)
    #   Westbound  (coming from E): stops at x = ix+iw+SL, on the NORTH half (y: ht..cy)
    stop_lines = (
        # Full-width stop lines (simpler read on small canvas)
        f'<line x1="{vl+2}" y1="{iy-SL}" x2="{vr-2}" y2="{iy-SL}"'
        f' stroke="{stopline}" stroke-width="3" stroke-linecap="round"/>'
        f'<line x1="{vl+2}" y1="{iy+ih+SL}" x2="{vr-2}" y2="{iy+ih+SL}"'
        f' stroke="{stopline}" stroke-width="3" stroke-linecap="round"/>'
        f'<line x1="{ix-SL}" y1="{ht+2}" x2="{ix-SL}" y2="{hb-2}"'
        f' stroke="{stopline}" stroke-width="3" stroke-linecap="round"/>'
        f'<line x1="{ix+iw+SL}" y1="{ht+2}" x2="{ix+iw+SL}" y2="{hb-2}"'
        f' stroke="{stopline}" stroke-width="3" stroke-linecap="round"/>'
    )

    # ── Direction arrows inside intersection ──────────────────────────────
    AL  = max(20, ih - 12)     # arrow length (capped to intersection height)
    ALh = max(16, iw // 2 - 8) # horizontal arrow length

    # Right-hand traffic lane centers inside the intersection:
    sb_x = cx - lane_px // 2   # southbound (west half of vertical road)
    nb_x = cx + lane_px // 2   # northbound (east half)
    eb_y = cy + lane_px // 4   # eastbound  (south half of horizontal road)
    wb_y = cy - lane_px // 4   # westbound  (north half)

    arrows = (
        # Southbound ↓
        f'<line x1="{sb_x}" y1="{iy+6}" x2="{sb_x}" y2="{iy+6+AL}"'
        f' stroke="rgba(255,255,255,0.5)" stroke-width="1.5" marker-end="url(#arr)"/>'
        # Northbound ↑
        f'<line x1="{nb_x}" y1="{iy+ih-6}" x2="{nb_x}" y2="{iy+ih-6-AL}"'
        f' stroke="rgba(255,255,255,0.5)" stroke-width="1.5" marker-end="url(#arr)"/>'
        # Eastbound →
        f'<line x1="{ix+6}" y1="{eb_y}" x2="{ix+6+ALh}" y2="{eb_y}"'
        f' stroke="rgba(255,255,255,0.5)" stroke-width="1.5" marker-end="url(#arr)"/>'
        # Westbound ←
        f'<line x1="{ix+iw-6}" y1="{wb_y}" x2="{ix+iw-6-ALh}" y2="{wb_y}"'
        f' stroke="rgba(255,255,255,0.5)" stroke-width="1.5" marker-end="url(#arr)"/>'
    )

    # ── Traffic light boxes ───────────────────────────────────────────────
    TW, TH = 10, 22

    def _tl(x, y, active_col, rotate=0):
        g  = f'<g transform="translate({x},{y}) rotate({rotate})">'
        g += (
            f'<rect x="{-TW//2}" y="{-TH//2}" width="{TW}" height="{TH}"'
            f' rx="4" fill="#111827" stroke="rgba(255,255,255,0.15)" stroke-width="1"/>'
            f'<circle cx="0" cy="{-TH//3}" r="3" fill="#ef4444"/>'
            f'<circle cx="0" cy="0" r="3" fill="#f59e0b" opacity="0.3"/>'
            f'<circle cx="0" cy="{TH//3}" r="3" fill="{active_col}" opacity="0.95"/>'
        )
        g += '</g>'
        return g

    off = 18  # offset from road edge
    traffic_lights = (
        # Southbound approach (from N): driver's right = WEST side, near north stop line
        _tl(vl - off, iy - TH // 2, ns_col) +
        # Northbound approach (from S): driver's right = EAST side, near south stop line
        _tl(vr + off, iy + ih + TH // 2, ns_col) +
        # Eastbound approach (from W): driver's right = NORTH side, near west stop line
        _tl(ix - TH // 2, ht - off, ew_col, rotate=90) +
        # Westbound approach (from E): driver's right = SOUTH side, near east stop line
        _tl(ix + iw + TH // 2, hb + off, ew_col, rotate=90)
    )

    # ── Approach labels ───────────────────────────────────────────────────
    mono = "'Space Mono','Courier New',monospace"
    lbl  = f'font-family:{mono};font-size:10px;fill:#64748b;letter-spacing:0.05em'
    val  = f'font-family:{mono};font-size:12px;font-weight:700;fill:#e2e8f0'

    def _label(x, y, direction, wait, anchor="middle"):
        s = f'<text x="{x}" y="{y}" text-anchor="{anchor}" style="{lbl}">{direction}</text>'
        if wait is not None:
            s += f'<text x="{x}" y="{y+15}" text-anchor="{anchor}" style="{val}">{wait:.0f}s</text>'
        return s

    labels = (
        _label(cx,         16,      "NORTH", north_wait) +
        _label(cx,         h - 4,   "SOUTH", south_wait) +
        _label(8,          cy - 8,  "WEST",  west_wait,  anchor="start") +
        _label(width - 8,  cy - 8,  "EAST",  east_wait,  anchor="end")
    )

    # ── Assemble SVG ──────────────────────────────────────────────────────
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{h}" '
        f'style="background:{bg};border-radius:12px;display:block;margin:auto;">'
        + defs
        + roads
        + corners
        + curbs
        + "".join(lane_marks)
        + stop_lines
        + arrows
        + traffic_lights
        + labels
        + '</svg>'
    )

    st.html(f'<div style="display:flex;justify-content:center;padding:8px 0;">{svg}</div>')
