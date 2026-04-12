#!/usr/bin/env python3
"""
GenoMAX² V7 — Design System v1.0
=================================
Clean implementation. Reuses V6 text primitives, QR, crop marks, parse_back_text.
All typography: IBM Plex Mono only. Spacing scale: 8/12/16/24/32/48/64.
Safe area: 28px all sides. Zero clipping/truncation/ellipsis.
"""

import json, os, sys, re, argparse, io
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

# ─── FONTS (IBM Plex Mono only per spec) ──────────────────────────────────
FONT_MAP = {
    "Mono":       "IBMPlexMono-Regular.ttf",
    "Mono-Med":   "IBMPlexMono-Medium.ttf",
    "Mono-SB":    "IBMPlexMono-SemiBold.ttf",
    "Mono-Bold":  "IBMPlexMono-Bold.ttf",
    "Mono-Light": "IBMPlexMono-Light.ttf",
    "Cond":       "IBMPlexSansCondensed-Regular.ttf",
    "Cond-Med":   "IBMPlexSansCondensed-Medium.ttf",
    "Cond-SB":    "IBMPlexSansCondensed-SemiBold.ttf",
    "Cond-Bold":  "IBMPlexSansCondensed-Bold.ttf",
}
for name, fn in FONT_MAP.items():
    p = FONTS_DIR / fn
    if p.exists():
        pdfmetrics.registerFont(TTFont(name, str(p)))

COND_MAP = {
    "Mono-Bold": "Cond-Bold", "Mono-Med": "Cond-Med",
    "Mono": "Cond", "Mono-SB": "Cond-SB",
}

# ─── COLORS ───────────────────────────────────────────────────────────────
def h2c(h):
    h = h.lstrip('#')
    r, g, b = int(h[0:2],16)/255, int(h[2:4],16)/255, int(h[4:6],16)/255
    k = 1 - max(r, g, b)
    if k == 1: return CMYKColor(0, 0, 0, 1)
    return CMYKColor((1-r-k)/(1-k), (1-g-k)/(1-k), (1-b-k)/(1-k), k)

C = {
    "bg":       h2c("#F4F2EC"),
    "t1":       h2c("#1A1815"),
    "t2":       h2c("#4A4843"),
    "t3":       h2c("#8A8880"),
    "div":      h2c("#C5C2BA"),
    "ax_mo":    h2c("#7A1E2E"),
    "ax_ma":    h2c("#7A304A"),
    "footer_bg": h2c("#6A6A72"),
    "white":    CMYKColor(0, 0, 0, 0),
}

def alpha_color(base_hex, alpha):
    h = base_hex.lstrip('#')
    r, g, b = int(h[0:2],16)/255, int(h[2:4],16)/255, int(h[4:6],16)/255
    bg_r, bg_g, bg_b = 0.957, 0.949, 0.925  # #F4F2EC
    mr = r * alpha + bg_r * (1 - alpha)
    mg = g * alpha + bg_g * (1 - alpha)
    mb = b * alpha + bg_b * (1 - alpha)
    return h2c("#{:02x}{:02x}{:02x}".format(int(mr*255), int(mg*255), int(mb*255)))

def footer_alpha(alpha):
    r, g, b = 1.0, 1.0, 1.0
    bg_r, bg_g, bg_b = 0.416, 0.416, 0.447  # #6A6A72
    mr = r * alpha + bg_r * (1 - alpha)
    mg = g * alpha + bg_g * (1 - alpha)
    mb = b * alpha + bg_b * (1 - alpha)
    return h2c("#{:02x}{:02x}{:02x}".format(int(mr*255), int(mg*255), int(mb*255)))

# ─── DESIGN TOKENS ────────────────────────────────────────────────────────
SAFE = 28  # 28px safe area all sides
BLEED = 3 * mm
SP = {1: 8, 2: 12, 3: 16, 4: 24, 5: 32, 6: 48, 7: 64}  # spacing scale
QR_GAP = 24

FORMAT_DIMS = {
    "BOTTLE":  {"w": 6*inch,   "h": 2.5*inch},
    "JAR":     {"w": 8.5*inch, "h": 2*inch},
    "POUCH":   {"w": 5*inch,   "h": 4*inch},
    "DROPPER": {"w": 2*inch,   "h": 4*inch},
    "STRIPS":  {"w": 4*inch,   "h": 6.5*inch},
}

QR_SIZE = {"BOTTLE": 84, "JAR": 78, "POUCH": 78, "DROPPER": 72, "STRIPS": 72}

PN_RANGE = {
    "BOTTLE": (18, 24), "JAR": (16, 20), "POUCH": (22, 27),
    "DROPPER": (16, 22), "STRIPS": (24, 28),
}

# Footer text color: rgba(255,255,255,0.88) blended on #6A6A72
FOOTER_TX = footer_alpha(0.88)

# ─── TEXT PRIMITIVES (from V6, adapted) ───────────────────────────────────

def _tw(t, f, s):
    return pdfmetrics.stringWidth(t, f, s)

def _d(c, x, y, t, f, s, co):
    o = c.beginText(x, y)
    o.setFont(f, s); o.setFillColor(co); o.setCharSpace(0)
    o.textOut(t); c.drawText(o)

def _dt(c, x, y, t, f, s, co, tr, mw=None):
    """Draw tracked text with cascading fit: tracking->shrink->condense."""
    if mw and t:
        def _trw(txt, sz, trk):
            return _tw(txt, f, sz) + max(0, len(txt)-1) * sz * trk
        orig_s, orig_f = s, f
        if _trw(t, s, tr) > mw:
            for test_tr in [tr*0.6, tr*0.3, 0]:
                if _trw(t, s, test_tr) <= mw: tr = test_tr; break
            else: tr = 0
        while _trw(t, s, tr) > mw and s > orig_s * 0.75: s -= 0.25
        if _trw(t, s, tr) > mw:
            alt = COND_MAP.get(f)
            if alt:
                try:
                    if _tw(t, alt, s) + max(0, len(t)-1)*s*tr <= mw: f = alt
                except: pass
        while _trw(t, s, tr) > mw and s > orig_s * 0.60: s -= 0.25
    o = c.beginText(x, y)
    o.setFont(f, s); o.setFillColor(co); o.setCharSpace(s * tr)
    o.textOut(t); c.drawText(o)

def _dc(c, x, y, t, f, s, co, mw):
    """Draw clamped: shrink->condense->shrink more. Never truncate."""
    orig_s = s
    while _tw(t, f, s) > mw and s > orig_s * 0.80: s -= 0.25
    if _tw(t, f, s) > mw:
        alt = COND_MAP.get(f)
        if alt:
            s_try = orig_s
            while _tw(t, alt, s_try) > mw and s_try > orig_s * 0.80: s_try -= 0.25
            if _tw(t, alt, s_try) <= mw: f = alt; s = s_try
    while _tw(t, f, s) > mw and s > orig_s * 0.60: s -= 0.25
    _d(c, x, y, t, f, s, co)

def _dr(c, xr, y, t, f, s, co):
    _d(c, xr - _tw(t, f, s), y, t, f, s, co)

def _w(t, f, s, mw):
    """Word-wrap with char-break fallback."""
    words, lines, cur = t.split(), [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if _tw(test, f, s) <= mw: cur = test
        else:
            if cur: lines.append(cur)
            if _tw(w, f, s) > mw:
                chunk = ""
                for ch in w:
                    if _tw(chunk + ch, f, s) <= mw: chunk += ch
                    else:
                        if chunk: lines.append(chunk)
                        chunk = ch
                cur = chunk
            else: cur = w
    if cur: lines.append(cur)
    return lines

def make_qr(url):
    qr = qrcode.QRCode(version=2, error_correction=qrcode.constants.ERROR_CORRECT_M,
                        box_size=8, border=1)
    qr.add_data(url); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO(); img.save(buf, format='PNG'); buf.seek(0)
    return ImageReader(buf)

def crop_marks(c, tx, ty, w, h):
    c.setStrokeColor(CMYKColor(0,0,0,1)); c.setLineWidth(0.25)
    L, O = 12, 3
    pts = [
        (tx-O,ty+h,tx-O-L,ty+h), (tx,ty+h+O,tx,ty+h+O+L),
        (tx+w+O,ty+h,tx+w+O+L,ty+h), (tx+w,ty+h+O,tx+w,ty+h+O+L),
        (tx-O,ty,tx-O-L,ty), (tx,ty-O,tx,ty-O-L),
        (tx+w+O,ty,tx+w+O+L,ty), (tx+w,ty-O,tx+w,ty-O-L),
    ]
    for p in pts: c.line(*p)

# ─── PARSE BACK TEXT (from V6) ────────────────────────────────────────────
def parse_back_text(raw):
    sections = {"context": "", "suggested_use": "", "cta_line": "", "warnings": [], "ingredients": ""}
    lines = raw.split('\n')
    current_section = None
    buffer = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_section and buffer:
                text = ' '.join(buffer).strip()
                if current_section == "context": sections["context"] = text
                elif current_section == "suggested_use":
                    sections["suggested_use"] += (" " + text if sections["suggested_use"] else text)
                elif current_section == "warnings":
                    if text: sections["warnings"].append(text)
                elif current_section == "ingredients": sections["ingredients"] = text
                elif current_section == "cta_line": sections["cta_line"] = text
                buffer = []
            continue
        if stripped == "This is not your full protocol.": continue
        if stripped in ("[QR]", "Scan to begin", "genomax.ai"): continue
        if stripped.startswith("Distributed by"): continue
        if stripped == "Suggested Use:":
            if buffer and current_section:
                text = ' '.join(buffer).strip()
                if current_section == "context": sections["context"] = text
                buffer = []
            current_section = "suggested_use"; continue
        elif stripped == "Warnings:":
            if buffer and current_section:
                text = ' '.join(buffer).strip()
                if current_section == "suggested_use":
                    sections["suggested_use"] += (" " + text if sections["suggested_use"] else text)
                elif current_section == "cta_line": sections["cta_line"] = text
                buffer = []
            current_section = "warnings"; continue
        elif stripped.startswith("Ingredients:"):
            if buffer and current_section == "warnings":
                text = ' '.join(buffer).strip()
                if text: sections["warnings"].append(text)
                buffer = []
            current_section = "ingredients"
            rest = stripped[len("Ingredients:"):].strip()
            if rest: buffer.append(rest)
            continue
        elif stripped.startswith("Often used in"):
            if buffer and current_section:
                text = ' '.join(buffer).strip()
                if current_section == "suggested_use":
                    sections["suggested_use"] += (" " + text if sections["suggested_use"] else text)
                buffer = []
            current_section = "cta_line"; buffer.append(stripped); continue
        if current_section is None: current_section = "context"
        buffer.append(stripped)
    if buffer and current_section:
        text = ' '.join(buffer).strip()
        if current_section == "context": sections["context"] = text
        elif current_section == "suggested_use":
            sections["suggested_use"] += (" " + text if sections["suggested_use"] else text)
        elif current_section == "warnings":
            if text: sections["warnings"].append(text)
        elif current_section == "ingredients": sections["ingredients"] = text
        elif current_section == "cta_line": sections["cta_line"] = text
    return sections

# ─── V7 FOOTER (shared between front/back) ───────────────────────────────
def draw_footer(c, tx, ty, w, fmt, left_text, right_text):
    """Draw footer bar. BG #6A6A72, text rgba(255,255,255,0.88). 8px padding top/bottom."""
    narrow = fmt == "DROPPER"
    fsz = 5.5 if not narrow else 4.5  # small footer text to fit
    pad = SP[1]  # 8px top/bottom
    if narrow:
        fh = pad + fsz + 2 + fsz + pad  # two-line footer for narrow
    else:
        fh = pad + fsz + pad  # single-line footer
    c.setFillColor(C["footer_bg"])
    c.rect(tx - BLEED, ty - BLEED, w + 2*BLEED, fh + BLEED, fill=1, stroke=0)
    fl = tx + SAFE
    fr = tx + w - SAFE
    fw = fr - fl
    if narrow:
        cy1 = ty + fh - pad - fsz
        _dc(c, fl, cy1, left_text, "Mono", fsz, FOOTER_TX, fw)
        cy2 = cy1 - fsz - 2
        _dc(c, fl, cy2, right_text, "Mono", fsz, FOOTER_TX, fw)
    else:
        cy = ty + (fh - fsz) / 2
        hw = fw * 0.48
        _dc(c, fl, cy, left_text, "Mono", fsz, FOOTER_TX, hw)
        _dr(c, fr, cy, right_text, "Mono", fsz, FOOTER_TX)
    return fh

# ═══════════════════════════════════════════════════════════════════════════
# FRONT LABEL — V7 Design System v1.0
# ═══════════════════════════════════════════════════════════════════════════
def render_front(c, sku, dims, accent, tx, ty):
    w, h = dims["w"], dims["h"]
    fmt = sku["format"]["label_format"]
    narrow = fmt == "DROPPER"
    short = fmt == "JAR"

    left = tx + SAFE
    right_ = tx + w - SAFE
    cw = right_ - left

    # Background + accent ceiling
    c.setFillColor(C["bg"])
    c.rect(tx - BLEED, ty - BLEED, w + 2*BLEED, h + 2*BLEED, fill=1, stroke=0)
    c.setFillColor(accent)
    c.rect(tx - BLEED, ty + h - 2, w + 2*BLEED, 2, fill=1, stroke=0)

    # Footer
    ver = sku["front_panel"]["zone_7"]["version_info"]
    qty = sku["front_panel"]["zone_7"]["net_quantity"]
    fh = draw_footer(c, tx, ty, w, fmt, ver, qty)
    floor = ty + fh + SAFE  # content must stay above this

    # ── VERTICAL RHYTHM (spec tokens) ──
    # Top → SP4(24) → Brand → SP2(12) → System → SP4(24) → Product name →
    # SP2(12) → Subtitle → SP3(16) → Descriptor → SP5(32) → Meta →
    # SP5(32) → Variant → auto → Footer

    top = ty + h - SAFE - 2  # top of content area

    # Extract data
    pn = sku["front_panel"]["zone_3"]["ingredient_name"]
    desc = sku["front_panel"]["zone_4"].get("descriptor", "")
    bio = sku["front_panel"]["zone_4"].get("biological_system", "")
    variant = sku["front_panel"]["zone_5"]["variant_name"]
    z6 = sku["front_panel"]["zone_6"]
    meta_items = [
        ("TYPE", z6["type"]["value"]),
        ("SYSTEM", (bio or "").split("\u00b7")[0].strip() or z6.get("status",{}).get("value","") or "\u2014"),
        ("FUNCTION", z6["function"]["value"]),
    ]

    # Typography sizes from spec
    brand_sz = 13
    sys_sz = 9
    pn_max = PN_RANGE[fmt][1]
    pn_min = PN_RANGE[fmt][0]
    sub_sz = 14
    meta_lbl_sz = 10
    meta_val_sz = 10.5
    var_sz = 10.5  # reuse meta value size for variant line

    # Adaptive: scale down for narrow/short
    if narrow:
        brand_sz = 9; sys_sz = 7; sub_sz = 10; meta_lbl_sz = 7.5
        meta_val_sz = 8; var_sz = 8
    elif short:
        brand_sz = 11; sys_sz = 8; sub_sz = 11; meta_lbl_sz = 8.5
        meta_val_sz = 9; var_sz = 9

    # ── PASS 1: Measure and fit ──
    ps = pn_max
    pf = "Mono-Bold"
    title_lines = _w(pn, pf, ps, cw)
    while len(title_lines) > 3 and ps > pn_min:
        ps -= 0.5
        title_lines = _w(pn, pf, ps, cw)
    title_lines = title_lines[:3]
    title_h = len(title_lines) * ps * 1.02

    sub_lines = []
    if desc:
        sub_lines = _w(desc, "Mono-Med", sub_sz, cw)
        _ss = sub_sz
        while len(sub_lines) > 2 and _ss > 9:
            _ss -= 0.5
            sub_lines = _w(desc, "Mono-Med", _ss, cw)
        sub_sz = _ss
        sub_lines = sub_lines[:2]
    sub_h = len(sub_lines) * sub_sz * 1.15

    bio_sz = sys_sz
    bio_h = bio_sz * 1.1 if bio else 0

    meta_lh = meta_val_sz * 1.25
    meta_h = 3 * meta_lh
    var_h = var_sz + 4

    # Gaps from spec tokens (initial ideal values)
    g_brand_sys = SP[2]   # 12
    g_sys_pn = SP[4]      # 24
    g_pn_sub = SP[2]      # 12
    g_sub_desc = SP[3]    # 16
    g_desc_meta = SP[5]   # 32
    g_meta_var = SP[5]    # 32

    top_pad = SP[4]  # initial 24px from top
    available = top - floor - top_pad

    def calc_total():
        return (brand_sz + g_brand_sys + sys_sz + g_sys_pn +
                title_h + g_pn_sub + sub_h +
                (g_sub_desc + bio_h if bio else 0) +
                g_desc_meta + meta_h + g_meta_var + var_h)

    # Iterative fit: shrink gaps, then sizes, until everything fits
    for _ in range(120):
        if calc_total() <= available:
            break
        # Phase 1: compress large gaps aggressively
        if g_desc_meta > 4: g_desc_meta -= 2; continue
        if g_meta_var > 4: g_meta_var -= 2; continue
        if g_sys_pn > 4: g_sys_pn -= 2; continue
        if g_sub_desc > 2: g_sub_desc -= 2; continue
        if g_pn_sub > 2: g_pn_sub -= 1; continue
        if g_brand_sys > 2: g_brand_sys -= 1; continue
        # Phase 2: shrink product name
        if ps > max(pn_min, 12):
            ps -= 0.5
            title_lines = _w(pn, pf, ps, cw)[:3]
            title_h = len(title_lines) * ps * 1.02
            continue
        # Phase 3: shrink subtitle
        if sub_sz > 7 and sub_lines:
            sub_sz -= 0.5
            sub_lines = _w(desc, "Mono-Med", sub_sz, cw)[:2]
            sub_h = len(sub_lines) * sub_sz * 1.15
            continue
        # Phase 4: shrink meta
        if meta_val_sz > 6:
            meta_val_sz -= 0.5; meta_lbl_sz = max(6, meta_lbl_sz - 0.5)
            meta_lh = meta_val_sz * 1.25; meta_h = 3 * meta_lh
            continue
        # Phase 5: shrink variant
        if var_sz > 6: var_sz -= 0.5; var_h = var_sz + 2; continue
        # Phase 6: shrink brand/sys
        if brand_sz > 8: brand_sz -= 0.5; continue
        if sys_sz > 6: sys_sz -= 0.5; continue
        # Phase 7: further shrink product name
        if ps > 10:
            ps -= 0.5
            title_lines = _w(pn, pf, ps, cw)[:3]
            title_h = len(title_lines) * ps * 1.02
            continue
        break

    # ── PASS 2: Draw ──
    if short:
        # JAR: 2-column layout (title+sub left, meta+variant right)
        col_split = left + cw * 0.55
        lcw = col_split - left - SP[2]
        rcw = right_ - col_split

        # Re-wrap title for JAR left column width
        jar_ps = min(ps, 20)  # cap product name for JAR height
        jar_lines = _w(pn, pf, jar_ps, lcw)
        while len(jar_lines) > 2 and jar_ps > 14:
            jar_ps -= 0.5
            jar_lines = _w(pn, pf, jar_ps, lcw)
        jar_lines = jar_lines[:2]

        jar_sub_sz = min(sub_sz, 9)
        jar_sub_lines = _w(desc, "Mono-Med", jar_sub_sz, lcw)[:2] if desc else []

        cy = top - SP[2]  # tighter top margin for short format
        # Brand
        _dt(c, left, cy - brand_sz, "GenoMAX\u00b2", "Mono-Bold", brand_sz, C["t1"], 0.08, mw=cw*0.65)
        _dr(c, right_, cy - (brand_sz * 0.5), sku["front_panel"]["zone_1"]["module_code"],
            "Mono-Med", 6, C["t3"])
        cy -= brand_sz + 4

        # Divider
        c.saveState(); c.setStrokeColor(C["t1"]); c.setLineWidth(0.5); c.setStrokeAlpha(0.25)
        c.line(left, cy, right_, cy); c.restoreState()
        cy -= 3

        # System line
        _dt(c, left, cy - sys_sz, sku["front_panel"]["zone_2"]["text"],
            "Mono", sys_sz, alpha_color("#4A4843", 0.72), 0.14, mw=cw)
        cy -= sys_sz + SP[2]

        content_top = cy
        # Left: title + subtitle
        lcy = content_top
        for ln in jar_lines:
            _dc(c, left, lcy - jar_ps, ln, pf, jar_ps, C["t1"], lcw)
            lcy -= jar_ps * 1.02
        lcy -= 4
        for sl in jar_sub_lines:
            _dc(c, left, lcy - jar_sub_sz, sl, "Mono-Med", jar_sub_sz,
                alpha_color("#1A1815", 0.88), lcw)
            lcy -= jar_sub_sz * 1.15
        if bio and lcy - bio_sz > floor:
            lcy -= 3
            _dc(c, left, lcy - bio_sz, bio, "Mono", bio_sz, C["t3"], lcw)

        # Right: meta + variant
        rcy = content_top
        jar_meta_lbl = min(meta_lbl_sz, 7.5)
        jar_meta_val = min(meta_val_sz, 8)
        jar_meta_lh = jar_meta_val * 1.25
        lbl_w = _tw("FUNCTION", "Mono", jar_meta_lbl) + jar_meta_lbl
        for label, val in meta_items:
            _d(c, col_split, rcy - jar_meta_lbl, label, "Mono",
               jar_meta_lbl, alpha_color("#1A1815", 0.58))
            _dc(c, col_split + lbl_w, rcy - jar_meta_val, val, "Mono-SB",
                jar_meta_val, alpha_color("#1A1815", 0.92), rcw - lbl_w)
            rcy -= jar_meta_lh
        rcy -= 6
        if rcy - var_sz > floor:
            _dc(c, col_split, rcy - var_sz, variant, "Mono-SB", var_sz, C["t1"], rcw)
            rcy -= var_sz + 2
            c.setFillColor(accent)
            c.rect(col_split, rcy - 2, 50, 2, fill=1, stroke=0)
    else:
        # BOTTLE/POUCH/DROPPER/STRIPS: single-column vertical
        cy = top - SP[4]

        # Brand (13px, weight 500=Medium, tracking 0.08em)
        _dt(c, left, cy - brand_sz, "GenoMAX\u00b2", "Mono-Med", brand_sz,
            C["t1"], 0.08, mw=cw*0.65)
        _dr(c, right_, cy - (brand_sz * 0.5),
            sku["front_panel"]["zone_1"]["module_code"], "Mono-Med",
            6 if not narrow else 5, C["t3"])
        cy -= brand_sz + g_brand_sys

        # System line (9px, weight 400, tracking 0.14em, opacity 0.72)
        _dt(c, left, cy - sys_sz, sku["front_panel"]["zone_2"]["text"],
            "Mono", sys_sz, alpha_color("#4A4843", 0.72), 0.14, mw=cw)
        cy -= sys_sz + g_sys_pn

        # Product name (27px range, weight 700=Bold, line-height 1.02)
        for ln in title_lines:
            if cy - ps < floor: break
            _dc(c, left, cy - ps, ln, pf, ps, C["t1"], cw)
            cy -= ps * 1.02
        cy -= g_pn_sub

        # Subtitle (14px, weight 500, opacity 0.88, line-height 1.15)
        for sl in sub_lines:
            if cy - sub_sz < floor: break
            _dc(c, left, cy - sub_sz, sl, "Mono-Med", sub_sz,
                alpha_color("#1A1815", 0.88), cw)
            cy -= sub_sz * 1.15
        cy -= g_sub_desc

        # Descriptor / biological system line
        if bio and cy - bio_sz > floor:
            _dc(c, left, cy - bio_sz, bio, "Mono", bio_sz, C["t3"], cw)
            cy -= bio_h
        cy -= g_desc_meta

        # Meta block — stacked (TYPE / SYSTEM / FUNCTION)
        lbl_w = _tw("FUNCTION", "Mono", meta_lbl_sz * 0.85) + meta_lbl_sz
        for label, val in meta_items:
            if cy - meta_lbl_sz < floor: break
            _d(c, left, cy - meta_lbl_sz, label, "Mono", meta_lbl_sz,
               alpha_color("#1A1815", 0.58))
            _dc(c, left + lbl_w, cy - meta_val_sz, val, "Mono-SB",
                meta_val_sz, alpha_color("#1A1815", 0.92), cw - lbl_w)
            cy -= meta_lh
        cy -= g_meta_var

        # Variant + accent bar
        if cy - var_sz > floor:
            _dc(c, left, cy - var_sz, variant, "Mono-SB", var_sz, C["t1"], cw)
            cy -= var_sz + 2
            bar_w = 70 if not narrow else 40
            c.setFillColor(accent)
            c.rect(left, cy - 2, bar_w, 2, fill=1, stroke=0)

# ═══════════════════════════════════════════════════════════════════════════
# BACK LABEL — V7 Design System v1.0
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
    top = ty + h - SAFE

    raw = sku.get("back_panel", {}).get("back_label_text", "")
    sec = parse_back_text(raw)

    # Background + accent ceiling
    c.setFillColor(C["bg"])
    c.rect(tx - BLEED, ty - BLEED, w + 2*BLEED, h + 2*BLEED, fill=1, stroke=0)
    c.setFillColor(accent)
    c.rect(tx - BLEED, ty + h - 2, w + 2*BLEED, 2, fill=1, stroke=0)

    # Footer
    fh = draw_footer(c, tx, ty, w, fmt,
                     "genomax.ai \u00b7 support@genomax.ai",
                     "Distributed by Genomax LLC")
    floor = ty + fh + SAFE

    # QR setup
    qr_sz = QR_SIZE[fmt]
    mc = sku["_meta"]["module_code"]
    osn = sku["_meta"]["os"].replace("\u00b2","2").replace("\u00b2","2").lower()
    qr_img = make_qr(f"https://genomax.ai/module/{osn}/{mc.lower()}")

    # Text sizes from spec
    BACK_TITLE = 18    # back title: 18px, 700, tracking 0.04em
    SECT_LBL = 9       # section label: 9px, 500, tracking 0.14em
    BODY_SZ = 10.5     # body: 10.5px, 400, line-height 1.32
    BODY_LH = 1.32
    SGAP = SP[2]       # 12px section gap (was 16; tightened for density)
    PROTO_SZ = 11      # protocol header

    # Scale for narrow/short
    if narrow:
        BACK_TITLE = 12; PROTO_SZ = 8; BODY_SZ = 7.5; SECT_LBL = 6.5
        SGAP = SP[1]  # 8
    elif short:
        BACK_TITLE = 14; PROTO_SZ = 9; BODY_SZ = 8; SECT_LBL = 7
        SGAP = SP[1]  # 8
    # BOTTLE is standard height (2.5") — tighten for density
    if fmt == "BOTTLE":
        BODY_SZ = 7.5; SECT_LBL = 7; SGAP = 6; BODY_LH = 1.2

    # Scale QR for back: use slightly smaller to save space
    back_qr_sz = int(qr_sz * 0.75)
    has_qr_side = not narrow and not tall
    qr_reserve = (back_qr_sz + QR_GAP) if has_qr_side else 0
    tw_ = cw - qr_reserve

    # ── Brand header ──
    cy = top - 2
    bbsz = 8 if not narrow else 6
    _dt(c, left, cy - bbsz, "GenoMAX\u00b2", "Mono-Bold", bbsz, C["t1"], 0.08, mw=cw*0.6)
    cy -= bbsz + 2

    c.saveState()
    c.setStrokeColor(C["t1"]); c.setLineWidth(0.5); c.setStrokeAlpha(0.25)
    c.line(left, cy, right_, cy)
    c.restoreState()
    cy -= SP[1]

    # ── Protocol header (18px back title spec) ──
    proto = "THIS IS NOT YOUR FULL PROTOCOL"
    proto_lines = _w(proto, "Mono-Bold", PROTO_SZ, tw_)
    for ln in proto_lines[:2]:
        _dc(c, left, cy - PROTO_SZ, ln, "Mono-Bold", PROTO_SZ,
            C["t1"], tw_)
        cy -= PROTO_SZ * 1.08
    cy -= SGAP

    # ── CTA + QR ──
    cta_sz = 10 if not narrow else 8
    cta_lines = _w("SCAN FOR FULL PROTOCOL", "Mono-SB", cta_sz,
                    tw_ if not narrow else cw)
    if has_qr_side:
        qr_x = right_ - back_qr_sz
        qr_y = cy - back_qr_sz
        if qr_y < floor + 10: qr_y = floor + 10
        c.drawImage(qr_img, qr_x, qr_y, back_qr_sz, back_qr_sz)
        for ln in cta_lines[:2]:
            _dc(c, left, cy - cta_sz, ln, "Mono-SB", cta_sz, C["t1"], tw_)
            cy -= cta_sz + 1
        _dc(c, left, cy - 6, "genomax.ai", "Mono", 6, C["t2"], tw_)
        cy -= 6 + SGAP
    else:
        for ln in cta_lines[:2]:
            _dc(c, left, cy - cta_sz, ln, "Mono-SB", cta_sz, C["t1"], cw)
            cy -= cta_sz + 1
        cy -= 3
        c.drawImage(qr_img, left, cy - back_qr_sz, back_qr_sz, back_qr_sz)
        _d(c, left + back_qr_sz + 4, cy - back_qr_sz/2 - 2, "genomax.ai", "Mono", 5.5, C["t2"])
        cy -= back_qr_sz + SGAP

    # Divider
    c.setStrokeColor(C["div"]); c.setLineWidth(0.35)
    c.line(left, cy, left + tw_, cy)
    cy -= SGAP

    # ── Context paragraph ──
    ctx = sec.get("context", "")
    if ctx and not short and cy > floor + 12:
        ctx_lines = _w(ctx, "Mono", BODY_SZ, tw_)
        mx = 2 if narrow else 3
        for ln in ctx_lines[:mx]:
            if cy < floor + BODY_SZ: break
            _dc(c, left, cy - BODY_SZ, ln, "Mono", BODY_SZ,
                alpha_color("#1A1815", 0.88), tw_)
            cy -= BODY_SZ * BODY_LH
        cy -= SGAP

    # ── Suggested use ──
    sug = sec.get("suggested_use", "")
    if sug and cy > floor + 10:
        _dt(c, left, cy - SECT_LBL, "SUGGESTED USE", "Mono-Med",
            SECT_LBL, alpha_color("#1A1815", 0.58), 0.14, mw=tw_)
        cy -= SECT_LBL + 2
        sug_lines = _w(sug, "Mono", BODY_SZ, tw_)
        mx = 2 if narrow else 3
        for ln in sug_lines[:mx]:
            if cy < floor + BODY_SZ: break
            _dc(c, left, cy - BODY_SZ, ln, "Mono", BODY_SZ,
                alpha_color("#1A1815", 0.88), tw_)
            cy -= BODY_SZ * BODY_LH
        cy -= SGAP

    # ── Warnings ──
    warn_text = ' '.join(sec.get("warnings", []))
    if warn_text and cy > floor + 12:
        _dt(c, left, cy - SECT_LBL, "WARNINGS", "Mono-Med",
            SECT_LBL, alpha_color("#1A1815", 0.58), 0.14, mw=tw_)
        cy -= SECT_LBL + 2
        wl = _w(warn_text, "Mono", BODY_SZ, tw_)
        mx = 3 if narrow else (5 if tall else 4)
        for ln in wl[:mx]:
            if cy < floor + BODY_SZ: break
            _dc(c, left, cy - BODY_SZ, ln, "Mono", BODY_SZ,
                alpha_color("#1A1815", 0.88), tw_)
            cy -= BODY_SZ * BODY_LH
        cy -= SGAP

    # ── Ingredients ──
    ingr = sec.get("ingredients", "")
    if ingr and cy > floor + 10:
        _dt(c, left, cy - SECT_LBL, "INGREDIENTS", "Mono-Med",
            SECT_LBL, alpha_color("#1A1815", 0.58), 0.14, mw=tw_)
        cy -= SECT_LBL + 2
        ingr_lines = _w(ingr, "Mono", BODY_SZ, tw_)
        for ln in ingr_lines[:3]:
            if cy < floor + BODY_SZ: break
            _dc(c, left, cy - BODY_SZ, ln, "Mono", BODY_SZ, C["t1"], tw_)
            cy -= BODY_SZ * BODY_LH

# ═══════════════════════════════════════════════════════════════════════════
# RENDER + EXPORT PIPELINE
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
    short_name = ing.replace("/","-").replace("\\","-").replace(":","").replace(" ","_")[:50].strip("_")
    out_dir = base / fmt / f"{meta['module_code']}_{sys_tag}_{short_name}"
    out_dir.mkdir(parents=True, exist_ok=True)

    cm = 20
    pw = dims["w"] + 2*BLEED + 2*cm
    ph = dims["h"] + 2*BLEED + 2*cm
    tx_ = cm + BLEED
    ty_ = cm + BLEED

    results = {}
    for side in ["front", "back"]:
        pdf_p = out_dir / f"{side}.pdf"
        cv = canvas.Canvas(str(pdf_p), pagesize=(pw, ph))
        cv.setAuthor("GenoMAX\u00b2 V7 Design System v1.0")
        cv.setTitle(f"{meta['module_code']} {ing} {fmt} {side}")
        cv.setFillColor(C["white"])
        cv.rect(0, 0, pw, ph, fill=1, stroke=0)

        if side == "front":
            render_front(cv, sku, dims, accent, tx_, ty_)
        else:
            render_back(cv, sku, dims, accent, tx_, ty_)

        crop_marks(cv, tx_, ty_, dims["w"], dims["h"])
        info = f"GenoMAX\u00b2 | {meta['module_code']} | {meta['os']} | {fmt} | {side.upper()} | V7-DESIGN-SYSTEM-v1.0"
        _d(cv, tx_, ty_ - BLEED - 10, info, "Mono", 3.5, C["t3"])
        cv.save()

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


# ═══════════════════════════════════════════════════════════════════════════
# VALIDATION SAMPLES — 7 specific SKUs per spec
# ═══════════════════════════════════════════════════════════════════════════
VALIDATION_TARGETS = [
    ("maximo", "CV-01"),   # BOTTLE standard
    ("maximo", "CV-04"),   # JAR short format
    ("maximo", "MT-09"),   # POUCH longest name
    ("maximo", "GL-01"),   # DROPPER narrowest
    ("maximo", "GL-04"),   # STRIPS tallest
    ("maximo", "GL-10"),   # BOTTLE densest back
    ("maxima", "IN-04"),   # DROPPER alt accent
]


def main():
    parser = argparse.ArgumentParser(description="GenoMAX\u00b2 V7 Design System v1.0 Renderer")
    parser.add_argument("--validate", action="store_true",
                        help="Render 7 validation samples to v7-preview-01/")
    parser.add_argument("--full", action="store_true",
                        help="Full production render of all 168 SKUs")
    parser.add_argument("--preview-dir", type=str, default=None,
                        help="Override preview directory name (e.g. v7-preview-02)")
    args = parser.parse_args()

    mode = "VALIDATION (7 samples)" if args.validate else "FULL PRODUCTION"
    print("=" * 60)
    print(f"GenoMAX\u00b2 V7 Design System v1.0 \u2014 {mode}")
    print("=" * 60)

    systems = {
        "maximo": DATA_DIR / "production-labels-maximo-v4.json",
        "maxima": DATA_DIR / "production-labels-maxima-v4.json",
    }

    # Load all data
    all_skus = {}
    for sn, dp in systems.items():
        with open(dp, encoding='utf-8') as f:
            data = json.load(f)
        all_skus[sn] = data["skus"]

    if args.validate:
        preview_name = args.preview_dir or "v7-preview-01"
        out_base = BASE / "design-system" / preview_name
        print(f"Output: {out_base}")
        total = 0
        for sys_name, mc in VALIDATION_TARGETS:
            skus = all_skus[sys_name]
            found = None
            for sku in skus:
                if sku["_meta"]["module_code"] == mc:
                    found = sku; break
            if not found:
                print(f"  SKIP {mc} ({sys_name}) \u2014 not found")
                continue
            fmt = found["format"]["label_format"]
            ing = found["front_panel"]["zone_3"]["ingredient_name"]
            print(f"  [{total+1}/7] {mc} | {fmt:7s} | {sys_name:6s} | {ing[:40]}", end="")
            try:
                render_sku(found, sys_name, output_base=out_base)
                total += 1
                print(" OK")
            except Exception as e:
                print(f" ERR: {e}")
                import traceback; traceback.print_exc()

        print(f"\nDONE: {total}/7 validation samples \u2192 {out_base}")

    elif args.full:
        total = 0
        for sn, skus in all_skus.items():
            print(f"\n--- {sn.upper()} ---")
            for i, sku in enumerate(skus):
                m = sku["_meta"]
                fmt = sku["format"]["label_format"]
                ing = sku["front_panel"]["zone_3"]["ingredient_name"]
                print(f"  [{i+1:3d}/{len(skus)}] {m['module_code']} | {fmt:7s} | {ing[:35]}", end="")
                try:
                    render_sku(sku, sn)
                    total += 1
                    print(" OK")
                except Exception as e:
                    print(f" ERR: {e}")
        print(f"\nDONE: {total} SKUs \u2192 {OUTPUT_BASE}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
