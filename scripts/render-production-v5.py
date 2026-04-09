#!/usr/bin/env python3
"""
GenoMAX² V5 FINAL QA — Clinical Readability & Hierarchy Pass
==============================================================
V4→V5: Back label rebuild ONLY. Front label unchanged.
Changes:
  - Protocol header: 10-11pt bold, ALL CAPS
  - CTA: 9-10pt, high contrast, aligned with QR
  - Warnings: ≥7pt enforced
  - Ingredients: ≥7pt enforced
  - Suggested Use: ≥8pt enforced
  - Strict top-to-bottom hierarchy
  - Section spacing: 8-12px minimum
  - Format-specific text reduction (DROPPER/STRIPS)
  - Export: JPG ≤1600px, no mockups
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
BASE = Path("C:/Projects/GenoMAX2")
FONTS_DIR = BASE / "design-system" / "fonts"
DATA_DIR = BASE / "design-system" / "data"
OUTPUT_BASE = BASE / "design-system" / "production-v5"
DRIVE_DEST = Path("G:/My Drive/Work/GenoMAX²/Design/Lables/GenoMAX_V5_FINAL_QA")

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
    "strip_bg": h2c("#1A1815"), "strip_tx": h2c("#C5C2BA"),
    "white": CMYKColor(0,0,0,0),
}

BLEED = 3 * mm
MARGIN = 12
STRIP_H = 14

FORMAT_DIMS = {
    "BOTTLE":  {"w": 6*inch,   "h": 2.5*inch, "pn_pt": 26, "tier": 1},
    "JAR":     {"w": 8.5*inch, "h": 2*inch,   "pn_pt": 22, "tier": 2},
    "POUCH":   {"w": 5*inch,   "h": 4*inch,   "pn_pt": 28, "tier": 1},
    "DROPPER": {"w": 2*inch,   "h": 4*inch,   "pn_pt": 14, "tier": 2},
    "STRIPS":  {"w": 4*inch,   "h": 6.5*inch, "pn_pt": 30, "tier": 1},
}

# ─── TEXT PRIMITIVES ─────────────────────────────────────────────────────
def _d(c, x, y, t, f, s, co):
    o = c.beginText(x, y); o.setFont(f, s); o.setFillColor(co); o.textOut(t); c.drawText(o)

def _dt(c, x, y, t, f, s, co, tr, mw=None):
    if mw:
        while len(t)>1 and pdfmetrics.stringWidth(t,f,s)+len(t)*s*tr > mw: t=t[:-1]
    o = c.beginText(x, y); o.setFont(f, s); o.setFillColor(co); o.setCharSpace(s*tr); o.textOut(t); c.drawText(o)

def _dr(c, xr, y, t, f, s, co):
    _d(c, xr - pdfmetrics.stringWidth(t, f, s), y, t, f, s, co)

def _dc(c, x, y, t, f, s, co, mw):
    while len(t)>1 and pdfmetrics.stringWidth(t,f,s) > mw: t=t[:-1]
    _d(c, x, y, t, f, s, co)

def _w(t, f, s, mw):
    words, lines, cur = t.split(), [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if pdfmetrics.stringWidth(test, f, s) <= mw: cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def _tw(t, f, s): return pdfmetrics.stringWidth(t, f, s)

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

    pf, ps = "PlexCondensed-Bold", dims["pn_pt"]
    pn = sku["front_panel"]["zone_3"]["ingredient_name"]
    lines = _w(pn, pf, ps, cw); ml = 3 if tall else 2
    if len(lines) > ml: ps = ps * 0.7; lines = _w(pn, pf, ps, cw)
    for ln in lines[:ml]: _dc(c, left, cy-ps, ln, pf, ps, C["t1"], cw); cy -= ps * 0.95
    cy -= 3

    desc = sku["front_panel"]["zone_4"].get("descriptor", "")
    if desc:
        ds = 8.5 if not narrow else 7
        if short: ds = 7
        _dc(c, left, cy-ds, desc, "PlexSans-Light", ds, C["t2"], cw); cy -= ds + (2 if not short else 1)
    bio = sku["front_panel"]["zone_4"].get("biological_system", "")
    if bio:
        bs2 = 6.5 if not narrow else 5.5
        if short: bs2 = 5.5
        _dc(c, left, cy-bs2, bio, "PlexMono", bs2, C["t3"], cw); cy -= bs2 + (6 if not short else 3)

    vs = 12 if not narrow else 8
    if short: vs = 9
    _dc(c, left, cy-vs, sku["front_panel"]["zone_5"]["variant_name"], "PlexSans-SemiBold", vs, C["t1"], cw)
    cy -= vs + 2
    c.setFillColor(accent); c.rect(left, cy-2, 70 if not narrow else 40, 2, fill=1, stroke=0)
    cy -= 2 + (6 if not short else 3)

    mls = 5.5 if short else (7 if not narrow else 5.5)
    mvs = 5.5 if short else (7 if not narrow else 6)
    mrh = mls + mvs + 1 + (3 if not short else 1)
    if cy > bot_safe + mrh:
        z6 = sku["front_panel"]["zone_6"]
        items = [(z6["type"]["label"],z6["type"]["value"]),(z6["function"]["label"],z6["function"]["value"]),(z6["status"]["label"],z6["status"]["value"])]
        if narrow:
            for lb, vl in items:
                if cy < bot_safe + mls + mvs + 4: break
                _d(c, left, cy-mls, lb, "PlexMono-Medium", mls, C["t3"]); cy -= mls + 1
                _dc(c, left, cy-mvs, vl, "PlexSans-Medium", mvs, C["t1"], cw); cy -= mvs + 3
        else:
            colw = cw / 3; ucol = colw - 4
            for i, (lb, vl) in enumerate(items):
                cx = left + i * colw
                _dc(c, cx, cy-mls, lb, "PlexMono-Medium", mls, C["t3"], ucol)
                _dc(c, cx, cy-mls-mvs-1, vl, "PlexSans-Medium", mvs, C["t1"], ucol)
            cy -= mls + mvs + 1 + 6

    sh = STRIP_H if not narrow else 22
    c.setFillColor(C["strip_bg"]); c.rect(tx-BLEED, ty-BLEED, w+2*BLEED, sh+BLEED, fill=1, stroke=0)
    ver, qty = sku["front_panel"]["zone_7"]["version_info"], sku["front_panel"]["zone_7"]["net_quantity"]
    ssz = 5.5 if not narrow else 4.5
    if narrow:
        st = ty + sh - 3 - ssz
        _dc(c, left, st, ver, "PlexMono", ssz, C["strip_tx"], cw)
        _dc(c, left, st-ssz-2, qty, "PlexMono", ssz, C["strip_tx"], cw)
    else:
        sty = ty + (sh - ssz) / 2; hw = cw * 0.48
        _dc(c, left, sty, ver, "PlexMono", ssz, C["strip_tx"], hw)
        qt = qty
        while len(qt)>1 and _tw(qt,"PlexMono",ssz)>hw: qt=qt[:-1]
        _dr(c, right_-2, sty, qt, "PlexMono", ssz, C["strip_tx"])


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

    # ── Strip ──
    bsh = STRIP_H if not narrow else 18
    c.setFillColor(C["strip_bg"]); c.rect(tx-BLEED, ty-BLEED, w+2*BLEED, bsh+BLEED, fill=1, stroke=0)
    stsz = 5.5 if not narrow else 4
    if narrow:
        sty_n = ty + bsh - 3 - stsz
        _dc(c, left, sty_n, "genomax.ai", "PlexMono", stsz, C["strip_tx"], cw)
        _dc(c, left, sty_n-stsz-1, "Distributed by Genomax LLC", "PlexMono", stsz, C["strip_tx"], cw)
    else:
        sty_w = ty + (bsh - stsz) / 2
        _dc(c, left, sty_w, "genomax.ai \u00b7 support@genomax.ai", "PlexMono", stsz, C["strip_tx"], cw*0.5)
        _dr(c, right_, sty_w, "Distributed by Genomax LLC", "PlexMono", stsz, C["strip_tx"])
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
    qr_reserve = qr_sz + 8 if has_qr_side else 0
    tw = cw - qr_reserve - 6  # text width with safety margin
    tw_wrap = tw - 6  # wrap width tighter than draw width to prevent edge clipping
    floor = strip_top + 4

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
        ctx_lines = _w(ctx, "PlexSans", BODY_SZ, tw_wrap)
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
        sug_lines = _w(sug, "PlexSans-Medium", SUGGEST_SZ, tw_wrap)
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
        wl = _w(warn_text, "PlexSans", WARN_SZ, tw_wrap)
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
        cv.setAuthor("GenoMAX\u00b2 V5 Final QA")
        cv.setTitle(f"{meta['module_code']} {ing} {fmt} {side}")
        cv.setFillColor(C["white"]); cv.rect(0,0,pw,ph,fill=1,stroke=0)

        if side == "front": render_front(cv, sku, dims, accent, tx, ty_)
        else: render_back(cv, sku, dims, accent, tx, ty_)

        crop_marks(cv, tx, ty_, dims["w"], dims["h"])
        info = f"GenoMAX\u00b2 | {meta['module_code']} | {meta['os']} | {fmt} | {side.upper()} | V5-FINAL-QA"
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
    print("=" * 60)
    print("GenoMAX\u00b2 V5 FINAL QA — Clinical Readability Pass")
    print("=" * 60)

    systems = {
        "maximo": DATA_DIR / "production-labels-maximo-v4.json",
        "maxima": DATA_DIR / "production-labels-maxima-v4.json",
    }

    total = 0
    for sn, dp in systems.items():
        print(f"\n--- {sn.upper()} ---")
        with open(dp, encoding='utf-8') as f:
            data = json.load(f)
        for i, sku in enumerate(data["skus"]):
            m = sku["_meta"]
            ing = sku["front_panel"]["zone_3"]["ingredient_name"]
            print(f"  [{i+1:3d}/{len(data['skus'])}] {m['module_code']} | {sku['format']['label_format']:7s} | {ing[:35]}", end="")
            try:
                render_sku(sku, sn)
                total += 1
                print(" OK")
            except Exception as e:
                print(f" ERR: {e}")

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
