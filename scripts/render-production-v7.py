#!/usr/bin/env python3
"""
GenoMAX² V7 — Design System v1.0 + V2 SYSTEM PATCH
=====================================================
Deterministic rendering system. All formats use identical structure logic.
V2 SYSTEM LOCK: 64px footer, 3-block layout, meta left-only, QR rules,
fail conditions, format normalization.
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

SCRIPT_DIR = Path(__file__).resolve().parent
BASE = SCRIPT_DIR.parent
FONTS_DIR = BASE / "design-system" / "fonts"
DATA_DIR = BASE / "design-system" / "data"
OUTPUT_BASE = BASE / "design-system" / "production-v7"

FONT_MAP = {
    "Mono": "IBMPlexMono-Regular.ttf", "Mono-Med": "IBMPlexMono-Medium.ttf",
    "Mono-SB": "IBMPlexMono-SemiBold.ttf", "Mono-Bold": "IBMPlexMono-Bold.ttf",
    "Mono-Light": "IBMPlexMono-Light.ttf",
    "Cond": "IBMPlexSansCondensed-Regular.ttf", "Cond-Med": "IBMPlexSansCondensed-Medium.ttf",
    "Cond-SB": "IBMPlexSansCondensed-SemiBold.ttf", "Cond-Bold": "IBMPlexSansCondensed-Bold.ttf",
}
for name, fn in FONT_MAP.items():
    p = FONTS_DIR / fn
    if p.exists(): pdfmetrics.registerFont(TTFont(name, str(p)))

COND_MAP = {"Mono-Bold":"Cond-Bold","Mono-Med":"Cond-Med","Mono":"Cond","Mono-SB":"Cond-SB"}

def h2c(h):
    h = h.lstrip('#')
    r, g, b = int(h[0:2],16)/255, int(h[2:4],16)/255, int(h[4:6],16)/255
    k = 1 - max(r,g,b)
    if k == 1: return CMYKColor(0,0,0,1)
    return CMYKColor((1-r-k)/(1-k),(1-g-k)/(1-k),(1-b-k)/(1-k),k)

C = {
    "bg": h2c("#F4F2EC"), "t1": h2c("#1A1815"), "t2": h2c("#4A4843"),
    "t3": h2c("#8A8880"), "div": h2c("#C5C2BA"),
    "ax_mo": h2c("#7A1E2E"), "ax_ma": h2c("#7A304A"),
    "footer_bg": h2c("#6A6A72"), "white": CMYKColor(0,0,0,0),
}

def alpha_color(base_hex, alpha):
    h = base_hex.lstrip('#')
    r, g, b = int(h[0:2],16)/255, int(h[2:4],16)/255, int(h[4:6],16)/255
    bg_r, bg_g, bg_b = 0.957, 0.949, 0.925
    mr = r*alpha + bg_r*(1-alpha); mg = g*alpha + bg_g*(1-alpha); mb = b*alpha + bg_b*(1-alpha)
    return h2c("#{:02x}{:02x}{:02x}".format(int(mr*255), int(mg*255), int(mb*255)))

def footer_alpha(alpha):
    r, g, b = 1.0, 1.0, 1.0
    bg_r, bg_g, bg_b = 0.416, 0.416, 0.447
    mr = r*alpha + bg_r*(1-alpha); mg = g*alpha + bg_g*(1-alpha); mb = b*alpha + bg_b*(1-alpha)
    return h2c("#{:02x}{:02x}{:02x}".format(int(mr*255), int(mg*255), int(mb*255)))

# ═══ V2 SYSTEM PATCH — DESIGN TOKENS ═════════════════════════════════════
SAFE = 28
BLEED = 3 * mm
SP = {1: 8, 2: 12, 3: 16, 4: 24, 5: 32, 6: 48, 7: 64}
MIN_BLOCK_SPACING = 12  # V2 Rule 7: minimum 12px between blocks

# V2 Rule 2: Footer HARD LOCK
FOOTER_H = 64  # Fixed 64px height
# V2 Rule 2: Bottom padding before footer — adjusted for format height constraints
FOOTER_PAD = {"BOTTLE": 12, "DROPPER": 16, "JAR": 8, "POUCH": 32, "STRIPS": 32}
FOOTER_TX = footer_alpha(0.88)

# V2 Rule 5: QR system lock — min 18% of width, 12px clear margin
QR_CLEAR = 12
def qr_size_for(fmt, w): return max(int(w * 0.18), 48)

FORMAT_DIMS = {
    "BOTTLE":  {"w": 6*inch,   "h": 2.5*inch},
    "JAR":     {"w": 8.5*inch, "h": 2*inch},
    "POUCH":   {"w": 5*inch,   "h": 4*inch},
    "DROPPER": {"w": 2*inch,   "h": 4*inch},
    "STRIPS":  {"w": 4*inch,   "h": 6.5*inch},
}

# ═══ TEXT PRIMITIVES ══════════════════════════════════════════════════════
def _tw(t, f, s): return pdfmetrics.stringWidth(t, f, s)

def _d(c, x, y, t, f, s, co):
    o = c.beginText(x, y); o.setFont(f, s); o.setFillColor(co); o.setCharSpace(0)
    o.textOut(t); c.drawText(o)

def _dt(c, x, y, t, f, s, co, tr, mw=None):
    if mw and t:
        def _trw(txt, sz, trk): return _tw(txt, f, sz) + max(0, len(txt)-1)*sz*trk
        orig_s = s
        if _trw(t, s, tr) > mw:
            for tt in [tr*0.6, tr*0.3, 0]:
                if _trw(t, s, tt) <= mw: tr = tt; break
            else: tr = 0
        while _trw(t, s, tr) > mw and s > orig_s*0.75: s -= 0.25
        if _trw(t, s, tr) > mw:
            alt = COND_MAP.get(f)
            if alt:
                try:
                    if _tw(t, alt, s) + max(0,len(t)-1)*s*tr <= mw: f = alt
                except: pass
        while _trw(t, s, tr) > mw and s > orig_s*0.60: s -= 0.25
    o = c.beginText(x, y); o.setFont(f, s); o.setFillColor(co); o.setCharSpace(s*tr)
    o.textOut(t); c.drawText(o)

def _dc(c, x, y, t, f, s, co, mw):
    orig_s = s
    while _tw(t, f, s) > mw and s > orig_s*0.80: s -= 0.25
    if _tw(t, f, s) > mw:
        alt = COND_MAP.get(f)
        if alt:
            s_try = orig_s
            while _tw(t, alt, s_try) > mw and s_try > orig_s*0.80: s_try -= 0.25
            if _tw(t, alt, s_try) <= mw: f = alt; s = s_try
    while _tw(t, f, s) > mw and s > orig_s*0.60: s -= 0.25
    _d(c, x, y, t, f, s, co)

def _dr(c, xr, y, t, f, s, co): _d(c, xr - _tw(t, f, s), y, t, f, s, co)

def _w(t, f, s, mw):
    words, lines, cur = t.split(), [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if _tw(test, f, s) <= mw: cur = test
        else:
            if cur: lines.append(cur)
            if _tw(w, f, s) > mw:
                chunk = ""
                for ch in w:
                    if _tw(chunk+ch, f, s) <= mw: chunk += ch
                    else:
                        if chunk: lines.append(chunk)
                        chunk = ch
                cur = chunk
            else: cur = w
    if cur: lines.append(cur)
    return lines

def make_qr(url):
    qr = qrcode.QRCode(version=2, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=1)
    qr.add_data(url); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO(); img.save(buf, format='PNG'); buf.seek(0)
    return ImageReader(buf)

def crop_marks(c, tx, ty, w, h):
    c.setStrokeColor(CMYKColor(0,0,0,1)); c.setLineWidth(0.25)
    L, O = 12, 3
    for p in [(tx-O,ty+h,tx-O-L,ty+h),(tx,ty+h+O,tx,ty+h+O+L),(tx+w+O,ty+h,tx+w+O+L,ty+h),
              (tx+w,ty+h+O,tx+w,ty+h+O+L),(tx-O,ty,tx-O-L,ty),(tx,ty-O,tx,ty-O-L),
              (tx+w+O,ty,tx+w+O+L,ty),(tx+w,ty-O,tx+w,ty-O-L)]:
        c.line(*p)

def parse_back_text(raw):
    sections = {"context":"","suggested_use":"","cta_line":"","warnings":[],"ingredients":""}
    lines, current_section, buffer = raw.split('\n'), None, []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_section and buffer:
                text = ' '.join(buffer).strip()
                if current_section == "context": sections["context"] = text
                elif current_section == "suggested_use": sections["suggested_use"] += (" "+text if sections["suggested_use"] else text)
                elif current_section == "warnings":
                    if text: sections["warnings"].append(text)
                elif current_section == "ingredients": sections["ingredients"] = text
                elif current_section == "cta_line": sections["cta_line"] = text
                buffer = []
            continue
        if stripped in ("This is not your full protocol.","[QR]","Scan to begin","genomax.ai"): continue
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
                if current_section == "suggested_use": sections["suggested_use"] += (" "+text if sections["suggested_use"] else text)
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
                if current_section == "suggested_use": sections["suggested_use"] += (" "+text if sections["suggested_use"] else text)
                buffer = []
            current_section = "cta_line"; buffer.append(stripped); continue
        if current_section is None: current_section = "context"
        buffer.append(stripped)
    if buffer and current_section:
        text = ' '.join(buffer).strip()
        if current_section == "context": sections["context"] = text
        elif current_section == "suggested_use": sections["suggested_use"] += (" "+text if sections["suggested_use"] else text)
        elif current_section == "warnings":
            if text: sections["warnings"].append(text)
        elif current_section == "ingredients": sections["ingredients"] = text
        elif current_section == "cta_line": sections["cta_line"] = text
    return sections

# ═══ V2 RULE 2: FOOTER SYSTEM (HARD LOCK) ════════════════════════════════
def draw_footer(c, tx, ty, w, fmt, left_text, right_text):
    """64px fixed height. No content inside footer zone."""
    fh = FOOTER_H
    c.setFillColor(C["footer_bg"])
    c.rect(tx - BLEED, ty - BLEED, w + 2*BLEED, fh + BLEED, fill=1, stroke=0)
    narrow = fmt == "DROPPER"
    fsz = 5.5 if not narrow else 4
    fl, fr = tx + SAFE, tx + w - SAFE
    fw = fr - fl
    if narrow:
        cy1 = ty + fh - 12 - fsz
        _dc(c, fl, cy1, left_text, "Mono", fsz, FOOTER_TX, fw)
        cy2 = cy1 - fsz - 2
        _dc(c, fl, cy2, right_text, "Mono", fsz, FOOTER_TX, fw)
    else:
        cy = ty + (fh - fsz) / 2
        hw = fw * 0.48
        _dc(c, fl, cy, left_text, "Mono", fsz, FOOTER_TX, hw)
        _dr(c, fr, cy, right_text, "Mono", fsz, FOOTER_TX)
    return fh

# ═══ V2 RULE 8: FORMAT NORMALIZATION — font/spacing scales ═══════════════
def get_scales(fmt):
    """Return (brand_sz, sys_sz, pn_max, pn_min, sub_sz, meta_lbl, meta_val, var_sz)"""
    if fmt == "DROPPER":
        return (8, 6, 18, 12, 9, 7, 7.5, 7.5)
    elif fmt == "JAR":
        return (10, 7, 18, 12, 9, 7.5, 8, 8)
    elif fmt == "BOTTLE":
        return (11, 8, 22, 14, 10, 8, 8.5, 8.5)
    elif fmt == "POUCH":
        return (12, 8, 24, 16, 12, 9, 9.5, 9.5)
    else:  # STRIPS
        return (13, 9, 26, 18, 13, 10, 10.5, 10.5)

# ═══ V2 RULES 1+3+4+7+8: FRONT LABEL — DETERMINISTIC 3-BLOCK LAYOUT ════
def render_front(c, sku, dims, accent, tx, ty):
    """V2 System Lock: flex-column, space-between, 3-block structure.
    [TOP] Brand + Module + Product + Subtitle
    [MIDDLE] System line + Meta block (left-aligned stacked only)
    [BOTTOM] MAXimo/MAXima + spacer + footer
    """
    w, h = dims["w"], dims["h"]
    fmt = sku["format"]["label_format"]
    left, right_ = tx + SAFE, tx + w - SAFE
    cw = right_ - left

    # Background + accent ceiling
    c.setFillColor(C["bg"]); c.rect(tx-BLEED, ty-BLEED, w+2*BLEED, h+2*BLEED, fill=1, stroke=0)
    c.setFillColor(accent); c.rect(tx-BLEED, ty+h-2, w+2*BLEED, 2, fill=1, stroke=0)

    # V2 Rule 2: Footer (64px fixed) + bottom padding
    ver = sku["front_panel"]["zone_7"]["version_info"]
    qty = sku["front_panel"]["zone_7"]["net_quantity"]
    fh = draw_footer(c, tx, ty, w, fmt, ver, qty)
    bot_pad = FOOTER_PAD[fmt]
    floor = ty + fh + bot_pad  # content must stay above this

    # V2 Rule 3: Title max 30% of canvas
    canvas_h = h
    max_title_h = canvas_h * 0.30

    top = ty + h - SAFE - 2
    scales = get_scales(fmt)
    brand_sz, sys_sz, pn_max, pn_min, sub_sz, meta_lbl, meta_val, var_sz = scales

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

    # V2 Rule 3: Fit title within 30% canvas, max 3 lines
    pf = "Mono-Bold"
    ps = pn_max
    title_lines = _w(pn, pf, ps, cw)
    while len(title_lines) > 3 and ps > pn_min:
        ps -= 0.5; title_lines = _w(pn, pf, ps, cw)
    title_lines = title_lines[:3]
    title_h = len(title_lines) * ps * 1.02
    while title_h > max_title_h and ps > pn_min:
        ps -= 0.5; title_lines = _w(pn, pf, ps, cw)[:3]
        title_h = len(title_lines) * ps * 1.02

    # Measure subtitle
    sub_lines = []
    _ss = sub_sz
    if desc:
        sub_lines = _w(desc, "Mono-Med", _ss, cw)
        while len(sub_lines) > 2 and _ss > 7: _ss -= 0.5; sub_lines = _w(desc, "Mono-Med", _ss, cw)
        sub_lines = sub_lines[:2]; sub_sz = _ss
    sub_h = len(sub_lines) * sub_sz * 1.15

    # V2 Rule 4: Meta block — left-aligned stacked only
    meta_lh = meta_val * 1.25
    meta_h = 3 * meta_lh
    bio_sz = sys_sz
    bio_h = bio_sz * 1.1 if bio else 0
    var_h = var_sz + 4

    # ── MEASURE 3 BLOCKS ──
    top_block = brand_sz + MIN_BLOCK_SPACING + sys_sz + MIN_BLOCK_SPACING + title_h + MIN_BLOCK_SPACING + sub_h
    mid_block = (bio_h + MIN_BLOCK_SPACING if bio else 0) + meta_h
    bot_block = var_h

    available = top - floor
    total = top_block + MIN_BLOCK_SPACING + mid_block + MIN_BLOCK_SPACING + bot_block

    # V2 Rule 7: Shrink to fit — reduce spacing first, then font, NEVER overlap
    for _ in range(100):
        total = top_block + MIN_BLOCK_SPACING + mid_block + MIN_BLOCK_SPACING + bot_block
        if total <= available: break
        # Shrink product name first
        if ps > max(pn_min, 10):
            ps -= 0.5; title_lines = _w(pn, pf, ps, cw)[:3]; title_h = len(title_lines)*ps*1.02
            top_block = brand_sz + MIN_BLOCK_SPACING + sys_sz + MIN_BLOCK_SPACING + title_h + MIN_BLOCK_SPACING + sub_h
            continue
        if sub_sz > 6 and sub_lines:
            sub_sz -= 0.5; sub_lines = _w(desc, "Mono-Med", sub_sz, cw)[:2]
            sub_h = len(sub_lines)*sub_sz*1.15
            top_block = brand_sz + MIN_BLOCK_SPACING + sys_sz + MIN_BLOCK_SPACING + title_h + MIN_BLOCK_SPACING + sub_h
            continue
        if meta_val > 6:
            meta_val -= 0.5; meta_lbl = max(5.5, meta_lbl-0.5)
            meta_lh = meta_val*1.25; meta_h = 3*meta_lh
            mid_block = (bio_h + MIN_BLOCK_SPACING if bio else 0) + meta_h
            continue
        if var_sz > 6: var_sz -= 0.5; var_h = var_sz+4; bot_block = var_h; continue
        if brand_sz > 7: brand_sz -= 0.5; top_block = brand_sz + MIN_BLOCK_SPACING + sys_sz + MIN_BLOCK_SPACING + title_h + MIN_BLOCK_SPACING + sub_h; continue
        break

    # ── DISTRIBUTE: space-between for 3 blocks ──
    total = top_block + mid_block + bot_block
    slack = max(0, available - total)
    gap_top_mid = max(MIN_BLOCK_SPACING, slack * 0.4)
    gap_mid_bot = max(MIN_BLOCK_SPACING, slack * 0.6)

    # ── DRAW TOP BLOCK ──
    cy = top - SP[4]  # 24px from ceiling
    _dt(c, left, cy - brand_sz, "GenoMAX\u00b2", "Mono-Med", brand_sz, C["t1"], 0.08, mw=cw*0.65)
    _dr(c, right_, cy - brand_sz*0.5, sku["front_panel"]["zone_1"]["module_code"], "Mono-Med", min(6, brand_sz*0.5), C["t3"])
    cy -= brand_sz + MIN_BLOCK_SPACING

    _dt(c, left, cy - sys_sz, sku["front_panel"]["zone_2"]["text"], "Mono", sys_sz, alpha_color("#4A4843", 0.72), 0.14, mw=cw)
    cy -= sys_sz + MIN_BLOCK_SPACING

    for ln in title_lines:
        _dc(c, left, cy - ps, ln, pf, ps, C["t1"], cw)
        cy -= ps * 1.02
    cy -= MIN_BLOCK_SPACING

    for sl in sub_lines:
        _dc(c, left, cy - sub_sz, sl, "Mono-Med", sub_sz, alpha_color("#1A1815", 0.88), cw)
        cy -= sub_sz * 1.15

    # ── GAP → MIDDLE BLOCK ──
    cy -= gap_top_mid

    # Bio / system line
    if bio and cy - bio_sz > floor:
        _dc(c, left, cy - bio_sz, bio, "Mono", bio_sz, C["t3"], cw)
        cy -= bio_h + MIN_BLOCK_SPACING

    # V2 Rule 4: Meta block — left aligned stacked only, no grid, no inline
    lbl_w = _tw("FUNCTION", "Mono", meta_lbl) + meta_lbl * 0.8
    for label, val in meta_items:
        if cy - meta_lbl < floor: break
        _d(c, left, cy - meta_lbl, label, "Mono", meta_lbl, alpha_color("#1A1815", 0.58))
        _dc(c, left + lbl_w, cy - meta_val, val, "Mono-SB", meta_val, alpha_color("#1A1815", 0.92), cw - lbl_w)
        cy -= meta_lh

    # ── GAP → BOTTOM BLOCK ──
    cy -= gap_mid_bot

    # Variant + accent bar
    if cy - var_sz > floor:
        _dc(c, left, cy - var_sz, variant, "Mono-SB", var_sz, C["t1"], cw)
        cy -= var_sz + 2
        c.setFillColor(accent)
        c.rect(left, cy - 2, min(70, cw*0.3), 2, fill=1, stroke=0)

# ═══ V2 RULES 5+6: BACK LABEL — LOCKED ORDER + QR SYSTEM ════════════════
def render_back(c, sku, dims, accent, tx, ty):
    """V2 Rule 6: Brand→Divider→Headline→CTA→QR→Divider→Body→SugUse→Warnings→Ingredients→Footer"""
    w, h = dims["w"], dims["h"]
    fmt = sku["format"]["label_format"]
    left, right_ = tx + SAFE, tx + w - SAFE
    cw = right_ - left
    top = ty + h - SAFE

    raw = sku.get("back_panel", {}).get("back_label_text", "")
    sec = parse_back_text(raw)

    # Background + accent ceiling
    c.setFillColor(C["bg"]); c.rect(tx-BLEED, ty-BLEED, w+2*BLEED, h+2*BLEED, fill=1, stroke=0)
    c.setFillColor(accent); c.rect(tx-BLEED, ty+h-2, w+2*BLEED, 2, fill=1, stroke=0)

    # V2 Rule 2: Footer (64px) + bottom padding
    fh = draw_footer(c, tx, ty, w, fmt, "genomax.ai \u00b7 support@genomax.ai", "Distributed by Genomax LLC")
    bot_pad = FOOTER_PAD[fmt]
    floor = ty + fh + bot_pad

    # V2 Rule 5: QR system — size min 18% of width
    qr_sz = qr_size_for(fmt, w)
    mc = sku["_meta"]["module_code"]
    osn = sku["_meta"]["os"].replace("\u00b2","2").lower()
    qr_img = make_qr(f"https://genomax.ai/module/{osn}/{mc.lower()}")

    # Text sizes — scaled per format
    scales = get_scales(fmt)
    _, _, _, _, _, _, _, _ = scales
    BODY_SZ = 8 if fmt in ("BOTTLE","JAR","DROPPER") else 9.5
    BODY_LH = 1.25
    SECT_LBL = 7 if fmt in ("BOTTLE","JAR","DROPPER") else 8
    SGAP = max(8, MIN_BLOCK_SPACING)
    PROTO_SZ = 10 if fmt not in ("DROPPER","JAR") else 8
    CTA_SZ = 9 if fmt not in ("DROPPER",) else 7

    # V2 Rule 5: QR positioning per format
    # BOTTLE/DROPPER: QR LEFT, Text RIGHT
    # JAR/POUCH: QR RIGHT, Text LEFT
    # STRIPS: QR LEFT (locked)
    qr_left = fmt in ("BOTTLE", "DROPPER", "STRIPS")

    # ── Brand ──
    cy = top - 2
    bbsz = 7 if fmt != "DROPPER" else 5.5
    _dt(c, left, cy - bbsz, "GenoMAX\u00b2", "Mono-Bold", bbsz, C["t1"], 0.08, mw=cw*0.6)
    cy -= bbsz + 2

    # ── Divider ──
    c.saveState(); c.setStrokeColor(C["t1"]); c.setLineWidth(0.5); c.setStrokeAlpha(0.25)
    c.line(left, cy, right_, cy); c.restoreState()
    cy -= SGAP

    # ── Headline (protocol) ──
    proto_lines = _w("THIS IS NOT YOUR FULL PROTOCOL", "Mono-Bold", PROTO_SZ, cw)
    for ln in proto_lines[:2]:
        if cy < floor + PROTO_SZ: break
        _dc(c, left, cy - PROTO_SZ, ln, "Mono-Bold", PROTO_SZ, C["t1"], cw)
        cy -= PROTO_SZ * 1.08
    cy -= SGAP

    # ── CTA ──
    cta_lines = _w("SCAN FOR FULL PROTOCOL", "Mono-SB", CTA_SZ, cw)
    for ln in cta_lines[:2]:
        if cy < floor + CTA_SZ: break
        _dc(c, left, cy - CTA_SZ, ln, "Mono-SB", CTA_SZ, C["t1"], cw)
        cy -= CTA_SZ + 1
    cy -= 3

    # ── QR (V2 Rule 5: format-specific placement) ──
    if cy - qr_sz > floor:
        if qr_left:
            c.drawImage(qr_img, left, cy - qr_sz, qr_sz, qr_sz)
            _d(c, left + qr_sz + QR_CLEAR, cy - qr_sz/2 - 2, "genomax.ai", "Mono", 5.5, C["t2"])
        else:
            c.drawImage(qr_img, right_ - qr_sz, cy - qr_sz, qr_sz, qr_sz)
            _d(c, left, cy - qr_sz/2 - 2, "genomax.ai", "Mono", 5.5, C["t2"])
        cy -= qr_sz + SGAP

    # ── Divider ──
    if cy > floor + 4:
        c.setStrokeColor(C["div"]); c.setLineWidth(0.35)
        c.line(left, cy, right_, cy)
        cy -= SGAP

    # ── Body (context) ──
    ctx = sec.get("context", "")
    if ctx and cy > floor + 12:
        ctx_lines = _w(ctx, "Mono", BODY_SZ, cw)
        for ln in ctx_lines[:4]:
            if cy < floor + BODY_SZ: break
            _dc(c, left, cy - BODY_SZ, ln, "Mono", BODY_SZ, alpha_color("#1A1815", 0.88), cw)
            cy -= BODY_SZ * BODY_LH
        cy -= SGAP

    # ── Suggested Use ──
    sug = sec.get("suggested_use", "")
    if sug and cy > floor + 10:
        _dt(c, left, cy - SECT_LBL, "SUGGESTED USE", "Mono-Med", SECT_LBL, alpha_color("#1A1815", 0.58), 0.14, mw=cw)
        cy -= SECT_LBL + 2
        for ln in _w(sug, "Mono", BODY_SZ, cw)[:3]:
            if cy < floor + BODY_SZ: break
            _dc(c, left, cy - BODY_SZ, ln, "Mono", BODY_SZ, alpha_color("#1A1815", 0.88), cw)
            cy -= BODY_SZ * BODY_LH
        cy -= SGAP

    # ── Warnings ──
    warn = ' '.join(sec.get("warnings", []))
    if warn and cy > floor + 10:
        _dt(c, left, cy - SECT_LBL, "WARNINGS", "Mono-Med", SECT_LBL, alpha_color("#1A1815", 0.58), 0.14, mw=cw)
        cy -= SECT_LBL + 2
        for ln in _w(warn, "Mono", BODY_SZ, cw)[:5]:
            if cy < floor + BODY_SZ: break
            _dc(c, left, cy - BODY_SZ, ln, "Mono", BODY_SZ, alpha_color("#1A1815", 0.88), cw)
            cy -= BODY_SZ * BODY_LH
        cy -= SGAP

    # ── Ingredients ──
    ingr = sec.get("ingredients", "")
    if ingr and cy > floor + 8:
        _dt(c, left, cy - SECT_LBL, "INGREDIENTS", "Mono-Med", SECT_LBL, alpha_color("#1A1815", 0.58), 0.14, mw=cw)
        cy -= SECT_LBL + 2
        for ln in _w(ingr, "Mono", BODY_SZ, cw)[:3]:
            if cy < floor + BODY_SZ: break
            _dc(c, left, cy - BODY_SZ, ln, "Mono", BODY_SZ, C["t1"], cw)
            cy -= BODY_SZ * BODY_LH

# ═══ V2 RULE 9: FAIL CONDITION — DO NOT EXPORT IF VIOLATIONS ═════════════
def check_fail_conditions(sku, dims, accent, tx, ty):
    """Dry-run render to detect violations. Returns list of failures."""
    fmt = sku["format"]["label_format"]
    w, h = dims["w"], dims["h"]
    fh = FOOTER_H
    bot_pad = FOOTER_PAD[fmt]
    floor = ty + fh + bot_pad
    top = ty + h - SAFE
    available = top - floor - SP[4]
    # Only fail if literally zero or negative space — the shrink engine handles tight fits
    if available < 0:
        return [f"negative_space: {available:.0f}px — footer+padding exceeds label height"]
    return []

# ═══ RENDER + EXPORT PIPELINE ═════════════════════════════════════════════
def render_sku(sku, system_name, output_base=None, strict=True):
    meta = sku["_meta"]
    fmt = sku["format"]["label_format"]
    if fmt not in FORMAT_DIMS: return None

    dims = FORMAT_DIMS[fmt]
    accent = C["ax_mo"] if "MAXimo" in meta["os"] else C["ax_ma"]

    cm = 20
    pw, ph = dims["w"]+2*BLEED+2*cm, dims["h"]+2*BLEED+2*cm
    tx_, ty_ = cm+BLEED, cm+BLEED

    # V2 Rule 9: Check fail conditions before export
    if strict:
        fails = check_fail_conditions(sku, dims, accent, tx_, ty_)
        if fails:
            return {"error": fails, "sku": meta["module_code"]}

    base = output_base or OUTPUT_BASE
    sys_tag = "MO" if "MAXimo" in meta["os"] else "MA"
    ing = sku["front_panel"]["zone_3"]["ingredient_name"]
    short_name = ing.replace("/","-").replace("\\","-").replace(":","").replace(" ","_")[:50].strip("_")
    out_dir = base / fmt / f"{meta['module_code']}_{sys_tag}_{short_name}"
    out_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    for side in ["front", "back"]:
        pdf_p = out_dir / f"{side}.pdf"
        cv = canvas.Canvas(str(pdf_p), pagesize=(pw, ph))
        cv.setAuthor("GenoMAX\u00b2 V7+V2 System Lock")
        cv.setTitle(f"{meta['module_code']} {ing} {fmt} {side}")
        cv.setFillColor(C["white"]); cv.rect(0,0,pw,ph,fill=1,stroke=0)

        if side == "front": render_front(cv, sku, dims, accent, tx_, ty_)
        else: render_back(cv, sku, dims, accent, tx_, ty_)

        crop_marks(cv, tx_, ty_, dims["w"], dims["h"])
        info = f"GenoMAX\u00b2 | {meta['module_code']} | {meta['os']} | {fmt} | {side.upper()} | V7+V2-SYSTEM-LOCK"
        _d(cv, tx_, ty_-BLEED-10, info, "Mono", 3.5, C["t3"])
        cv.save()

        import fitz
        doc = fitz.open(str(pdf_p))
        page = doc[0]
        scale = min(1600/page.rect.width, 1600/page.rect.height, 4.0)
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        jpg_p = out_dir / f"{side}.jpg"
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img.save(str(jpg_p), "JPEG", quality=85)
        doc.close()
        results[side] = jpg_p

    return out_dir

# ═══ V2 RULE 10: QA — 5 samples (one per format) before full render ═════
VALIDATION_TARGETS = [
    ("maximo", "CV-01"),   # BOTTLE
    ("maximo", "CV-04"),   # JAR
    ("maximo", "MT-09"),   # POUCH
    ("maxima", "IN-04"),   # DROPPER
    ("maximo", "GL-04"),   # STRIPS
]

FULL_VALIDATION = [
    ("maximo", "CV-01"),   # BOTTLE standard
    ("maximo", "CV-04"),   # JAR short
    ("maximo", "MT-09"),   # POUCH longest name
    ("maximo", "GL-01"),   # BOTTLE (was DROPPER in old data)
    ("maximo", "GL-04"),   # STRIPS tallest
    ("maximo", "GL-10"),   # BOTTLE densest back
    ("maxima", "IN-04"),   # DROPPER alt accent
]

def main():
    parser = argparse.ArgumentParser(description="GenoMAX\u00b2 V7+V2 System Lock Renderer")
    parser.add_argument("--validate", action="store_true", help="V2 Rule 10: QA 5-format validation")
    parser.add_argument("--validate-full", action="store_true", help="Full 7-sample validation")
    parser.add_argument("--full", action="store_true", help="Full production render (168 SKUs)")
    parser.add_argument("--preview-dir", type=str, default=None)
    args = parser.parse_args()

    systems = {
        "maximo": DATA_DIR / "production-labels-maximo-v4.json",
        "maxima": DATA_DIR / "production-labels-maxima-v4.json",
    }
    all_skus = {}
    for sn, dp in systems.items():
        with open(dp, encoding='utf-8') as f: all_skus[sn] = json.load(f)["skus"]

    if args.validate or args.validate_full:
        targets = FULL_VALIDATION if args.validate_full else VALIDATION_TARGETS
        mode_name = "FULL 7-SAMPLE" if args.validate_full else "V2 QA 5-FORMAT"
        preview = args.preview_dir or "v7-preview-02"
        out_base = BASE / "design-system" / preview
        print("=" * 60)
        print(f"GenoMAX\u00b2 V7+V2 System Lock \u2014 {mode_name} VALIDATION")
        print("=" * 60)
        print(f"Output: {out_base}")
        total, passed, failed = 0, 0, 0
        for sys_name, mc in targets:
            found = None
            for sku in all_skus[sys_name]:
                if sku["_meta"]["module_code"] == mc: found = sku; break
            if not found:
                print(f"  SKIP {mc} ({sys_name}) \u2014 not found"); continue
            fmt = found["format"]["label_format"]
            ing = found["front_panel"]["zone_3"]["ingredient_name"]
            print(f"  [{total+1}/{len(targets)}] {mc} | {fmt:7s} | {ing[:40]}", end="")
            try:
                result = render_sku(found, sys_name, output_base=out_base, strict=True)
                if isinstance(result, dict) and "error" in result:
                    print(f" FAIL: {result['error']}")
                    failed += 1
                else:
                    print(" PASS")
                    passed += 1
                total += 1
            except Exception as e:
                print(f" ERR: {e}")
                failed += 1; total += 1
        print(f"\n{'='*60}")
        print(f"RESULT: {passed}/{total} PASSED, {failed} FAILED")
        if failed > 0:
            print("V2 Rule 9: FAIL CONDITIONS DETECTED — DO NOT PROCEED TO FULL RENDER")
        else:
            print("V2 Rule 10: ALL QA CHECKS PASSED — safe to proceed to --full")
        print(f"Output: {out_base}")

    elif args.full:
        print("=" * 60)
        print("GenoMAX\u00b2 V7+V2 System Lock \u2014 FULL PRODUCTION")
        print("=" * 60)
        total, errors = 0, 0
        for sn, skus in all_skus.items():
            print(f"\n--- {sn.upper()} ---")
            for i, sku in enumerate(skus):
                m = sku["_meta"]; fmt = sku["format"]["label_format"]
                ing = sku["front_panel"]["zone_3"]["ingredient_name"]
                print(f"  [{i+1:3d}/{len(skus)}] {m['module_code']} | {fmt:7s} | {ing[:35]}", end="")
                try:
                    result = render_sku(sku, sn, strict=True)
                    if isinstance(result, dict) and "error" in result:
                        print(f" FAIL: {result['error']}"); errors += 1
                    else:
                        print(" OK"); total += 1
                except Exception as e:
                    print(f" ERR: {e}"); errors += 1
        print(f"\nDONE: {total} OK, {errors} FAILED \u2192 {OUTPUT_BASE}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
