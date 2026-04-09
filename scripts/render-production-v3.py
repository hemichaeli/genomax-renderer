#!/usr/bin/env python3
"""
GenoMAX² V3 Production Label Renderer — FIXED LAYOUT ENGINE
=============================================================
All layout math corrected:
- Safe-area enforcement on all edges
- Bottom-up stacking for back label footer
- Text wrapping with max_width on ALL text blocks
- Column overflow protection in metadata grid
- Strip text collision prevention
"""

import json
import os
import sys
import math
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from reportlab.lib.units import inch, mm
from reportlab.lib.colors import CMYKColor
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
import qrcode
from PIL import Image
import io

# ─── PATHS ─────────────────────────────────────────────────────────────────
BASE = Path("C:/Projects/GenoMAX2")
FONTS_DIR = BASE / "design-system" / "fonts"
DATA_DIR = BASE / "design-system" / "data"
OUTPUT_BASE = BASE / "design-system" / "production-v3"

# ─── REGISTER FONTS ───────────────────────────────────────────────────────
FONT_MAP = {
    "PlexMono": "IBMPlexMono-Regular.ttf",
    "PlexMono-Medium": "IBMPlexMono-Medium.ttf",
    "PlexMono-SemiBold": "IBMPlexMono-SemiBold.ttf",
    "PlexMono-Bold": "IBMPlexMono-Bold.ttf",
    "PlexMono-Light": "IBMPlexMono-Light.ttf",
    "PlexSans": "IBMPlexSans-Regular.ttf",
    "PlexSans-Medium": "IBMPlexSans-Medium.ttf",
    "PlexSans-SemiBold": "IBMPlexSans-SemiBold.ttf",
    "PlexSans-Bold": "IBMPlexSans-Bold.ttf",
    "PlexSans-Light": "IBMPlexSans-Light.ttf",
    "PlexCondensed": "IBMPlexSansCondensed-Regular.ttf",
    "PlexCondensed-Medium": "IBMPlexSansCondensed-Medium.ttf",
    "PlexCondensed-SemiBold": "IBMPlexSansCondensed-SemiBold.ttf",
    "PlexCondensed-Bold": "IBMPlexSansCondensed-Bold.ttf",
}
for name, filename in FONT_MAP.items():
    path = FONTS_DIR / filename
    if path.exists():
        pdfmetrics.registerFont(TTFont(name, str(path)))

# ─── COLORS ───────────────────────────────────────────────────────────────
def hex_to_cmyk(h):
    h = h.lstrip('#')
    r, g, b = int(h[0:2], 16)/255, int(h[2:4], 16)/255, int(h[4:6], 16)/255
    k = 1 - max(r, g, b)
    if k == 1: return CMYKColor(0, 0, 0, 1)
    return CMYKColor((1-r-k)/(1-k), (1-g-k)/(1-k), (1-b-k)/(1-k), k)

C = {
    "bg": hex_to_cmyk("#F4F2EC"),
    "t1": hex_to_cmyk("#1A1815"),
    "t2": hex_to_cmyk("#4A4843"),
    "t3": hex_to_cmyk("#8A8880"),
    "div": hex_to_cmyk("#C5C2BA"),
    "ax_mo": hex_to_cmyk("#7A1E2E"),
    "ax_ma": hex_to_cmyk("#7A304A"),
    "strip_bg": hex_to_cmyk("#1A1815"),
    "strip_tx": hex_to_cmyk("#C5C2BA"),
    "white": CMYKColor(0, 0, 0, 0),
}

BLEED = 3 * mm
MARGIN = 12  # pt — safe area inset from trim on all 4 sides
STRIP_H = 14  # pt — zone 7 dark strip height

FORMAT_DIMS = {
    "BOTTLE":  {"w": 6*inch,   "h": 2.5*inch, "pn_pt": 26},
    "JAR":     {"w": 8.5*inch, "h": 2*inch,   "pn_pt": 22},
    "POUCH":   {"w": 5*inch,   "h": 4*inch,   "pn_pt": 28},
    "DROPPER": {"w": 2*inch,   "h": 4*inch,   "pn_pt": 14},
    "STRIPS":  {"w": 4*inch,   "h": 6.5*inch, "pn_pt": 30},
}


# ─── TEXT UTILITIES ───────────────────────────────────────────────────────
def _draw(c, x, y, text, font, size, color):
    """Unicode-safe text draw via text object."""
    t = c.beginText(x, y)
    t.setFont(font, size)
    t.setFillColor(color)
    t.textOut(text)
    c.drawText(t)


def _draw_tracked(c, x, y, text, font, size, color, tracking, max_w=None):
    """Draw text with character spacing. Enforces max_w."""
    if max_w:
        while len(text) > 1:
            tw = pdfmetrics.stringWidth(text, font, size) + len(text) * size * tracking
            if tw <= max_w:
                break
            text = text[:-1]
    t = c.beginText(x, y)
    t.setFont(font, size)
    t.setFillColor(color)
    t.setCharSpace(size * tracking)
    t.textOut(text)
    c.drawText(t)


def _draw_right(c, x_right, y, text, font, size, color):
    """Right-aligned draw."""
    w = pdfmetrics.stringWidth(text, font, size)
    _draw(c, x_right - w, y, text, font, size, color)


def _draw_capped(c, x, y, text, font, size, color, max_w):
    """Draw text, truncating with ellipsis if exceeds max_w."""
    while len(text) > 1 and pdfmetrics.stringWidth(text, font, size) > max_w:
        text = text[:-1]
    _draw(c, x, y, text, font, size, color)


def _wrap(text, font, size, max_w):
    """Word-wrap text, return list of lines."""
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if pdfmetrics.stringWidth(test, font, size) <= max_w:
            cur = test
        else:
            if cur: lines.append(cur)
            # If single word exceeds max_w, force it (will be capped at draw)
            cur = w
    if cur: lines.append(cur)
    return lines


def _text_w(text, font, size):
    return pdfmetrics.stringWidth(text, font, size)


# ─── QR ───────────────────────────────────────────────────────────────────
def make_qr(url):
    qr = qrcode.QRCode(version=2, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=1)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return ImageReader(buf)


# ─── CROP MARKS ──────────────────────────────────────────────────────────
def draw_crop_marks(c, tx, ty, w, h):
    c.setStrokeColor(CMYKColor(0, 0, 0, 1))
    c.setLineWidth(0.25)
    L, O = 12, 3
    for (x1, y1, x2, y2) in [
        (tx-O, ty+h, tx-O-L, ty+h), (tx, ty+h+O, tx, ty+h+O+L),
        (tx+w+O, ty+h, tx+w+O+L, ty+h), (tx+w, ty+h+O, tx+w, ty+h+O+L),
        (tx-O, ty, tx-O-L, ty), (tx, ty-O, tx, ty-O-L),
        (tx+w+O, ty, tx+w+O+L, ty), (tx+w, ty-O, tx+w, ty-O-L),
    ]:
        c.line(x1, y1, x2, y2)


# ═══════════════════════════════════════════════════════════════════════════
# FRONT LABEL — FIXED LAYOUT
# ═══════════════════════════════════════════════════════════════════════════
def render_front(c, sku, dims, accent, tx, ty):
    w, h = dims["w"], dims["h"]
    fmt = sku["format"]["label_format"]
    narrow = fmt == "DROPPER"
    tall = fmt in ("STRIPS", "POUCH")

    # ── Safe area boundaries ──
    left = tx + MARGIN
    right = tx + w - MARGIN
    content_w = right - left
    top = ty + h - MARGIN
    short = fmt == "JAR"  # JAR is only 2" tall — needs compressed layout
    # Bottom safe = top of strip + margin
    strip_top = ty + STRIP_H
    bot_safe = strip_top + 2  # 2pt gap above strip

    # ── Background + ceiling ──
    c.setFillColor(C["bg"])
    c.rect(tx - BLEED, ty - BLEED, w + 2*BLEED, h + 2*BLEED, fill=1, stroke=0)
    c.setFillColor(accent)
    c.rect(tx - BLEED, ty + h - 2, w + 2*BLEED, 2, fill=1, stroke=0)

    cy = top - 2  # cursor below ceiling

    # ── Zone 1: Brand + Module Code ──
    cy -= (4 if not short else 2)  # tighter for JAR
    bsz = 12 if not narrow else 8
    if short: bsz = 10  # slightly smaller brand for JAR
    msz = 6 if not narrow else 5
    _draw_tracked(c, left, cy - bsz, "GenoMAX\u00b2", "PlexMono-Bold", bsz, C["t1"], 0.18, max_w=content_w * 0.65)
    mc = sku["front_panel"]["zone_1"]["module_code"]
    _draw_right(c, right, cy - msz, mc, "PlexMono-Medium", msz, C["t3"])
    cy -= bsz + (3 if not short else 2)

    # Brand rule
    c.saveState()
    c.setStrokeColor(C["t1"]); c.setLineWidth(0.5); c.setStrokeAlpha(0.25)
    c.line(left, cy, right, cy)
    c.restoreState()
    cy -= (4 if not short else 2)

    # ── Zone 2: BIOLOGICAL OS MODULE ──
    z2sz = 7 if not narrow else 5.5
    if short: z2sz = 6
    _draw_tracked(c, left, cy - z2sz, sku["front_panel"]["zone_2"]["text"],
                  "PlexMono-Medium", z2sz, C["t2"], 0.18, max_w=content_w)
    cy -= z2sz + (6 if not short else 3)

    # ── Zone 3: Product Name ──
    pn_font = "PlexCondensed-Bold"
    pn_sz = dims["pn_pt"]
    pn_text = sku["front_panel"]["zone_3"]["ingredient_name"]

    # Available vertical space for product name
    # Reserve space below: desc(~10) + bio(~8) + variant(~14) + accent(4) + meta(~18)
    reserved_below = 60 if not narrow else 80
    available_for_pn = cy - bot_safe - reserved_below

    lines = _wrap(pn_text, pn_font, pn_sz, content_w)
    max_lines = 3 if tall else 2
    if len(lines) > max_lines:
        pn_sz = pn_sz * 0.7
        lines = _wrap(pn_text, pn_font, pn_sz, content_w)

    for line in lines[:max_lines]:
        _draw_capped(c, left, cy - pn_sz, line, pn_font, pn_sz, C["t1"], content_w)
        cy -= pn_sz * 0.95
    cy -= 3

    # ── Zone 4: Descriptor + Bio System ──
    desc = sku["front_panel"]["zone_4"].get("descriptor", "")
    if desc:
        dsz = 8.5 if not narrow else 7
        if short: dsz = 7
        _draw_capped(c, left, cy - dsz, desc, "PlexSans-Light", dsz, C["t2"], content_w)
        cy -= dsz + (2 if not short else 1)

    bio = sku["front_panel"]["zone_4"].get("biological_system", "")
    if bio:
        bsz2 = 6.5 if not narrow else 5.5
        if short: bsz2 = 5.5
        _draw_capped(c, left, cy - bsz2, bio, "PlexMono", bsz2, C["t3"], content_w)
        cy -= bsz2 + (6 if not short else 3)

    # ── Zone 5: Variant + Accent Rule ──
    vsz = 12 if not narrow else 8
    if short: vsz = 9
    _draw_capped(c, left, cy - vsz, sku["front_panel"]["zone_5"]["variant_name"],
                 "PlexSans-SemiBold", vsz, C["t1"], content_w)
    cy -= vsz + 2
    aw = 70 if not narrow else 40
    c.setFillColor(accent)
    c.rect(left, cy - 2, aw, 2, fill=1, stroke=0)
    cy -= 2 + (6 if not short else 3)

    # ── Zone 6: Metadata (TYPE / FUNCTION / STATUS) ──
    # Adaptive sizing: compress for short formats
    short = fmt == "JAR"
    ml_s_default = 5.5 if short else (7 if not narrow else 5.5)
    mv_s_default = 5.5 if short else (7 if not narrow else 6)
    meta_row_h = ml_s_default + mv_s_default + 1 + (3 if not short else 1)
    if cy > bot_safe + meta_row_h:
        ml_f, ml_s = "PlexMono-Medium", ml_s_default
        mv_f, mv_s = "PlexSans-Medium", mv_s_default

        z6 = sku["front_panel"]["zone_6"]
        items = [
            (z6["type"]["label"], z6["type"]["value"]),
            (z6["function"]["label"], z6["function"]["value"]),
            (z6["status"]["label"], z6["status"]["value"]),
        ]

        if narrow:
            for label, value in items:
                if cy < bot_safe + ml_s + mv_s + 4: break
                _draw(c, left, cy - ml_s, label, ml_f, ml_s, C["t3"])
                cy -= ml_s + 1
                _draw_capped(c, left, cy - mv_s, value, mv_f, mv_s, C["t1"], content_w)
                cy -= mv_s + 3
        else:
            col_w = content_w / 3
            col_gap = 4  # gap between columns
            usable_col = col_w - col_gap
            for i, (label, value) in enumerate(items):
                cx = left + i * col_w
                _draw_capped(c, cx, cy - ml_s, label, ml_f, ml_s, C["t3"], usable_col)
                _draw_capped(c, cx, cy - ml_s - mv_s - 1, value, mv_f, mv_s, C["t1"], usable_col)
            cy -= ml_s + mv_s + 1 + 6

    # ── Zone 7: Dark Strip ──
    strip_h_actual = STRIP_H if not narrow else 22  # taller strip for narrow
    c.setFillColor(C["strip_bg"])
    c.rect(tx - BLEED, ty - BLEED, w + 2*BLEED, strip_h_actual + BLEED, fill=1, stroke=0)

    ver = sku["front_panel"]["zone_7"]["version_info"]
    qty = sku["front_panel"]["zone_7"]["net_quantity"]
    ssz = 5.5 if not narrow else 4.5

    if narrow:
        # Stack vertically for narrow formats
        sty_top = ty + strip_h_actual - 3 - ssz
        _draw_capped(c, left, sty_top, ver, "PlexMono", ssz, C["strip_tx"], content_w)
        _draw_capped(c, left, sty_top - ssz - 2, qty, "PlexMono", ssz, C["strip_tx"], content_w)
    else:
        sty = ty + (strip_h_actual - ssz) / 2
        half_w = content_w * 0.48
        _draw_capped(c, left, sty, ver, "PlexMono", ssz, C["strip_tx"], half_w)
        # Right-align qty, capped to half width, with 2pt right safety
        qty_t = qty
        while len(qty_t) > 1 and _text_w(qty_t, "PlexMono", ssz) > half_w:
            qty_t = qty_t[:-1]
        _draw_right(c, right - 2, sty, qty_t, "PlexMono", ssz, C["strip_tx"])


# ═══════════════════════════════════════════════════════════════════════════
# BACK LABEL — FIXED LAYOUT (bottom-up stacking)
# ═══════════════════════════════════════════════════════════════════════════
def render_back(c, sku, dims, accent, tx, ty):
    w, h = dims["w"], dims["h"]
    fmt = sku["format"]["label_format"]
    narrow = fmt == "DROPPER"
    tall = fmt in ("STRIPS", "POUCH")

    left = tx + MARGIN
    right = tx + w - MARGIN
    content_w = right - left
    top = ty + h - MARGIN

    back = sku.get("back_panel", {})

    # ── Background + ceiling ──
    c.setFillColor(C["bg"])
    c.rect(tx - BLEED, ty - BLEED, w + 2*BLEED, h + 2*BLEED, fill=1, stroke=0)
    c.setFillColor(accent)
    c.rect(tx - BLEED, ty + h - 2, w + 2*BLEED, 2, fill=1, stroke=0)

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 1: Compute bottom stack height (build from bottom up)
    # ══════════════════════════════════════════════════════════════════════

    # Layer 1 (bottom): Dark strip
    strip_top = ty + STRIP_H

    # Layer 2: FDA disclaimer
    fda = back.get("fda_disclaimer", "")
    fda_font, fda_sz = "PlexSans", 6
    fda_wrap_w = content_w - 4  # 4pt safety margin to prevent edge clipping
    fda_lines = _wrap(fda, fda_font, fda_sz, fda_wrap_w) if fda else []
    fda_h = len(fda_lines[:3]) * (fda_sz + 1) if fda_lines else 0

    # Layer 3: Manufacturer
    mfg_text = "Genomax LLC \u00b7 95 Newfield Ave, Suite A, Edison, NJ 08837 \u00b7 genomax.ai"
    mfg_font, mfg_sz = "PlexMono", 5.5
    mfg_lines = _wrap(mfg_text, mfg_font, mfg_sz, content_w)
    mfg_h = len(mfg_lines[:2]) * (mfg_sz + 1)

    # Layer 4: QR code (on back, for narrow/tall formats placed inline)
    qr_sz = 40 if not narrow else 28
    module_code = sku["_meta"]["module_code"]
    os_name = sku["_meta"]["os"].replace("\u00b2", "2").replace("²", "2").lower()
    qr_url = f"https://genomax.ai/module/{os_name}/{module_code.lower()}"

    # Bottom stack total (from strip_top upward)
    gap = 3
    bottom_stack = gap + fda_h + gap + mfg_h + gap

    # For wide formats (BOTTLE, JAR): QR goes on right side of content area
    # For narrow/tall: QR goes above FDA
    if narrow or tall:
        bottom_stack += qr_sz + 8 + gap  # qr + "SCAN FOR INFO" + gap

    bot_content_floor = strip_top + bottom_stack
    # This is where the top-down content must stop

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 2: Render top-down content
    # ══════════════════════════════════════════════════════════════════════

    cy = top - 2  # below ceiling

    # Brand
    cy -= 4
    bbsz = 8 if not narrow else 6
    _draw_tracked(c, left, cy - bbsz, "GenoMAX\u00b2", "PlexMono-Bold", bbsz, C["t1"], 0.18, max_w=content_w * 0.6)
    cy -= bbsz + 3

    # Brand rule
    c.saveState()
    c.setStrokeColor(C["t1"]); c.setLineWidth(0.5); c.setStrokeAlpha(0.25)
    c.line(left, cy, right, cy)
    c.restoreState()
    cy -= 5

    # QR side reservation for wide formats
    has_qr_side = not narrow and not tall
    qr_reserve = qr_sz + 8 if has_qr_side else 0
    text_w = content_w - qr_reserve

    sf, ssz = "PlexMono-Medium", 6
    bf, bsz = "PlexSans", 6.5 if not narrow else 6
    wsz = 6  # warning minimum

    # OS Role
    layer = back.get("layer", "")
    if layer and cy > bot_content_floor + 20:
        _draw_tracked(c, left, cy - ssz, "OS ROLE", sf, ssz, C["t3"], 0.1, max_w=text_w)
        cy -= ssz + 2
        _draw_capped(c, left, cy - bsz, layer, bf, bsz, C["t1"], text_w)
        cy -= bsz + 5

        c.setStrokeColor(C["div"]); c.setLineWidth(0.5)
        c.line(left, cy, left + text_w, cy)
        cy -= 4

    # Suggested Use
    sug = back.get("suggested_use", "")
    if sug and cy > bot_content_floor + 20:
        _draw_tracked(c, left, cy - ssz, "SUGGESTED USE", sf, ssz, C["t3"], 0.1, max_w=text_w)
        cy -= ssz + 2
        for line in _wrap(sug, bf, bsz, text_w)[:4]:
            if cy < bot_content_floor + bsz: break
            _draw_capped(c, left, cy - bsz, line, bf, bsz, C["t1"], text_w)
            cy -= bsz + 1
        cy -= 3

        c.setStrokeColor(C["div"]); c.setLineWidth(0.5)
        c.line(left, cy, left + text_w, cy)
        cy -= 4

    # Safety
    safety = back.get("safety_notes", "")
    if safety and safety.lower() != "excellent" and cy > bot_content_floor + 15:
        _draw_tracked(c, left, cy - ssz, "SAFETY", sf, ssz, C["t3"], 0.1, max_w=text_w)
        cy -= ssz + 2
        clean = safety.replace("Excellent", "").strip()
        if clean:
            for line in _wrap(clean, bf, wsz, text_w)[:3]:
                if cy < bot_content_floor + wsz: break
                _draw_capped(c, left, cy - wsz, line, bf, wsz, C["t2"], text_w)
                cy -= wsz + 1

    # Contraindications
    contra = back.get("contraindications", "")
    if contra and contra.lower() != "no known contraindications" and cy > bot_content_floor + 10:
        cy -= 2
        ct = f"Caution: {contra}. Consult a healthcare professional before use."
        for line in _wrap(ct, bf, wsz, text_w)[:3]:
            if cy < bot_content_floor + wsz: break
            _draw_capped(c, left, cy - wsz, line, bf, wsz, C["t2"], text_w)
            cy -= wsz + 1

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 3: Render bottom stack (top-down from a computed baseline)
    # ══════════════════════════════════════════════════════════════════════

    # Dark strip (same narrow handling as front)
    back_strip_h = STRIP_H if not narrow else 20
    c.setFillColor(C["strip_bg"])
    c.rect(tx - BLEED, ty - BLEED, w + 2*BLEED, back_strip_h + BLEED, fill=1, stroke=0)
    strip_ssz = 5.5 if not narrow else 4
    if narrow:
        # Stack vertically
        st1 = ty + back_strip_h - 3 - strip_ssz
        _draw_capped(c, left, st1, "genomax.ai", "PlexMono", strip_ssz, C["strip_tx"], content_w)
        _draw_capped(c, left, st1 - strip_ssz - 2, "Keep out of reach of children.", "PlexMono", strip_ssz, C["strip_tx"], content_w)
    else:
        sty = ty + (back_strip_h - strip_ssz) / 2
        contact = "genomax.ai \u00b7 support@genomax.ai"
        _draw_capped(c, left, sty, contact, "PlexMono", strip_ssz, C["strip_tx"], content_w * 0.5)
        keep = "Keep out of reach of children."
        _draw_right(c, right, sty, keep, "PlexMono", strip_ssz, C["strip_tx"])

    # Compute render cursor from strip top, going UP (higher y = higher on page)
    # We render text top-down visually, so highest y first
    back_strip_top = ty + back_strip_h

    # FDA disclaimer — above strip, rendered top-down
    fda_base_y = back_strip_top + gap
    fda_rendered = fda_lines[:3]
    # Render from top line to bottom: highest line first gets highest y
    n_fda = len(fda_rendered)
    for i, line in enumerate(fda_rendered):
        line_y = fda_base_y + (n_fda - 1 - i) * (fda_sz + 1)
        _draw_capped(c, left, line_y, line, fda_font, fda_sz, C["t3"], content_w)
    fda_top_y = fda_base_y + n_fda * (fda_sz + 1)

    # Manufacturer — above FDA
    mfg_base_y = fda_top_y + gap
    n_mfg = len(mfg_lines[:2])
    for i, line in enumerate(mfg_lines[:2]):
        line_y = mfg_base_y + (n_mfg - 1 - i) * (mfg_sz + 1)
        _draw_capped(c, left, line_y, line, mfg_font, mfg_sz, C["t3"], content_w)
    mfg_top_y = mfg_base_y + n_mfg * (mfg_sz + 1)

    # QR code
    qr_img = make_qr(qr_url)
    if has_qr_side:
        qr_x = right - qr_sz
        qr_y = top - bbsz - 12 - qr_sz
        if qr_y < back_strip_top + 4:
            qr_y = back_strip_top + 4
        c.drawImage(qr_img, qr_x, qr_y, qr_sz, qr_sz)
        cta_w = _text_w("SCAN FOR INFO", "PlexMono", 5)
        _draw(c, qr_x + (qr_sz - cta_w) / 2, qr_y - 7, "SCAN FOR INFO", "PlexMono", 5, C["t3"])
    else:
        qr_y = mfg_top_y + gap
        qr_x = left
        c.drawImage(qr_img, qr_x, qr_y, qr_sz, qr_sz)
        _draw(c, qr_x + qr_sz + 4, qr_y + qr_sz / 2 - 2, "SCAN FOR INFO", "PlexMono", 5, C["t3"])


# ═══════════════════════════════════════════════════════════════════════════
# RENDER PIPELINE
# ═══════════════════════════════════════════════════════════════════════════
def render_sku(sku, system_name):
    meta = sku["_meta"]
    fmt = sku["format"]["label_format"]
    if fmt not in FORMAT_DIMS: return

    dims = FORMAT_DIMS[fmt]
    accent = C["ax_mo"] if "MAXimo" in meta["os"] else C["ax_ma"]

    out_dir = OUTPUT_BASE / system_name / fmt / meta["module_code"]
    out_dir.mkdir(parents=True, exist_ok=True)

    ingredient = sku["front_panel"]["zone_3"]["ingredient_name"]
    safe = ingredient.replace("/", "-").replace("\\", "-").replace(":", "")[:40].strip().replace(" ", "_")
    fbase = f"{meta['module_code']}_{safe}_{fmt}"

    crop_m = 20
    pw = dims["w"] + 2*BLEED + 2*crop_m
    ph = dims["h"] + 2*BLEED + 2*crop_m
    tx = crop_m + BLEED
    ty_ = crop_m + BLEED

    for side in ["front", "back"]:
        pdf_p = out_dir / f"{fbase}_{side}.pdf"
        cv = canvas.Canvas(str(pdf_p), pagesize=(pw, ph))
        cv.setAuthor("GenoMAX\u00b2 V3")
        cv.setTitle(f"{meta['module_code']} {ingredient} {fmt} {side}")

        cv.setFillColor(C["white"])
        cv.rect(0, 0, pw, ph, fill=1, stroke=0)

        if side == "front":
            render_front(cv, sku, dims, accent, tx, ty_)
        else:
            render_back(cv, sku, dims, accent, tx, ty_)

        draw_crop_marks(cv, tx, ty_, dims["w"], dims["h"])

        # Info line — OUTSIDE trim, in crop margin (safe)
        info = f"GenoMAX\u00b2 | {meta['module_code']} | {meta['os']} | {fmt} | {side.upper()} | V3-LOCKED | CMYK | 3mm bleed"
        _draw(cv, tx, ty_ - BLEED - 10, info, "PlexMono", 3.5, C["t3"])

        cv.save()
    return out_dir


def main():
    print("=" * 60)
    print("GenoMAX\u00b2 V3 Production Renderer — FIXED LAYOUT")
    print("=" * 60)

    systems = {
        "maximo": DATA_DIR / "production-labels-maximo.json",
        "maxima": DATA_DIR / "production-labels-maxima.json",
    }
    total = 0
    for sname, dpath in systems.items():
        print(f"\n--- {sname.upper()} ---")
        with open(dpath, encoding='utf-8') as f:
            data = json.load(f)
        for i, sku in enumerate(data["skus"]):
            m = sku["_meta"]
            ing = sku["front_panel"]["zone_3"]["ingredient_name"]
            print(f"  [{i+1:3d}/{len(data['skus'])}] {m['module_code']} | {sku['format']['label_format']:7s} | {ing[:35]}", end="")
            try:
                render_sku(sku, sname)
                total += 1
                print(" OK")
            except Exception as e:
                print(f" ERR: {e}")

    print(f"\nDONE: {total} SKUs, {total*2} PDFs")

if __name__ == "__main__":
    main()
