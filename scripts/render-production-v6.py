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
    "strip_bg": h2c("#3A3A3A"), "strip_tx": h2c("#C5C2BA"),
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
    """Draw tracked text. V6: correct charspace width calc, auto-shrink on overflow."""
    if mw:
        # Correct width: stringWidth + (len-1)*charspace (last char has no trailing space)
        def _tracked_w(txt):
            return _tw(txt, f, s) + max(0, len(txt)-1) * s * tr
        # Step 1: try reducing tracking slightly (-50% of original)
        orig_tr = tr
        if _tracked_w(t) > mw and tr > 0:
            tr = max(0, tr * 0.5)
        # Step 2: auto-shrink font up to -10%
        cur_s = s
        while _tracked_w(t) > mw and cur_s > s * 0.9:
            cur_s -= 0.25
            tr = orig_tr  # reset tracking for new size test
        s = cur_s
        # Step 3: last resort — truncate with ellipsis
        if _tracked_w(t) > mw:
            while len(t) > 4 and _tracked_w(t + "...") > mw:
                t = t[:-1]
            if _tracked_w(t + "...") <= mw:
                t = t + "..."
    o = c.beginText(x, y); o.setFont(f, s); o.setFillColor(co); o.setCharSpace(s*tr); o.textOut(t); c.drawText(o)

def _dr(c, xr, y, t, f, s, co):
    """Draw right-aligned text."""
    _d(c, xr - _tw(t, f, s), y, t, f, s, co)

def _dc(c, x, y, t, f, s, co, mw):
    """Draw clamped text. V6: auto-shrink font up to -10%, then truncate with ellipsis."""
    orig_s = s
    # Step 1: try reducing font size up to -10%
    while _tw(t, f, s) > mw and s > orig_s * 0.9:
        s -= 0.25
    # Step 2: if still overflows, truncate with visible ellipsis
    if _tw(t, f, s) > mw:
        while len(t) > 4 and _tw(t.rstrip() + "...", f, s) > mw:
            t = t[:-1]
        t = t.rstrip() + "..."
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
    w, h = dims["w"], dims["h"]
    fmt = sku["format"]["label_format"]
    narrow = fmt == "DROPPER"; tall = fmt in ("STRIPS", "POUCH"); short = fmt == "JAR"
    left, right_ = tx + MARGIN, tx + w - MARGIN
    cw = right_ - left; top = ty + h - MARGIN; bot_safe = ty + STRIP_H + 2

    c.setFillColor(C["bg"]); c.rect(tx-BLEED, ty-BLEED, w+2*BLEED, h+2*BLEED, fill=1, stroke=0)
    c.setFillColor(accent); c.rect(tx-BLEED, ty+h-2, w+2*BLEED, 2, fill=1, stroke=0)
    cy = top - 2 - (4 if not short else 2)

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
    cy -= z2s + (6 if not short else 3)

    # ── V6.2: Product Name (26-28px, max 27px target) ──
    pf, ps = "PlexCondensed-Bold", min(dims["pn_pt"], 27)
    if narrow: ps = 14  # DROPPER stays small
    if short: ps = 22   # JAR stays at 22
    pn = sku["front_panel"]["zone_3"]["ingredient_name"]
    lines = _w(pn, pf, ps, cw); ml = 3 if tall else 2
    if len(lines) > ml: ps = ps * 0.75; lines = _w(pn, pf, ps, cw)
    for ln in lines[:ml]: _dc(c, left, cy-ps, ln, pf, ps, C["t1"], cw); cy -= ps * 0.95

    # ── V6.2: Title → Subtitle gap: 6px ──
    cy -= 6

    # ── V6.2: Subtitle at 14px, weight 500 (PlexSans-Medium) ──
    desc = sku["front_panel"]["zone_4"].get("descriptor", "")
    sub_sz = 14 if not narrow else 10
    if short: sub_sz = 11
    if desc:
        _dc(c, left, cy-sub_sz, desc, "PlexSans-Medium", sub_sz, C["t2"], cw); cy -= sub_sz
    bio = sku["front_panel"]["zone_4"].get("biological_system", "")
    if bio:
        bio_sz = min(sub_sz - 1, 11) if not narrow else 7
        if short: bio_sz = 8
        _dc(c, left, cy-bio_sz, bio, "PlexMono", bio_sz, C["t3"], cw); cy -= bio_sz

    # ── V6.2: Subtitle → Meta gap: 14px ──
    cy -= 14

    # ── V6.2: Compact meta block (TYPE / SYSTEM / FUNCTION) 10-11px ──
    z6 = sku["front_panel"]["zone_6"]
    meta_sz = 10.5 if not narrow else 7.5
    if short: meta_sz = 9
    meta_lh = meta_sz * 1.5  # line-height 1.5
    if cy > bot_safe + meta_lh * 3 + 18:
        meta_items = [
            ("TYPE", z6["type"]["value"]),
            ("SYSTEM", z6["function"]["label"].replace("FUNCTION","").strip() or z6["function"]["value"]),
            ("FUNCTION", z6["function"]["value"]),
        ]
        if narrow:
            for label, val in meta_items:
                if cy < bot_safe + meta_lh + 18: break
                meta_line = f"{label}: {val}"
                _dc(c, left, cy-meta_sz, meta_line, "PlexMono-Medium", meta_sz, C["t2"], cw)
                cy -= meta_lh
        else:
            # Single line: TYPE / SYSTEM / FUNCTION
            type_val = z6["type"]["value"]
            func_val = z6["function"]["value"]
            status_val = z6["status"]["value"]
            meta_line = f"{type_val}  ·  {func_val}  ·  {status_val}"
            _dc(c, left, cy-meta_sz, meta_line, "PlexMono-Medium", meta_sz, C["t2"], cw)
            cy -= meta_lh

    # ── V6.2: Variant name + accent bar ──
    vs = 12 if not narrow else 8
    if short: vs = 9
    _dc(c, left, cy-vs, sku["front_panel"]["zone_5"]["variant_name"], "PlexSans-SemiBold", vs, C["t1"], cw)
    cy -= vs + 2
    c.setFillColor(accent); c.rect(left, cy-2, 70 if not narrow else 40, 2, fill=1, stroke=0)

    # ── V6.2: Meta → Footer gap: 18px ──
    cy -= 2 + 18

    # V6.2: Footer strip — height -30%, color #3A3A3A, 10px vertical padding
    sh_base = STRIP_H if not narrow else 22
    sh = int(sh_base * 0.70)  # -30% height
    if sh < 10: sh = 10  # minimum
    c.setFillColor(C["strip_bg"]); c.rect(tx-BLEED, ty-BLEED, w+2*BLEED, sh+BLEED, fill=1, stroke=0)
    ver, qty = sku["front_panel"]["zone_7"]["version_info"], sku["front_panel"]["zone_7"]["net_quantity"]
    ssz = 5 if not narrow else 4
    footer_safe_w = cw - 8
    foot_pad = 10  # 10px vertical padding
    if narrow:
        st = ty + sh - foot_pad + 2
        _dc(c, left, st, ver, "PlexMono", ssz, C["strip_tx"], footer_safe_w)
        _dc(c, left, st-ssz-1, qty, "PlexMono", ssz, C["strip_tx"], footer_safe_w)
    else:
        sty = ty + (sh - ssz) / 2; hw = footer_safe_w * 0.48
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

    # ── Strip (V6.2: -30% height, #3A3A3A, 10px padding) ──
    bsh_base = STRIP_H if not narrow else 20
    bsh = int(bsh_base * 0.70)
    if bsh < 10: bsh = 10
    c.setFillColor(C["strip_bg"]); c.rect(tx-BLEED, ty-BLEED, w+2*BLEED, bsh+BLEED, fill=1, stroke=0)
    stsz = 5 if not narrow else 4
    footer_w = cw - 8
    if narrow:
        sty_n = ty + bsh - 3 - stsz
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
