#!/usr/bin/env python3
"""
GenoMAX² V7 — Design System v1.0 Implementation
=================================================
Clean rewrite. Reuses only: text primitives, QR, crop marks, parse_back_text, pipeline.

Design tokens:
  Safe area: 28px
  Spacing:   8 / 12 / 16 / 24 / 32 / 48 / 64
  Fonts:     IBM Plex Mono only (Regular/Medium/SemiBold/Bold)
"""

import json, os, sys, re, argparse, io, shutil
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from reportlab.lib.units import inch, mm
from reportlab.lib.colors import CMYKColor, Color
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
import qrcode
from PIL import Image

# ─── PATHS ────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
BASE = SCRIPT_DIR.parent
FONTS_DIR = BASE / "design-system" / "fonts"
DATA_DIR = BASE / "design-system" / "data"
OUTPUT_BASE = BASE / "design-system" / "production-v7"

# ─── FONTS (IBM Plex Mono only per Design System v1.0) ───────────────────
FONT_MAP = {
    "Mono":         "IBMPlexMono-Regular.ttf",
    "Mono-Medium":  "IBMPlexMono-Medium.ttf",
    "Mono-SemiBold":"IBMPlexMono-SemiBold.ttf",
    "Mono-Bold":    "IBMPlexMono-Bold.ttf",
    "Mono-Light":   "IBMPlexMono-Light.ttf",
    # Condensed fallbacks for overflow cascading
    "Cond":         "IBMPlexSansCondensed-Regular.ttf",
    "Cond-Medium":  "IBMPlexSansCondensed-Medium.ttf",
    "Cond-SemiBold":"IBMPlexSansCondensed-SemiBold.ttf",
    "Cond-Bold":    "IBMPlexSansCondensed-Bold.ttf",
}
for name, fn in FONT_MAP.items():
    p = FONTS_DIR / fn
    if p.exists():
        pdfmetrics.registerFont(TTFont(name, str(p)))

COND_MAP = {
    "Mono-Bold": "Cond-Bold",
    "Mono-SemiBold": "Cond-SemiBold",
    "Mono-Medium": "Cond-Medium",
    "Mono": "Cond",
}

# ─── COLORS ──────────────────────────────────────────────────────────────
def h2c(h):
    h = h.lstrip('#')
    r, g, b = int(h[0:2],16)/255, int(h[2:4],16)/255, int(h[4:6],16)/255
    k = 1 - max(r, g, b)
    if k == 1:
        return CMYKColor(0, 0, 0, 1)
    return CMYKColor((1-r-k)/(1-k), (1-g-k)/(1-k), (1-b-k)/(1-k), k)

C = {
    "bg":       h2c("#F4F2EC"),
    "t1":       h2c("#1A1815"),   # primary text
    "t2":       h2c("#4A4843"),   # secondary
    "t3":       h2c("#8A8880"),   # tertiary
    "div":      h2c("#C5C2BA"),
    "ax_mo":    h2c("#7A1E2E"),   # MAXimo accent
    "ax_ma":    h2c("#7A304A"),   # MAXima accent
    "footer_bg":h2c("#6A6A72"),   # V7: updated footer bg
    "white":    CMYKColor(0, 0, 0, 0),
}

# ─── DESIGN TOKENS ───────────────────────────────────────────────────────
BLEED = 3 * mm
SAFE = 28          # V7: 28px safe area
SP = {1: 8, 2: 12, 3: 16, 4: 24, 5: 32, 6: 48, 7: 64}

# QR sizes per format
QR_SIZES = {"BOTTLE": 84, "JAR": 78, "POUCH": 78, "DROPPER": 72, "STRIPS": 72}
QR_GAP = 24  # minimum gap between QR and text

FORMAT_DIMS = {
    "BOTTLE":  {"w": 6*inch,   "h": 2.5*inch},
    "JAR":     {"w": 8.5*inch, "h": 2*inch},
    "POUCH":   {"w": 5*inch,   "h": 4*inch},
    "DROPPER": {"w": 2*inch,   "h": 4*inch},
    "STRIPS":  {"w": 4*inch,   "h": 6.5*inch},
}

# Product name size ranges per format
PN_RANGE = {
    "BOTTLE":  (26, 28),
    "JAR":     (24, 27),
    "POUCH":   (24, 27),
    "DROPPER": (20, 24),
    "STRIPS":  (24, 28),
}


# ═══════════════════════════════════════════════════════════════════════════
# TEXT PRIMITIVES (reused from V6, IBM Plex Mono only)
# ═══════════════════════════════════════════════════════════════════════════

def _tw(t, f, s):
    """Measure text width."""
    return pdfmetrics.stringWidth(t, f, s)


def _d(c, x, y, t, f, s, co, alpha=1.0):
    """Draw text at exact position."""
    if alpha < 1.0:
        c.saveState()
        c.setFillAlpha(alpha)
    o = c.beginText(x, y)
    o.setFont(f, s)
    o.setFillColor(co)
    o.setCharSpace(0)
    o.textOut(t)
    c.drawText(o)
    if alpha < 1.0:
        c.restoreState()


def _dt(c, x, y, t, f, s, co, tr, mw=None, alpha=1.0):
    """Draw tracked text with cascading fit: tracking->shrink->condensed->shrink more."""
    orig_s = s
    orig_f = f

    if mw and t:
        def _tracked_w(txt, sz, trk, font=f):
            return _tw(txt, font, sz) + max(0, len(txt)-1) * sz * trk

        # Step 1: reduce tracking to 0
        if _tracked_w(t, s, tr) > mw:
            for test_tr in [tr * 0.6, tr * 0.3, 0]:
                if _tracked_w(t, s, test_tr) <= mw:
                    tr = test_tr
                    break
            else:
                tr = 0

        # Step 2: shrink font up to -25%
        while _tracked_w(t, s, tr) > mw and s > orig_s * 0.75:
            s -= 0.25

        # Step 3: condensed fallback
        if _tracked_w(t, s, tr) > mw:
            alt = COND_MAP.get(f)
            if alt:
                try:
                    if _tracked_w(t, s, tr, alt) <= mw:
                        f = alt
                except:
                    pass

        # Step 4: emergency shrink to -40%
        while _tracked_w(t, s, tr) > mw and s > orig_s * 0.60:
            s -= 0.25

        # Step 5: absolute floor 6pt
        while _tracked_w(t, s, tr) > mw and s > 6:
            s -= 0.25

        # Step 6: truncate with ellipsis if still overflows
        if _tracked_w(t, s, tr) > mw and len(t) > 3:
            while len(t) > 3 and _tracked_w(t + "...", s, tr) > mw:
                t = t[:-1].rstrip()
            t = t + "..."

    if alpha < 1.0:
        c.saveState()
        c.setFillAlpha(alpha)
    o = c.beginText(x, y)
    o.setFont(f, s)
    o.setFillColor(co)
    o.setCharSpace(s * tr)
    o.textOut(t)
    c.drawText(o)
    if alpha < 1.0:
        c.restoreState()


def _dc(c, x, y, t, f, s, co, mw, alpha=1.0):
    """Draw clamped text with cascading fit: shrink->condensed->shrink more."""
    orig_s = s
    # Step 1: shrink up to -20%
    while _tw(t, f, s) > mw and s > orig_s * 0.80:
        s -= 0.25
    # Step 2: condensed fallback
    if _tw(t, f, s) > mw:
        alt = COND_MAP.get(f)
        if alt:
            s_try = orig_s
            while _tw(t, alt, s_try) > mw and s_try > orig_s * 0.80:
                s_try -= 0.25
            if _tw(t, alt, s_try) <= mw:
                f = alt
                s = s_try
    # Step 3: emergency shrink to -40%
    while _tw(t, f, s) > mw and s > orig_s * 0.60:
        s -= 0.25
    # Step 4: absolute floor 6pt
    while _tw(t, f, s) > mw and s > 6:
        s -= 0.25
    # Step 5: truncate with ellipsis if still overflows
    if _tw(t, f, s) > mw and len(t) > 3:
        while len(t) > 3 and _tw(t + "...", f, s) > mw:
            t = t[:-1].rstrip()
        t = t + "..."
    _d(c, x, y, t, f, s, co, alpha)


def _dr(c, xr, y, t, f, s, co, alpha=1.0):
    """Draw right-aligned text."""
    _d(c, xr - _tw(t, f, s), y, t, f, s, co, alpha)


def _w(t, f, s, mw):
    """Word-wrap text. Handles single words wider than mw via char-break."""
    words, lines, cur = t.split(), [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if _tw(test, f, s) <= mw:
            cur = test
        else:
            if cur:
                lines.append(cur)
            if _tw(w, f, s) > mw:
                chunk = ""
                for ch in w:
                    if _tw(chunk + ch, f, s) <= mw:
                        chunk += ch
                    else:
                        if chunk:
                            lines.append(chunk)
                        chunk = ch
                cur = chunk
            else:
                cur = w
    if cur:
        lines.append(cur)
    return lines


def make_qr(url):
    qr = qrcode.QRCode(version=2, error_correction=qrcode.constants.ERROR_CORRECT_M,
                        box_size=8, border=1)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return ImageReader(buf)


def crop_marks(c, tx, ty, w, h):
    c.setStrokeColor(CMYKColor(0, 0, 0, 1))
    c.setLineWidth(0.25)
    L, O = 12, 3
    for p in [
        (tx-O, ty+h, tx-O-L, ty+h), (tx, ty+h+O, tx, ty+h+O+L),
        (tx+w+O, ty+h, tx+w+O+L, ty+h), (tx+w, ty+h+O, tx+w, ty+h+O+L),
        (tx-O, ty, tx-O-L, ty), (tx, ty-O, tx, ty-O-L),
        (tx+w+O, ty, tx+w+O+L, ty), (tx+w, ty-O, tx+w, ty-O-L),
    ]:
        c.line(*p)


# ═══════════════════════════════════════════════════════════════════════════
# BACK LABEL TEXT PARSER (reused from V6)
# ═══════════════════════════════════════════════════════════════════════════

def parse_back_text(raw):
    sections = {
        "context": "", "suggested_use": "", "cta_line": "",
        "warnings": [], "ingredients": "",
    }
    lines = raw.split('\n')
    current_section = None
    buffer = []

    def flush():
        nonlocal buffer
        if current_section and buffer:
            text = ' '.join(buffer).strip()
            if current_section == "context":
                sections["context"] = text
            elif current_section == "suggested_use":
                sections["suggested_use"] += (" " + text if sections["suggested_use"] else text)
            elif current_section == "warnings":
                if text:
                    sections["warnings"].append(text)
            elif current_section == "ingredients":
                sections["ingredients"] = text
            elif current_section == "cta_line":
                sections["cta_line"] = text
        buffer = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush()
            continue
        if stripped in ("This is not your full protocol.", "[QR]", "Scan to begin", "genomax.ai"):
            continue
        if stripped.startswith("Distributed by"):
            continue

        if stripped == "Suggested Use:":
            flush()
            current_section = "suggested_use"
            continue
        elif stripped == "Warnings:":
            flush()
            current_section = "warnings"
            continue
        elif stripped.startswith("Ingredients:"):
            flush()
            current_section = "ingredients"
            rest = stripped[len("Ingredients:"):].strip()
            if rest:
                buffer.append(rest)
            continue
        elif stripped.startswith("Often used in"):
            flush()
            current_section = "cta_line"
            buffer.append(stripped)
            continue

        if current_section is None:
            current_section = "context"
        buffer.append(stripped)

    flush()
    return sections


# ═══════════════════════════════════════════════════════════════════════════
# V7 TYPOGRAPHY SPEC
# ═══════════════════════════════════════════════════════════════════════════
# All IBM Plex Mono. Weight mapping: 400=Regular, 500=Medium, 600=SemiBold, 700=Bold
TYPO = {
    "brand":        {"font": "Mono-Medium",   "size": 13,   "track": 0.08,  "alpha": 1.0,  "lh": 1.0},
    "system":       {"font": "Mono",          "size": 9,    "track": 0.14,  "alpha": 0.72, "lh": 1.0},
    "product":      {"font": "Mono-Bold",     "size": 27,   "track": 0,     "alpha": 1.0,  "lh": 1.02},
    "subtitle":     {"font": "Mono-Medium",   "size": 14,   "track": 0,     "alpha": 0.88, "lh": 1.15},
    "meta_label":   {"font": "Mono",          "size": 10,   "track": 0.08,  "alpha": 0.58, "lh": 1.0},
    "meta_value":   {"font": "Mono-SemiBold", "size": 10.5, "track": 0,     "alpha": 0.92, "lh": 1.25},
    "back_title":   {"font": "Mono-Bold",     "size": 18,   "track": 0.04,  "alpha": 1.0,  "lh": 1.08},
    "back_section": {"font": "Mono-Medium",   "size": 9,    "track": 0.14,  "alpha": 0.58, "lh": 1.0},
    "back_body":    {"font": "Mono",          "size": 10.5, "track": 0,     "alpha": 0.88, "lh": 1.32},
    "footer":       {"font": "Mono",          "size": 9,    "track": 0.06,  "alpha": 1.0,  "lh": 1.0},
}


# ═══════════════════════════════════════════════════════════════════════════
# V7 FOOTER
# ═══════════════════════════════════════════════════════════════════════════
def footer_height(fmt):
    """V7 footer: ~25% smaller than V6.4."""
    # V6.4 strip was int(16 * 0.42) ~ 6-8px. V7: fixed 18px for consistency.
    # This gives 8px top/bottom padding around 9px text.
    return 18 if fmt != "DROPPER" else 20


def draw_footer(c, tx, ty, w, fmt, left_text, right_text):
    """Draw footer bar with V7 Design System styling."""
    fh = footer_height(fmt)
    narrow = fmt == "DROPPER"
    left = tx + SAFE
    right_ = tx + w - SAFE
    cw = right_ - left

    # Background
    c.setFillColor(C["footer_bg"])
    c.rect(tx - BLEED, ty - BLEED, w + 2*BLEED, fh + BLEED, fill=1, stroke=0)

    ft = TYPO["footer"]
    fsz = ft["size"]
    if narrow:
        fsz = 5
    elif fmt == "JAR":
        fsz = 7.5

    c.saveState()
    c.setFillAlpha(0.88)

    if narrow:
        # Stack text vertically for narrow formats
        line1_y = ty + fh - 4 - fsz
        line2_y = line1_y - fsz - 1
        _dc(c, left, line1_y, left_text, ft["font"], fsz, C["white"], cw, alpha=1.0)
        _dc(c, left, line2_y, right_text, ft["font"], fsz, C["white"], cw, alpha=1.0)
    else:
        text_y = ty + (fh - fsz) / 2
        # Left text
        _dc(c, left, text_y, left_text, ft["font"], fsz, C["white"], cw * 0.55, alpha=1.0)
        # Right text - shrink to fit
        _fsz = fsz
        while _tw(right_text, ft["font"], _fsz) > cw * 0.44 and _fsz > 5:
            _fsz -= 0.25
        rw = _tw(right_text, ft["font"], _fsz)
        _d(c, right_ - rw, text_y, right_text, ft["font"], _fsz, C["white"], alpha=1.0)

    c.restoreState()
    return fh


# ═══════════════════════════════════════════════════════════════════════════
# V7 FRONT LABEL (2-pass measure/distribute with proportional scaling)
# ═══════════════════════════════════════════════════════════════════════════

def render_front(c, sku, dims, accent, tx, ty):
    w, h = dims["w"], dims["h"]
    fmt = sku["format"]["label_format"]
    narrow = fmt == "DROPPER"
    short = fmt == "JAR"

    left = tx + SAFE
    right_ = tx + w - SAFE
    cw = right_ - left

    # ── Background + accent ceiling ──
    c.setFillColor(C["bg"])
    c.rect(tx - BLEED, ty - BLEED, w + 2*BLEED, h + 2*BLEED, fill=1, stroke=0)
    c.setFillColor(accent)
    c.rect(tx - BLEED, ty + h - 2, w + 2*BLEED, 2, fill=1, stroke=0)

    # ── Footer ──
    ver = sku["front_panel"]["zone_7"]["version_info"]
    qty = sku["front_panel"]["zone_7"]["net_quantity"]
    fh = draw_footer(c, tx, ty, w, fmt, ver, qty)
    content_floor = ty + fh + 4

    # ── Available height ──
    content_top = ty + h - SAFE
    avail = content_top - content_floor

    # ── Data extraction ──
    pn = sku["front_panel"]["zone_3"]["ingredient_name"]
    desc = sku["front_panel"]["zone_4"].get("descriptor", "")
    bio = sku["front_panel"]["zone_4"].get("biological_system", "")
    variant = sku["front_panel"]["zone_5"]["variant_name"]
    z6 = sku["front_panel"]["zone_6"]
    meta_items = [
        ("TYPE", z6["type"]["value"]),
        ("SYSTEM", (sku["front_panel"]["zone_4"].get("biological_system", "") or "").split("\u00b7")[0].strip()
                   or z6.get("status", {}).get("value", "") or "\u2014"),
        ("FUNCTION", z6["function"]["value"]),
    ]

    # ── PASS 1: Determine scale factor ──
    # Reference height is STRIPS (6.5" = 468pt), scale proportionally
    ref_avail = 468 - SAFE * 2 - 22  # ~390pt reference available
    scale = min(1.0, avail / ref_avail)
    # Clamp scale to reasonable range
    scale = max(0.35, scale)

    def sc(v):
        """Scale a value, with floor of 5."""
        return max(5, v * scale)

    # Scaled sizes
    brand_sz = sc(13)
    sys_sz = sc(9)
    pn_min_s, pn_max_s = sc(PN_RANGE[fmt][0]), sc(PN_RANGE[fmt][1])
    sub_sz = sc(14)
    bio_sz = sc(8)
    ml_sz = sc(10)
    mv_sz = sc(10.5)
    vs = sc(10)
    meta_lh = mv_sz * 1.2

    pn_t = TYPO["product"]

    # Adaptive product name sizing (max 3 lines, shrink->condense)
    pn_sz = pn_max_s
    pn_font = pn_t["font"]
    pn_lines = _w(pn, pn_font, pn_sz, cw)
    while len(pn_lines) > 3 and pn_sz > pn_min_s:
        pn_sz -= 0.5
        pn_lines = _w(pn, pn_font, pn_sz, cw)
    if len(pn_lines) > 3:
        alt = COND_MAP.get(pn_font)
        if alt:
            pn_sz_c = pn_max_s
            pn_lines_c = _w(pn, alt, pn_sz_c, cw)
            while len(pn_lines_c) > 3 and pn_sz_c > pn_min_s:
                pn_sz_c -= 0.5
                pn_lines_c = _w(pn, alt, pn_sz_c, cw)
            if len(pn_lines_c) <= 3:
                pn_font, pn_sz, pn_lines = alt, pn_sz_c, pn_lines_c
    pn_lines = pn_lines[:3]
    pn_lh = pn_sz * pn_t["lh"]

    # Subtitle lines
    sub_t = TYPO["subtitle"]
    sub_lines = []
    if desc:
        _ssz = sub_sz
        sub_lines = _w(desc, sub_t["font"], _ssz, cw)
        while len(sub_lines) > 2 and _ssz > 6:
            _ssz -= 0.5
            sub_lines = _w(desc, sub_t["font"], _ssz, cw)
        sub_lines = sub_lines[:2]
        sub_sz = _ssz
    sub_lh = sub_sz * sub_t["lh"]

    # Measure content heights
    use_grid_meta = short or fmt == "POUCH"  # 3-col grid for short/wide formats
    if use_grid_meta:
        meta_h = ml_sz + mv_sz * 1.05
    else:
        meta_h = 3 * meta_lh

    h_brand = brand_sz
    h_sys = sys_sz
    h_div = 4
    h_pn = len(pn_lines) * pn_lh
    h_sub = len(sub_lines) * sub_lh if sub_lines else 0
    h_bio = bio_sz if bio else 0
    h_meta = meta_h
    h_variant = vs + 4

    total_content = h_brand + h_sys + h_div + h_pn + h_sub + h_bio + h_meta + h_variant

    # Gaps (scaled from spec)
    gap_spec = [sc(24), sc(12), sc(24), sc(12) if sub_lines else 0,
                sc(16) if bio else 0, sc(32), sc(32)]
    gap_min = [4, 2, 4, 2 if sub_lines else 0, 2 if bio else 0, 4, 4]

    total_gap_spec = sum(gap_spec)
    total_gap_min = sum(gap_min)
    slack = avail - total_content

    if slack >= total_gap_spec:
        gaps = list(gap_spec)
    elif slack >= total_gap_min:
        ratio = (slack - total_gap_min) / max(1, total_gap_spec - total_gap_min)
        gaps = [gmin + (gspec - gmin) * ratio for gmin, gspec in zip(gap_min, gap_spec)]
    else:
        gaps = list(gap_min)
        # Emergency: further shrink product name
        while total_content + sum(gaps) > avail and pn_sz > 8:
            pn_sz -= 0.5
            pn_lines = _w(pn, pn_font, pn_sz, cw)[:3]
            pn_lh = pn_sz * pn_t["lh"]
            h_pn = len(pn_lines) * pn_lh
            total_content = h_brand + h_sys + h_div + h_pn + h_sub + h_bio + h_meta + h_variant
        # If still tight, drop bio
        if total_content + sum(gaps) > avail and bio:
            h_bio = 0
            gaps[4] = 0
            total_content = h_brand + h_sys + h_div + h_pn + h_sub + h_bio + h_meta + h_variant

    # ── PASS 2: DRAW ──
    cy = content_top

    # Brand
    cy -= gaps[0]
    _dt(c, left, cy - brand_sz, "GenoMAX\u00b2", TYPO["brand"]["font"], brand_sz,
        C["t1"], TYPO["brand"]["track"], mw=cw * 0.65, alpha=1.0)
    mc_sz = max(5, brand_sz * 0.55)
    _dr(c, right_, cy - mc_sz, sku["front_panel"]["zone_1"]["module_code"],
        "Mono-Medium", mc_sz, C["t3"], alpha=0.58)
    cy -= brand_sz

    # System line
    cy -= gaps[1]
    _dt(c, left, cy - sys_sz, sku["front_panel"]["zone_2"]["text"],
        TYPO["system"]["font"], sys_sz, C["t1"], TYPO["system"]["track"],
        mw=cw, alpha=TYPO["system"]["alpha"])
    cy -= sys_sz

    # Divider
    cy -= 2
    c.saveState()
    c.setStrokeColor(C["t1"]); c.setLineWidth(0.5); c.setStrokeAlpha(0.20)
    c.line(left, cy, right_, cy)
    c.restoreState()
    cy -= 2

    # Product name
    cy -= gaps[2]
    for ln in pn_lines:
        _dc(c, left, cy - pn_sz, ln, pn_font, pn_sz, C["t1"], cw, alpha=1.0)
        cy -= pn_lh

    # Subtitle
    if sub_lines:
        cy -= gaps[3]
        for ln in sub_lines:
            _dc(c, left, cy - sub_sz, ln, sub_t["font"], sub_sz, C["t1"], cw, alpha=TYPO["subtitle"]["alpha"])
            cy -= sub_lh

    # Biological system
    if h_bio > 0:
        cy -= gaps[4]
        _dc(c, left, cy - bio_sz, bio, "Mono", bio_sz, C["t3"], cw, alpha=0.58)
        cy -= bio_sz

    # Meta block
    cy -= gaps[5]
    ml_font = TYPO["meta_label"]["font"]
    mv_font = TYPO["meta_value"]["font"]

    if use_grid_meta:
        # 3-column grid
        col_w = cw / 3
        for idx, (label, val) in enumerate(meta_items):
            cx = left + idx * col_w
            _dt(c, cx, cy - ml_sz, label, ml_font, ml_sz, C["t1"],
                TYPO["meta_label"]["track"], mw=col_w - 4, alpha=TYPO["meta_label"]["alpha"])
            _dc(c, cx, cy - ml_sz - mv_sz * 1.05, val, mv_font, mv_sz,
                C["t1"], col_w - 4, alpha=TYPO["meta_value"]["alpha"])
        cy -= ml_sz + mv_sz * 1.05
    else:
        # Single-column stacked
        label_col_w = _tw("FUNCTION", ml_font, ml_sz) + ml_sz * TYPO["meta_label"]["track"] * 8 + 8
        for label, val in meta_items:
            _dt(c, left, cy - ml_sz, label, ml_font, ml_sz, C["t1"],
                TYPO["meta_label"]["track"], mw=label_col_w, alpha=TYPO["meta_label"]["alpha"])
            _dc(c, left + label_col_w, cy - mv_sz, val, mv_font, mv_sz,
                C["t1"], cw - label_col_w, alpha=TYPO["meta_value"]["alpha"])
            cy -= meta_lh

    # Variant + accent bar
    cy -= gaps[6]
    # Ensure we don't draw below floor
    if cy - vs > content_floor:
        _dc(c, left, cy - vs, variant, "Mono-SemiBold", vs, C["t1"], cw, alpha=1.0)
        cy -= vs + 2
        bar_w = min(70, cw * 0.3)
        if narrow:
            bar_w = 40
        c.setFillColor(accent)
        c.rect(left, cy - 2, bar_w, 2, fill=1, stroke=0)


# ═══════════════════════════════════════════════════════════════════════════
# V7 BACK LABEL
# ═══════════════════════════════════════════════════════════════════════════

def render_back(c, sku, dims, accent, tx, ty):
    w, h = dims["w"], dims["h"]
    fmt = sku["format"]["label_format"]
    narrow = fmt == "DROPPER"
    tall = fmt in ("STRIPS", "POUCH")
    short = fmt == "JAR"

    left = tx + SAFE
    right_ = tx + w - SAFE
    cw = right_ - left

    raw = sku.get("back_panel", {}).get("back_label_text", "")
    sec = parse_back_text(raw)

    # ── Background + ceiling ──
    c.setFillColor(C["bg"])
    c.rect(tx - BLEED, ty - BLEED, w + 2*BLEED, h + 2*BLEED, fill=1, stroke=0)
    c.setFillColor(accent)
    c.rect(tx - BLEED, ty + h - 2, w + 2*BLEED, 2, fill=1, stroke=0)

    # ── Footer ──
    fh = draw_footer(c, tx, ty, w, fmt,
                     "genomax.ai \u00b7 support@genomax.ai",
                     "Distributed by Genomax LLC")
    floor = ty + fh + 8  # small buffer above footer

    # ── QR setup: adaptive sizing ──
    # Spec QR sizes may be too large for tight formats; scale to fit
    qr_sz_spec = QR_SIZES[fmt]
    avail_h = (ty + h - SAFE) - floor
    # QR should use at most 35% of available height
    qr_sz = min(qr_sz_spec, int(avail_h * 0.35))
    if qr_sz < 24:
        qr_sz = 24  # absolute minimum for scannability

    mc = sku["_meta"]["module_code"]
    osn = sku["_meta"]["os"].replace("\u00b2", "2").replace("\u00b2", "2").lower()
    qr_img = make_qr(f"https://genomax.ai/module/{osn}/{mc.lower()}")

    # Side QR: BOTTLE and JAR place QR to the right of text
    has_qr_side = not narrow and not tall
    qr_reserve = (qr_sz + QR_GAP) if has_qr_side else 0
    tw = cw - qr_reserve

    # ── Adaptive body sizing ──
    bt = TYPO["back_title"]
    bs = TYPO["back_section"]
    bb = TYPO["back_body"]

    # Scale text sizes based on available height
    if avail_h < 120:  # very tight (JAR, BOTTLE)
        title_sz = 10
        sect_sz = 6.5
        body_sz = 7
        sgap = 4
    elif avail_h < 180:  # moderate
        title_sz = 12
        sect_sz = 7.5
        body_sz = 8
        sgap = 6
    elif narrow:
        title_sz = 12
        sect_sz = 7
        body_sz = 8
        sgap = 6
    else:  # tall/spacious
        title_sz = bt["size"]
        sect_sz = bs["size"]
        body_sz = bb["size"]
        sgap = SP[2]

    body_lh = body_sz * 1.25

    # ── START DRAWING (top-down) ──
    cy = ty + h - SAFE

    # 1. Brand
    brand_sz = min(10, title_sz * 0.6)
    if brand_sz < 6:
        brand_sz = 6
    _dt(c, left, cy - brand_sz, "GenoMAX\u00b2", "Mono-Bold", brand_sz,
        C["t1"], 0.08, mw=cw * 0.6, alpha=1.0)
    cy -= brand_sz + 3

    # Divider
    c.saveState()
    c.setStrokeColor(C["t1"]); c.setLineWidth(0.5); c.setStrokeAlpha(0.20)
    c.line(left, cy, right_, cy)
    c.restoreState()
    cy -= sgap

    # 2. "THIS IS NOT YOUR FULL PROTOCOL"
    proto_sz = title_sz
    proto_lines = _w("THIS IS NOT YOUR FULL PROTOCOL", "Mono-Bold", proto_sz, tw)
    while len(proto_lines) > 2 and proto_sz > 8:
        proto_sz -= 0.5
        proto_lines = _w("THIS IS NOT YOUR FULL PROTOCOL", "Mono-Bold", proto_sz, tw)
    proto_lines = proto_lines[:2]
    for ln in proto_lines:
        _dc(c, left, cy - proto_sz, ln, "Mono-Bold", proto_sz, C["t1"], tw, alpha=1.0)
        cy -= proto_sz * 1.08
    cy -= sgap

    # 3. "SCAN FOR FULL PROTOCOL" + QR
    cta_sz = min(sect_sz + 1, body_sz)
    cta_lines = _w("SCAN FOR FULL PROTOCOL", "Mono-SemiBold", cta_sz, tw if not narrow else cw)

    if has_qr_side:
        qr_x = right_ - qr_sz
        qr_y = cy - qr_sz
        if qr_y < floor + 5:
            qr_y = floor + 5
        c.drawImage(qr_img, qr_x, qr_y, qr_sz, qr_sz)
        for ln in cta_lines[:2]:
            _dc(c, left, cy - cta_sz, ln, "Mono-SemiBold", cta_sz, C["t1"], tw, alpha=1.0)
            cy -= cta_sz * 1.1
        url_sz = min(6, cta_sz - 1)
        _d(c, left, cy - url_sz, "genomax.ai", "Mono", url_sz, C["t2"], alpha=0.72)
        cy -= url_sz + sgap
    else:
        for ln in cta_lines[:2]:
            _dc(c, left, cy - cta_sz, ln, "Mono-SemiBold", cta_sz, C["t1"], cw, alpha=1.0)
            cy -= cta_sz * 1.1
        cy -= 3
        c.drawImage(qr_img, left, cy - qr_sz, qr_sz, qr_sz)
        url_sz = 5.5
        _d(c, left + qr_sz + 6, cy - qr_sz/2 - 2, "genomax.ai", "Mono", url_sz, C["t2"], alpha=0.72)
        cy -= qr_sz + sgap

    # 4. Divider
    c.setStrokeColor(C["div"]); c.setLineWidth(0.35)
    c.line(left, cy, left + tw, cy)
    cy -= sgap

    # ── Remaining content sections ──
    remaining = cy - floor
    ABS_MIN = 6

    # If very tight, shrink body further
    if remaining < 60:
        body_sz = max(ABS_MIN, body_sz - 1)
        body_lh = body_sz * 1.2
        sgap = max(3, sgap - 2)

    # 5. Context paragraph
    ctx = sec.get("context", "")
    if ctx and remaining > 30:
        ctx_lines = _w(ctx, bb["font"], body_sz, tw)
        mx = 2 if (narrow or short or remaining < 80) else 3
        if tall:
            mx = 4
        drawn = 0
        for ln in ctx_lines[:mx]:
            if cy - body_sz < floor:
                break
            _dc(c, left, cy - body_sz, ln, bb["font"], body_sz, C["t1"], tw, alpha=bb["alpha"])
            cy -= body_lh
            drawn += 1
        if drawn > 0:
            cy -= sgap

    # 6. Suggested Use
    sug = sec.get("suggested_use", "")
    if sug and cy - floor > 18:
        _dt(c, left, cy - sect_sz, "SUGGESTED USE", bs["font"], sect_sz,
            C["t1"], bs["track"], mw=tw, alpha=bs["alpha"])
        cy -= sect_sz + 3
        sug_lines = _w(sug, "Mono-Medium", body_sz, tw)
        mx = 2 if (narrow or short) else 3
        for ln in sug_lines[:mx]:
            if cy - body_sz < floor:
                break
            _dc(c, left, cy - body_sz, ln, "Mono-Medium", body_sz, C["t1"], tw, alpha=0.92)
            cy -= body_lh
        cy -= sgap

    # 7. Warnings
    warn_text = ' '.join(sec.get("warnings", []))
    if warn_text and cy - floor > 15:
        _dt(c, left, cy - sect_sz, "WARNINGS", bs["font"], sect_sz,
            C["t1"], bs["track"], mw=tw, alpha=bs["alpha"])
        cy -= sect_sz + 3
        warn_sz = max(ABS_MIN, body_sz - 0.5)
        warn_lh = warn_sz * 1.15
        warn_lines = _w(warn_text, bb["font"], warn_sz, tw)
        mx = 3 if (narrow or short) else 4
        if tall:
            mx = 6
        for ln in warn_lines[:mx]:
            if cy - warn_sz < floor:
                break
            _dc(c, left, cy - warn_sz, ln, bb["font"], warn_sz, C["t2"], tw, alpha=bb["alpha"])
            cy -= warn_lh
        cy -= sgap

    # 8. Ingredients
    ingr = sec.get("ingredients", "")
    if ingr and cy - floor > 10:
        _dt(c, left, cy - sect_sz, "INGREDIENTS", bs["font"], sect_sz,
            C["t1"], bs["track"], mw=tw, alpha=bs["alpha"])
        cy -= sect_sz + 3
        ingr_sz = max(ABS_MIN, body_sz - 0.5)
        ingr_lines = _w(ingr, bb["font"], ingr_sz, tw)
        for ln in ingr_lines[:3]:
            if cy - ingr_sz < floor:
                break
            _dc(c, left, cy - ingr_sz, ln, bb["font"], ingr_sz, C["t1"], tw, alpha=0.92)
            cy -= ingr_sz * 1.15


# ═══════════════════════════════════════════════════════════════════════════
# RENDER PIPELINE
# ═══════════════════════════════════════════════════════════════════════════

def render_sku(sku, system_name, output_base=None):
    meta = sku["_meta"]
    fmt = sku["format"]["label_format"]
    if fmt not in FORMAT_DIMS:
        return None

    dims = FORMAT_DIMS[fmt]
    accent = C["ax_mo"] if "MAXimo" in meta["os"] else C["ax_ma"]

    base = output_base or OUTPUT_BASE
    sys_tag = "MO" if "MAXimo" in meta["os"] else "MA"
    ing = sku["front_panel"]["zone_3"]["ingredient_name"]
    short = ing.replace("/", "-").replace("\\", "-").replace(":", "").replace(" ", "_")[:50].strip("_")
    out_dir = base / fmt / f"{meta['module_code']}_{sys_tag}_{short}"
    out_dir.mkdir(parents=True, exist_ok=True)

    cm = 20
    pw = dims["w"] + 2*BLEED + 2*cm
    ph = dims["h"] + 2*BLEED + 2*cm
    tx, ty_ = cm + BLEED, cm + BLEED

    results = {}
    for side in ["front", "back"]:
        pdf_p = out_dir / f"{side}.pdf"
        cv = canvas.Canvas(str(pdf_p), pagesize=(pw, ph))
        cv.setAuthor("GenoMAX\u00b2 V7 Design System v1.0")
        cv.setTitle(f"{meta['module_code']} {ing} {fmt} {side}")
        cv.setFillColor(C["white"])
        cv.rect(0, 0, pw, ph, fill=1, stroke=0)

        if side == "front":
            render_front(cv, sku, dims, accent, tx, ty_)
        else:
            render_back(cv, sku, dims, accent, tx, ty_)

        crop_marks(cv, tx, ty_, dims["w"], dims["h"])
        info = f"GenoMAX\u00b2 | {meta['module_code']} | {meta['os']} | {fmt} | {side.upper()} | V7-DESIGN-SYSTEM-v1.0"
        _d(cv, tx, ty_ - BLEED - 10, info, "Mono", 3.5, C["t3"])
        cv.save()

        # Generate JPG
        import fitz
        doc = fitz.open(str(pdf_p))
        page = doc[0]
        max_dim = 1600
        pw_pt, ph_pt = page.rect.width, page.rect.height
        scale = min(max_dim / pw_pt, max_dim / ph_pt, 4.0)
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        jpg_p = out_dir / f"{side}.jpg"
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img.save(str(jpg_p), "JPEG", quality=85)
        doc.close()

        results[side] = jpg_p

    return out_dir


def main():
    parser = argparse.ArgumentParser(description="GenoMAX\u00b2 V7 Design System v1.0 Renderer")
    parser.add_argument("--validate", action="store_true", help="Render 7 validation samples only")
    parser.add_argument("--full", action="store_true", help="Full production render (all 168 SKUs)")
    parser.add_argument("--output", type=str, default=None, help="Custom output directory")
    args = parser.parse_args()

    mode = "VALIDATION" if args.validate else "FULL PRODUCTION"
    print("=" * 60)
    print(f"GenoMAX\u00b2 V7 Design System v1.0 -- {mode}")
    print("=" * 60)

    systems = {
        "maximo": DATA_DIR / "production-labels-maximo-v4.json",
        "maxima": DATA_DIR / "production-labels-maxima-v4.json",
    }

    # Validation targets: specific SKUs to render
    VALIDATION_TARGETS = [
        ("maximo", "CV-01", "BOTTLE"),   # 1. standard
        ("maximo", "CV-04", "JAR"),      # 2. short format
        ("maximo", "MT-09", "POUCH"),    # 3. longest name (46 chars)
        ("maximo", "GL-01", "DROPPER"),  # 4. narrowest format
        ("maximo", "GL-04", "STRIPS"),   # 5. tallest format
        ("maximo", "GL-10", "BOTTLE"),   # 6. densest back (872 chars)
        ("maxima", "IN-04", "DROPPER"),  # 7. alt system accent
    ]

    out_base = Path(args.output) if args.output else OUTPUT_BASE
    if args.validate:
        # Use preview directory
        preview_dir = BASE / "design-system" / "v7-preview-01"
        out_base = preview_dir

    total = 0
    for sn, dp in systems.items():
        print(f"\n--- {sn.upper()} ---")
        with open(dp, encoding='utf-8') as f:
            data = json.load(f)

        for i, sku in enumerate(data["skus"]):
            m = sku["_meta"]
            fmt = sku['format']['label_format']
            mc = m['module_code']
            ing = sku["front_panel"]["zone_3"]["ingredient_name"]

            if args.validate:
                # Only render validation targets
                if (sn, mc, fmt) not in VALIDATION_TARGETS:
                    continue
            elif not args.full:
                # Default: render first of each format
                continue

            print(f"  [{total+1:3d}] {mc} | {fmt:7s} | {sn:6s} | {ing[:40]}", end="")
            try:
                render_sku(sku, sn, out_base)
                total += 1
                print(" OK")
            except Exception as e:
                print(f" ERR: {e}")
                import traceback
                traceback.print_exc()

    print(f"\nDONE: {total} SKUs rendered to {out_base}")


if __name__ == "__main__":
    main()
