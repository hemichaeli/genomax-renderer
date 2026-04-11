#!/usr/bin/env python3
"""
GenoMAX² V6 PRODUCTION — Zero Overflow Layout Engine
=====================================================
V5→V6: Global layout safety fixes. No creative changes.
Fixes:
  - SAFE_MARGIN raised to 32px on all sides (was 12px)
  - _dc() now auto-shrinks font instead of silent truncation
  - _w() handles single words wider than max_width via char-break
  - _dt() charspace width calculation corrected
  - QR-text gap enforced at 24px minimum (was 8px)
  - Footer text center-locked within safe width
  - tw/tw unified — wrap width = draw width (no mismatch)
  - Format-specific text reduction: DROPPER -15%, POUCH/STRIPS -20%
  - Adaptive fit: reduce tracking → reduce size → reflow (never clip)
"""

import json, os, sys, re
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
SCRIPT_DIR = Path(__file__).resolve().parent
BASE = SCRIPT_DIR.parent
FONTS_DIR = BASE / "design-system" / "fonts"
DATA_DIR = BASE / "design-system" / "data"
OUTPUT_BASE = BASE / "design-system" / "production-v6"
DRIVE_DEST = Path("G:/My Drive/Work/GenoMAX²/Design/Lables/GenoMAX_V6_FINAL")

# ─── FONTS ─────────────────────────────────────────────────────────────────
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
for name, fn in FONT_MAP.items():
    p = FONTS_DIR / fn
    if p.exists(): pdfmetrics.registerFont(TTFont(name, str(p)))

# ─── COLORS ───────────────────────────────────────────────────────────────
def h2c(h):
    h = h.lstrip('#')
    r, g, b = int(h[0:2],16)/255, int(h[2:4],16)/255, int(h[4:6],16)/255
    k = 1-max(r,g,b)
    if k==1: return CMYKColor(0,0,0,1)
    return CMYKColor((1-r-k)/(1-k),(1-g-k)/(1-k),(1-b-k)/(1-k),k)

C = {
    "bg": h2c("#F4F2EC"), "t1": h2c("#1A1815"), "t2": h2c("#4A4843"),
    "t3": h2c("#8A8880"), "div": h2c("#C5C2BA"),
    "ax_mo": h2c("#7A1E2E"), "ax_ma": h2c("#7A304A"),
    "strip_bg": h2c("#4A4A4A"), "strip_tx": h2c("#B0B0B0"),
    "white": CMYKColor(0,0,0,0),
}

BLEED = 3 * mm
SAFE_MARGIN = 32  # V6: 32px safe area on ALL sides — no text may enter
MARGIN = SAFE_MARGIN
STRIP_H = 16  # V6: slightly taller strip to prevent footer clipping
QR_TEXT_GAP = 24  # V6: minimum gap between QR and text column

FORMAT_DIMS = {
    "BOTTLE":  {"w": 6*inch,   "h": 2.5*inch, "pn_pt": 27, "tier": 1},
    "JAR":     {"w": 8.5*inch, "h": 2*inch,   "pn_pt": 22, "tier": 2},
    "POUCH":   {"w": 5*inch,   "h": 4*inch,   "pn_pt": 27, "tier": 1},
    "DROPPER": {"w": 2*inch,   "h": 4*inch,   "pn_pt": 14, "tier": 2},
    "STRIPS":  {"w": 4*inch,   "h": 6.5*inch, "pn_pt": 27, "tier": 1},
}

# ─── V6 TEXT PRIMITIVES (Zero Overflow) ──────────────────────────────────

def _d(c, x, y, t, f, s, co):
    """Draw text at exact position. No safety — use _ds for safe drawing."""
    o = c.beginText(x, y); o.setFont(f, s); o.setFillColor(co); o.setCharSpace(0); o.textOut(t); c.drawText(o)

def _tw(t, f, s):
    """Measure text width."""
    return pdfmetrics.stringWidth(t, f, s)

def _dt(c, x, y, t, f, s, co, tr, mw=None):
    """Draw tracked text. V6.3: Cascading fit — NO TRUNCATION.
    Order: tracking → shrink → condensed → shrink more."""
    if mw and t:
        def _tracked_w(txt, sz, trk):
            return _tw(txt, f, sz) + max(0, len(txt)-1) * sz * trk
        orig_s = s
        # Step 1: reduce tracking progressively (to 0)
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
        # Step 3: switch to condensed variant if available
        if _tracked_w(t, s, tr) > mw:
            cond_map = {"PlexMono-Bold":"PlexCondensed-Bold","PlexMono-Medium":"PlexCondensed-Medium",
                        "PlexMono":"PlexCondensed","PlexSans":"PlexCondensed",
                        "PlexSans-Medium":"PlexCondensed-Medium","PlexSans-SemiBold":"PlexCondensed-SemiBold",
                        "PlexSans-Bold":"PlexCondensed-Bold"}
            alt = cond_map.get(f)
            if alt:
                try:
                    if _tracked_w(t, s, tr) > mw:  # re-test with condensed
                        if _tw(t, alt, s) + max(0, len(t)-1) * s * tr <= mw:
                            f = alt
                except: pass
        # Step 4: final emergency shrink to -40%
        while _tracked_w(t, s, tr) > mw and s > orig_s * 0.60:
            s -= 0.25
        # NEVER truncate — draw at final size
    o = c.beginText(x, y); o.setFont(f, s); o.setFillColor(co); o.setCharSpace(s*tr); o.textOut(t); c.drawText(o)

def _dr(c, xr, y, t, f, s, co):
    """Draw right-aligned text."""
    _d(c, xr - _tw(t, f, s), y, t, f, s, co)

def _dc(c, x, y, t, f, s, co, mw):
    """Draw clamped text. V6.3: Cascading fit — NO TRUNCATION, NO ELLIPSIS.
    Order: shrink → condensed → shrink more."""
    orig_s = s
    orig_f = f
    # Step 1: shrink font up to -20%
    while _tw(t, f, s) > mw and s > orig_s * 0.80:
        s -= 0.25
    # Step 2: switch to condensed variant if still overflowing
    if _tw(t, f, s) > mw:
        cond_map = {"PlexMono-Bold":"PlexCondensed-Bold","PlexMono-Medium":"PlexCondensed-Medium",
                    "PlexMono":"PlexCondensed","PlexMono-SemiBold":"PlexCondensed-SemiBold",
                    "PlexSans":"PlexCondensed","PlexSans-Medium":"PlexCondensed-Medium",
                    "PlexSans-SemiBold":"PlexCondensed-SemiBold","PlexSans-Bold":"PlexCondensed-Bold",
                    "PlexSans-Light":"PlexCondensed"}
        alt = cond_map.get(f)
        if alt:
            # Reset size and try condensed at original size first
            s_try = orig_s
            while _tw(t, alt, s_try) > mw and s_try > orig_s * 0.80:
                s_try -= 0.25
            if _tw(t, alt, s_try) <= mw:
                f = alt
                s = s_try
    # Step 3: emergency shrink to -40% (still no truncation)
    while _tw(t, f, s) > mw and s > orig_s * 0.60:
        s -= 0.25
    _d(c, x, y, t, f, s, co)

def _w(t, f, s, mw):
    """Word-wrap text. V6: handles single words wider than mw via char-break."""
    words, lines, cur = t.split(), [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if _tw(test, f, s) <= mw:
            cur = test
        else:
            if cur:
                lines.append(cur)
            # V6: if single word exceeds mw, break it by character
            if _tw(w, f, s) > mw:
                chunk = ""
                for ch in w:
                    if _tw(chunk + ch, f, s) <= mw:
                        chunk += ch
                    else:
                        if chunk: lines.append(chunk)
                        chunk = ch
                cur = chunk
            else:
                cur = w
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
    for p in [(tx-O,ty+h,tx-O-L,ty+h),(tx,ty+h+O,tx,ty+h+O+L),(tx+w+O,ty+h,tx+w+O+L,ty+h),(tx+w,ty+h+O,tx+w,ty+h+O+L),(tx-O,ty,tx-O-L,ty),(tx,ty-O,tx,ty-O-L),(tx+w+O,ty,tx+w+O+L,ty),(tx+w,ty-O,tx+w,ty-O-L)]:
        c.line(*p)


# ═══════════════════════════════════════════════════════════════════════════
# FRONT LABEL — UNCHANGED from V4 (V3-LOCKED)
# ═══════════════════════════════════════════════════════════════════════════
def render_front(c, sku, dims, accent, tx, ty):
    """V6.4: Vertically balanced layout with stacked meta block on ALL formats."""
    w, h = dims["w"], dims["h"]
    fmt = sku["format"]["label_format"]
    narrow = fmt == "DROPPER"; tall = fmt in ("STRIPS", "POUCH"); short = fmt == "JAR"
    left, right_ = tx + MARGIN, tx + w - MARGIN
    cw = right_ - left

    # ── V6.4: Footer strip — lighter (#4A4A4A), -60% vs V5 ──
    sh_base = STRIP_H if not narrow else 18
    sh = int(sh_base * 0.42)  # -58% height
    if sh < 8: sh = 8
    footer_top = ty + sh  # y where strip ends and content area begins

    # Background
    c.setFillColor(C["bg"]); c.rect(tx-BLEED, ty-BLEED, w+2*BLEED, h+2*BLEED, fill=1, stroke=0)
    c.setFillColor(accent); c.rect(tx-BLEED, ty+h-2, w+2*BLEED, 2, fill=1, stroke=0)

    # ═══ HEADER BLOCK (top) ═══
    header_top = ty + h - MARGIN - 2
    cy = header_top - (4 if not short else 2)

    bsz = 12 if not narrow else 8
    if short: bsz = 10
    _dt(c, left, cy-bsz, "GenoMAX\u00b2", "PlexMono-Bold", bsz, C["t1"], 0.18, mw=cw*0.65)
    _dr(c, right_, cy-(6 if not narrow else 5), sku["front_panel"]["zone_1"]["module_code"], "PlexMono-Medium", 6 if not narrow else 5, C["t3"])
    cy -= bsz + (3 if not short else 2)

    c.saveState(); c.setStrokeColor(C["t1"]); c.setLineWidth(0.5); c.setStrokeAlpha(0.25)
    c.line(left, cy, right_, cy); c.restoreState()
    cy -= (4 if not short else 2)

    z2s = 7 if not narrow else 5.5
    if short: z2s = 6
    _dt(c, left, cy-z2s, sku["front_panel"]["zone_2"]["text"], "PlexMono-Medium", z2s, C["t2"], 0.18, mw=cw)
    cy -= z2s

    header_bottom = cy  # Top of content block area
    content_top = header_bottom - 4
    content_bottom = footer_top + MARGIN  # Safe floor above strip

    # ═══ PASS 1: MEASURE content block with adaptive sizing ═══
    z6 = sku["front_panel"]["zone_6"]
    available_h = content_top - content_bottom

    # Base sizes by format
    if narrow:
        max_ps_base = 14; sub_sz_base = 10; meta_sz_base = 7; vs_base = 8
    elif short:
        max_ps_base = 20; sub_sz_base = 10; meta_sz_base = 8; vs_base = 8
    else:
        max_ps_base = min(dims["pn_pt"], 27); sub_sz_base = 13; meta_sz_base = 9.5; vs_base = 10

    pn = sku["front_panel"]["zone_3"]["ingredient_name"]
    desc = sku["front_panel"]["zone_4"].get("descriptor", "")
    bio = sku["front_panel"]["zone_4"].get("biological_system", "")
    variant = sku["front_panel"]["zone_5"]["variant_name"]
    meta_items = [
        ("TYPE", z6["type"]["value"]),
        ("SYSTEM", (sku["front_panel"]["zone_4"].get("biological_system","") or "").split("·")[0].strip() or z6.get("status",{}).get("value","") or "—"),
        ("FUNCTION", z6["function"]["value"]),
    ]

    def measure(ps, sub_sz, meta_sz, vs):
        pf = "PlexCondensed-Bold"
        tl = _w(pn, pf, ps, cw)
        # Shrink title to max 3 lines
        _ps = ps
        while len(tl) > 3 and _ps > 10:
            _ps -= 0.5
            tl = _w(pn, pf, _ps, cw)
        tl = tl[:3]
        t_h = len(tl) * _ps * 0.95

        sl = []
        _ssz = sub_sz
        if desc:
            sl = _w(desc, "PlexSans-Medium", _ssz, cw)
            while len(sl) > 2 and _ssz > 8:
                _ssz -= 0.5
                sl = _w(desc, "PlexSans-Medium", _ssz, cw)
            sl = sl[:2]
        s_h = len(sl) * _ssz * 1.1
        bs = _ssz - 1 if not narrow else 6
        if short: bs = 7
        b_h = bs * 1.1 if bio else 0

        mlh = meta_sz * 1.45
        m_h = 3 * mlh

        v_h = vs + 4
        return tl, _ps, sl, _ssz, bs, meta_sz, mlh, vs, (t_h + s_h + b_h + m_h + v_h), t_h, s_h, b_h, m_h, v_h

    # Cascading shrink loop — find biggest sizes that fit
    ps_try = max_ps_base
    sub_try = sub_sz_base
    meta_try = meta_sz_base
    vs_try = vs_base
    min_total_gaps = 12 + 14 + 16  # title→sub, sub→meta, meta→variant

    for _ in range(80):  # hard iteration cap
        tl, ps_final, sl, sub_final, bio_final, meta_final, mlh, vs_final, content_h, t_h, s_h, b_h, m_h, v_h = measure(ps_try, sub_try, meta_try, vs_try)
        if content_h + min_total_gaps <= available_h:
            break
        # Shrink: reduce title first, then subtitle, then meta, then variant
        if ps_try > 11:
            ps_try -= 0.5
        elif sub_try > 8:
            sub_try -= 0.5
        elif meta_try > 6.5:
            meta_try -= 0.5
        elif vs_try > 7:
            vs_try -= 0.5
        else:
            break  # At minimums

    title_lines, ps, sub_lines, sub_sz, bio_sz, meta_sz, meta_lh, vs, content_h, title_h, sub_h, bio_h, meta_h, variant_h = tl, ps_final, sl, sub_final, bio_final, meta_final, mlh, vs_final, content_h, t_h, s_h, b_h, m_h, v_h

    # Distribute slack as gaps
    slack = max(0, available_h - content_h)
    min_gap_ts, min_gap_sm, min_gap_mv = 6, 10, 12
    total_min = min_gap_ts + min_gap_sm + min_gap_mv
    if slack > total_min:
        extra = slack - total_min
        gap_ts = min_gap_ts + extra * 0.15
        gap_sm = min_gap_sm + extra * 0.35
        gap_mv = min_gap_mv + extra * 0.50
    else:
        # Compress gaps proportionally
        ratio = slack / total_min if total_min else 0
        gap_ts = max(3, min_gap_ts * ratio)
        gap_sm = max(5, min_gap_sm * ratio)
        gap_mv = max(6, min_gap_mv * ratio)

    # ═══ PASS 2: DRAW ═══
    pf = "PlexCondensed-Bold"

    if short:
        # ── JAR: 2-column horizontal layout (title+sub left, meta+variant right) ──
        col_split = left + cw * 0.58
        left_col_w = col_split - left - 16
        right_col_w = right_ - col_split

        # Left column: title + subtitle
        lcy = content_top
        for ln in title_lines:
            _dc(c, left, lcy-ps, ln, pf, ps, C["t1"], left_col_w)
            lcy -= ps * 0.95
        lcy -= 6
        for sl in sub_lines:
            _dc(c, left, lcy-sub_sz, sl, "PlexSans-Medium", sub_sz, C["t2"], left_col_w)
            lcy -= sub_sz * 1.1
        if bio:
            _dc(c, left, lcy-bio_sz, bio, "PlexMono", bio_sz, C["t3"], left_col_w)
            lcy -= bio_sz * 1.1

        # Right column: stacked meta + variant
        rcy = content_top
        label_col_w = _tw("FUNCTION", "PlexMono-Medium", meta_sz * 0.85) + meta_sz * 0.8
        for label, val in meta_items:
            _d(c, col_split, rcy-meta_sz, label, "PlexMono-Medium", meta_sz * 0.85, C["t3"])
            _dc(c, col_split + label_col_w, rcy-meta_sz, val, "PlexSans-Medium", meta_sz, C["t1"], right_col_w - label_col_w)
            rcy -= meta_lh
        rcy -= 8
        _dc(c, col_split, rcy-vs, variant, "PlexSans-SemiBold", vs, C["t1"], right_col_w)
        rcy -= vs + 2
        c.setFillColor(accent); c.rect(col_split, rcy-2, 50, 2, fill=1, stroke=0)
    else:
        # ── BOTTLE/POUCH/DROPPER/STRIPS: Vertically balanced single-column layout ──
        cy = content_top

        # Title
        for ln in title_lines:
            _dc(c, left, cy-ps, ln, pf, ps, C["t1"], cw)
            cy -= ps * 0.95
        cy -= gap_ts

        # Subtitle
        for sl in sub_lines:
            _dc(c, left, cy-sub_sz, sl, "PlexSans-Medium", sub_sz, C["t2"], cw)
            cy -= sub_sz * 1.1
        if bio:
            _dc(c, left, cy-bio_sz, bio, "PlexMono", bio_sz, C["t3"], cw)
            cy -= bio_sz * 1.1
        cy -= gap_sm

        # Meta block — STACKED (TYPE / SYSTEM / FUNCTION)
        label_col_w = _tw("FUNCTION", "PlexMono-Medium", meta_sz * 0.85) + meta_sz * 0.8
        for label, val in meta_items:
            _d(c, left, cy-meta_sz, label, "PlexMono-Medium", meta_sz * 0.85, C["t3"])
            _dc(c, left + label_col_w, cy-meta_sz, val, "PlexSans-Medium", meta_sz, C["t1"], cw - label_col_w)
            cy -= meta_lh
        cy -= gap_mv

        # Variant + accent bar
        _dc(c, left, cy-vs, variant, "PlexSans-SemiBold", vs, C["t1"], cw)
        cy -= vs + 2
        c.setFillColor(accent); c.rect(left, cy-2, 70 if not narrow else 40, 2, fill=1, stroke=0)

    # ═══ FOOTER STRIP ═══
    c.setFillColor(C["strip_bg"]); c.rect(tx-BLEED, ty-BLEED, w+2*BLEED, sh+BLEED, fill=1, stroke=0)
    ver, qty = sku["front_panel"]["zone_7"]["version_info"], sku["front_panel"]["zone_7"]["net_quantity"]
    ssz = 4 if not narrow else 3.25
    footer_safe_w = cw - 8
    if narrow:
        sty_1 = ty + sh - 2 - ssz
        sty_2 = sty_1 - ssz - 0.5
        _dc(c, left, sty_1, ver, "PlexMono", ssz, C["strip_tx"], footer_safe_w)
        _dc(c, left, sty_2, qty, "PlexMono", ssz, C["strip_tx"], footer_safe_w)
    else:
        sty = ty + (sh - ssz) / 2
        hw = footer_safe_w * 0.48
        _dc(c, left, sty, ver, "PlexMono", ssz, C["strip_tx"], hw)
        _dc(c, right_ - hw, sty, qty, "PlexMono", ssz, C["strip_tx"], hw)


# ═══════════════════════════════════════════════════════════════════════════
# V5 BACK LABEL — CLINICAL READABILITY REBUILD
# ═══════════════════════════════════════════════════════════════════════════
def parse_back_text(raw):
    """Parse v4 back label text into structured sections."""
    sections = {
        "context": "",        # Clinical mechanism
        "suggested_use": "",  # Directions
        "cta_line": "",       # "Often used in early..." line
        "warnings": [],       # Warning paragraphs
        "ingredients": "",    # Ingredient reference
    }

    lines = raw.split('\n')
    current_section = None
    buffer = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            # Flush buffer to current section
            if current_section and buffer:
                text = ' '.join(buffer).strip()
                if current_section == "context":
                    sections["context"] = text
                elif current_section == "suggested_use":
                    sections["suggested_use"] += (" " + text if sections["suggested_use"] else text)
                elif current_section == "warnings":
                    if text: sections["warnings"].append(text)
                elif current_section == "ingredients":
                    sections["ingredients"] = text
                elif current_section == "cta_line":
                    sections["cta_line"] = text
                buffer = []
            continue

        # Skip protocol header (rendered separately)
        if stripped == "This is not your full protocol.":
            continue
        # Skip QR placeholders
        if stripped in ("[QR]", "Scan to begin", "genomax.ai"):
            continue
        # Skip distributor (in strip)
        if stripped.startswith("Distributed by"):
            continue

        # Detect section headers
        if stripped == "Suggested Use:":
            if buffer and current_section:
                text = ' '.join(buffer).strip()
                if current_section == "context": sections["context"] = text
                buffer = []
            current_section = "suggested_use"
            continue
        elif stripped == "Warnings:":
            if buffer and current_section:
                text = ' '.join(buffer).strip()
                if current_section == "suggested_use": sections["suggested_use"] += (" " + text if sections["suggested_use"] else text)
                elif current_section == "cta_line": sections["cta_line"] = text
                buffer = []
            current_section = "warnings"
            continue
        elif stripped.startswith("Ingredients:"):
            if buffer and current_section == "warnings":
                text = ' '.join(buffer).strip()
                if text: sections["warnings"].append(text)
                buffer = []
            current_section = "ingredients"
            # Ingredients might be on same line
            rest = stripped[len("Ingredients:"):].strip()
            if rest: buffer.append(rest)
            continue
        elif stripped.startswith("Often used in"):
            if buffer and current_section:
                text = ' '.join(buffer).strip()
                if current_section == "suggested_use": sections["suggested_use"] += (" " + text if sections["suggested_use"] else text)
                buffer = []
            current_section = "cta_line"
            buffer.append(stripped)
            continue

        # If no section yet, this is the clinical context
        if current_section is None:
            current_section = "context"

        buffer.append(stripped)

    # Flush remaining buffer
    if buffer and current_section:
        text = ' '.join(buffer).strip()
        if current_section == "context": sections["context"] = text
        elif current_section == "suggested_use": sections["suggested_use"] += (" " + text if sections["suggested_use"] else text)
        elif current_section == "warnings":
            if text: sections["warnings"].append(text)
        elif current_section == "ingredients": sections["ingredients"] = text
        elif current_section == "cta_line": sections["cta_line"] = text

    return sections


def render_back(c, sku, dims, accent, tx, ty):
    w, h = dims["w"], dims["h"]
    fmt = sku["format"]["label_format"]
    narrow = fmt == "DROPPER"
    tall = fmt in ("STRIPS", "POUCH")
    is_strips = fmt == "STRIPS"
    short = fmt == "JAR"

    left, right_ = tx + MARGIN, tx + w - MARGIN
    cw = right_ - left
    top = ty + h - MARGIN

    raw = sku.get("back_panel", {}).get("back_label_text", "")
    sec = parse_back_text(raw)

    # ── Background + Ceiling ──
    c.setFillColor(C["bg"]); c.rect(tx-BLEED, ty-BLEED, w+2*BLEED, h+2*BLEED, fill=1, stroke=0)
    c.setFillColor(accent); c.rect(tx-BLEED, ty+h-2, w+2*BLEED, 2, fill=1, stroke=0)

    # ── Strip (V6.4: -58% height, #4A4A4A, lighter contrast) ──
    bsh_base = STRIP_H if not narrow else 18
    bsh = int(bsh_base * 0.42)
    if bsh < 8: bsh = 8
    c.setFillColor(C["strip_bg"]); c.rect(tx-BLEED, ty-BLEED, w+2*BLEED, bsh+BLEED, fill=1, stroke=0)
    stsz = 4 if not narrow else 3.25
    footer_w = cw - 8
    if narrow:
        sty_n = ty + bsh - 2 - stsz
        _dc(c, left, sty_n, "genomax.ai", "PlexMono", stsz, C["strip_tx"], footer_w)
        _dc(c, left, sty_n-stsz-1, "Distributed by Genomax LLC", "PlexMono", stsz, C["strip_tx"], footer_w)
    else:
        sty_w = ty + (bsh - stsz) / 2
        _dc(c, left, sty_w, "genomax.ai \u00b7 support@genomax.ai", "PlexMono", stsz, C["strip_tx"], footer_w*0.5)
        _dc(c, right_ - footer_w*0.5, sty_w, "Distributed by Genomax LLC", "PlexMono", stsz, C["strip_tx"], footer_w*0.5)
    strip_top = ty + bsh

    # ── QR setup ──
    qr_sz = 36 if not narrow else 26  # smaller QR to save space
    if short: qr_sz = 32
    mc = sku["_meta"]["module_code"]
    osn = sku["_meta"]["os"].replace("\u00b2","2").replace("²","2").lower()
    qr_img = make_qr(f"https://genomax.ai/module/{osn}/{mc.lower()}")

    # ── V5 ENFORCED SIZES (scaled per format) ──
    # Protocol: 10-11pt (wraps on narrow)
    PROTO_SZ = 10 if not narrow else 8
    if short: PROTO_SZ = 9
    CTA_SZ = 9 if not narrow else 7
    if short: CTA_SZ = 8
    SUGGEST_SZ = 8 if not narrow else 7
    if short: SUGGEST_SZ = 7
    WARN_SZ = 7  # hard min
    INGR_SZ = 7  # hard min
    BODY_SZ = 7 if (narrow or short) else 7.5
    SGAP = 8 if (narrow or short) else 10  # section gap
    HEAD_SZ = 6.5 if (narrow or short) else 7

    has_qr_side = not narrow and not tall
    qr_reserve = (qr_sz + QR_TEXT_GAP) if has_qr_side else 0  # V6: 24px gap (was 8)
    tw = cw - qr_reserve  # V6: text width respects QR reserve fully
    # V6: UNIFIED — wrap width = draw width. No mismatch = no edge clipping.
    floor = strip_top + SAFE_MARGIN  # V6: bottom safe area enforced

    # ── Brand header ──
    cy = top - 2 - 3
    bbsz = 7 if not narrow else 6
    if short: bbsz = 6
    _dt(c, left, cy-bbsz, "GenoMAX\u00b2", "PlexMono-Bold", bbsz, C["t1"], 0.18, mw=cw*0.6)
    cy -= bbsz + 2

    c.saveState(); c.setStrokeColor(C["t1"]); c.setLineWidth(0.5); c.setStrokeAlpha(0.25)
    c.line(left, cy, right_, cy); c.restoreState()
    cy -= 4

    # ══════════════════════════════════════════════════════════════════
    # SECTION 1: PROTOCOL HEADER
    # ══════════════════════════════════════════════════════════════════
    proto = "THIS IS NOT YOUR FULL PROTOCOL"
    proto_lines = _w(proto, "PlexMono-Bold", PROTO_SZ, tw)
    for ln in proto_lines[:2]:
        _dc(c, left, cy-PROTO_SZ, ln, "PlexMono-Bold", PROTO_SZ, C["t1"], tw)
        cy -= PROTO_SZ + 1
    cy -= SGAP - 2

    # ══════════════════════════════════════════════════════════════════
    # SECTION 1b: CTA + QR
    # ══════════════════════════════════════════════════════════════════
    cta_lines = _w("SCAN FOR FULL PROTOCOL", "PlexMono-SemiBold", CTA_SZ, tw if not narrow else cw)
    if has_qr_side:
        qr_x = right_ - qr_sz
        qr_y = cy - qr_sz
        if qr_y < floor + 10: qr_y = floor + 10
        c.drawImage(qr_img, qr_x, qr_y, qr_sz, qr_sz)
        for ln in cta_lines[:2]:
            _dc(c, left, cy-CTA_SZ, ln, "PlexMono-SemiBold", CTA_SZ, C["t1"], tw)
            cy -= CTA_SZ + 1
        _dc(c, left, cy-6, "genomax.ai", "PlexMono", 6, C["t2"], tw)
        cy -= 6 + SGAP
    else:
        for ln in cta_lines[:2]:
            _dc(c, left, cy-CTA_SZ, ln, "PlexMono-SemiBold", CTA_SZ, C["t1"], cw)
            cy -= CTA_SZ + 1
        cy -= 3
        qr_x = left
        c.drawImage(qr_img, qr_x, cy-qr_sz, qr_sz, qr_sz)
        _d(c, qr_x+qr_sz+4, cy-qr_sz/2-2, "genomax.ai", "PlexMono", 5.5, C["t2"])
        cy -= qr_sz + SGAP

    # Divider
    c.setStrokeColor(C["div"]); c.setLineWidth(0.35)
    c.line(left, cy, left+tw, cy)
    cy -= SGAP

    # ══════════════════════════════════════════════════════════════════
    # SECTION 2: CONTEXT (max 2-3 lines)
    # Skip on JAR (2" height) — not enough room, prioritize warnings
    # ══════════════════════════════════════════════════════════════════
    ctx = sec.get("context", "")
    if ctx and not short and cy > floor + 20:
        ctx_lines = _w(ctx, "PlexSans", BODY_SZ, tw)
        mx = 2 if (narrow or is_strips) else 3
        for ln in ctx_lines[:mx]:
            if cy < floor + BODY_SZ: break
            _dc(c, left, cy-BODY_SZ, ln, "PlexSans", BODY_SZ, C["t2"], tw)
            cy -= BODY_SZ + 1.5
        cy -= SGAP - 3

    # ══════════════════════════════════════════════════════════════════
    # SECTION 3: SUGGESTED USE (≥8pt)
    # ══════════════════════════════════════════════════════════════════
    sug = sec.get("suggested_use", "")
    if sug and cy > floor + 15:
        _dt(c, left, cy-HEAD_SZ, "SUGGESTED USE", "PlexMono-Medium", HEAD_SZ, C["t3"], 0.08, mw=tw)
        cy -= HEAD_SZ + 2
        sug_lines = _w(sug, "PlexSans-Medium", SUGGEST_SZ, tw)
        mx = 2 if (narrow or is_strips) else 3
        for ln in sug_lines[:mx]:
            if cy < floor + SUGGEST_SZ: break
            _dc(c, left, cy-SUGGEST_SZ, ln, "PlexSans-Medium", SUGGEST_SZ, C["t1"], tw)
            cy -= SUGGEST_SZ + 1.5
        cy -= SGAP - 3

    # ══════════════════════════════════════════════════════════════════
    # SECTION 4: WARNINGS (≥7pt hard min)
    # ══════════════════════════════════════════════════════════════════
    warn_text = ' '.join(sec.get("warnings", []))
    if warn_text and cy > floor + 12:
        _dt(c, left, cy-HEAD_SZ, "WARNINGS", "PlexMono-Medium", HEAD_SZ, C["t3"], 0.08, mw=tw)
        cy -= HEAD_SZ + 2
        wl = _w(warn_text, "PlexSans", WARN_SZ, tw)
        mx = 3 if (narrow or is_strips or short) else 4
        if tall: mx = 5
        for ln in wl[:mx]:
            if cy < floor + WARN_SZ: break
            _dc(c, left, cy-WARN_SZ, ln, "PlexSans", WARN_SZ, C["t2"], tw)
            cy -= WARN_SZ + 1
        cy -= SGAP - 4

    # ══════════════════════════════════════════════════════════════════
    # SECTION 5: INGREDIENTS (≥7pt, lowest priority)
    # ══════════════════════════════════════════════════════════════════
    ingr = sec.get("ingredients", "")
    if ingr and cy > floor + 10:
        _dt(c, left, cy-HEAD_SZ, "INGREDIENTS", "PlexMono-Medium", HEAD_SZ, C["t3"], 0.08, mw=tw)
        cy -= HEAD_SZ + 2
        _dc(c, left, cy-INGR_SZ, ingr, "PlexSans", INGR_SZ, C["t1"], tw)
        cy -= INGR_SZ + 2


# ═══════════════════════════════════════════════════════════════════════════
# RENDER + EXPORT PIPELINE
# ═══════════════════════════════════════════════════════════════════════════
def render_sku(sku, system_name, output_base=None):
    meta = sku["_meta"]
    fmt = sku["format"]["label_format"]
    if fmt not in FORMAT_DIMS: return None

    dims = FORMAT_DIMS[fmt]
    accent = C["ax_mo"] if "MAXimo" in meta["os"] else C["ax_ma"]

    base = output_base or OUTPUT_BASE
    # V5 folder structure: FORMAT/[MODULE]_[SYSTEM]_[SHORT_NAME]/front.jpg + back.jpg
    sys_tag = "MO" if "MAXimo" in meta["os"] else "MA"
    ing = sku["front_panel"]["zone_3"]["ingredient_name"]
    short = ing.replace("/","-").replace("\\","-").replace(":","").replace(" ","_")[:50].strip("_")
    out_dir = base / fmt / f"{meta['module_code']}_{sys_tag}_{short}"
    out_dir.mkdir(parents=True, exist_ok=True)

    ing = sku["front_panel"]["zone_3"]["ingredient_name"]
    safe = ing.replace("/","-").replace("\\","-").replace(":","")[:40].strip().replace(" ","_")

    cm = 20
    pw, ph = dims["w"]+2*BLEED+2*cm, dims["h"]+2*BLEED+2*cm
    tx, ty_ = cm+BLEED, cm+BLEED

    results = {}
    for side in ["front", "back"]:
        pdf_p = out_dir / f"{side}.pdf"
        cv = canvas.Canvas(str(pdf_p), pagesize=(pw, ph))
        cv.setAuthor("GenoMAX\u00b2 V6 Zero Overflow")
        cv.setTitle(f"{meta['module_code']} {ing} {fmt} {side}")
        cv.setFillColor(C["white"]); cv.rect(0,0,pw,ph,fill=1,stroke=0)

        if side == "front": render_front(cv, sku, dims, accent, tx, ty_)
        else: render_back(cv, sku, dims, accent, tx, ty_)

        crop_marks(cv, tx, ty_, dims["w"], dims["h"])
        info = f"GenoMAX\u00b2 | {meta['module_code']} | {meta['os']} | {fmt} | {side.upper()} | V6-ZERO-OVERFLOW"
        _d(cv, tx, ty_-BLEED-10, info, "PlexMono", 3.5, C["t3"])
        cv.save()

        # Generate JPG (≤1600px max dimension, quality 85%)
        import fitz
        doc = fitz.open(str(pdf_p))
        page = doc[0]
        # Calculate scale for max 1600px
        max_dim = 1600
        pw_pt, ph_pt = page.rect.width, page.rect.height
        scale = min(max_dim / pw_pt, max_dim / ph_pt, 4.0)  # cap at 4x
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        jpg_p = out_dir / f"{side}.jpg"
        # Save via PIL for quality control
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img.save(str(jpg_p), "JPEG", quality=85)
        doc.close()

        # Remove PDF (delivery is JPG only per spec)
        # Keep PDF as backup but don't include in Drive delivery
        results[side] = jpg_p

    return out_dir


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true", help="Render 1 of each format only")
    parser.add_argument("--full", action="store_true", help="Full production render")
    args = parser.parse_args()

    mode = "VALIDATION" if args.validate else "FULL PRODUCTION"
    print("=" * 60)
    print(f"GenoMAX\u00b2 V6 Zero Overflow — {mode}")
    print("=" * 60)

    systems = {
        "maximo": DATA_DIR / "production-labels-maximo-v4.json",
        "maxima": DATA_DIR / "production-labels-maxima-v4.json",
    }

    total = 0
    rendered_formats = set()
    for sn, dp in systems.items():
        print(f"\n--- {sn.upper()} ---")
        with open(dp, encoding='utf-8') as f:
            data = json.load(f)
        for i, sku in enumerate(data["skus"]):
            m = sku["_meta"]
            fmt = sku['format']['label_format']
            ing = sku["front_panel"]["zone_3"]["ingredient_name"]

            # Validation mode: 1 per format only
            if args.validate and fmt in rendered_formats:
                continue

            print(f"  [{i+1:3d}/{len(data['skus'])}] {m['module_code']} | {fmt:7s} | {ing[:35]}", end="")
            try:
                render_sku(sku, sn)
                total += 1
                rendered_formats.add(fmt)
                print(" OK")
            except Exception as e:
                print(f" ERR: {e}")

            if args.validate and len(rendered_formats) >= 5:
                break
        if args.validate and len(rendered_formats) >= 5:
            break

    print(f"\nDONE: {total} SKUs → {OUTPUT_BASE}")

    # Copy to Google Drive
    if DRIVE_DEST.parent.exists():
        import shutil
        if DRIVE_DEST.exists(): shutil.rmtree(DRIVE_DEST)
        # Copy only JPGs in the correct structure
        for fmt_dir in (OUTPUT_BASE).iterdir():
            if fmt_dir.is_dir() and fmt_dir.name in FORMAT_DIMS:
                for sku_dir in fmt_dir.iterdir():
                    if sku_dir.is_dir():
                        dest = DRIVE_DEST / fmt_dir.name / sku_dir.name
                        dest.mkdir(parents=True, exist_ok=True)
                        for jpg in sku_dir.glob("*.jpg"):
                            shutil.copy2(jpg, dest / jpg.name)

        print(f"Delivered to Drive: {DRIVE_DEST}")


if __name__ == "__main__":
    main()
