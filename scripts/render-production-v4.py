#!/usr/bin/env python3
"""
GenoMAX² V4 CLINICAL Production Label Renderer
================================================
Final production from v4 clinical catalog Excel files.
Front label: V3-LOCKED system (unchanged).
Back label: Pre-formatted Back Label Text from v4 (rendered verbatim).
"""

import json, os, sys, math
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
OUTPUT_BASE = BASE / "design-system" / "production-v4"
DRIVE_BASE = Path("G:/My Drive/Work/GenoMAX²/Design/Lables/V9-production-fixed")

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
for name, fn in FONT_MAP.items():
    p = FONTS_DIR / fn
    if p.exists():
        pdfmetrics.registerFont(TTFont(name, str(p)))

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

# ─── TEXT UTILITIES ───────────────────────────────────────────────────────
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

# ─── QR ───────────────────────────────────────────────────────────────────
def make_qr(url):
    qr = qrcode.QRCode(version=2, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=1)
    qr.add_data(url); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO(); img.save(buf, format='PNG'); buf.seek(0)
    return ImageReader(buf)

# ─── CROP MARKS ──────────────────────────────────────────────────────────
def crop_marks(c, tx, ty, w, h):
    c.setStrokeColor(CMYKColor(0,0,0,1)); c.setLineWidth(0.25)
    L, O = 12, 3
    for p in [(tx-O,ty+h,tx-O-L,ty+h),(tx,ty+h+O,tx,ty+h+O+L),(tx+w+O,ty+h,tx+w+O+L,ty+h),(tx+w,ty+h+O,tx+w,ty+h+O+L),(tx-O,ty,tx-O-L,ty),(tx,ty-O,tx,ty-O-L),(tx+w+O,ty,tx+w+O+L,ty),(tx+w,ty-O,tx+w,ty-O-L)]:
        c.line(*p)


# ═══════════════════════════════════════════════════════════════════════════
# FRONT LABEL (V3-LOCKED — identical logic to v3 renderer)
# ═══════════════════════════════════════════════════════════════════════════
def render_front(c, sku, dims, accent, tx, ty):
    w, h = dims["w"], dims["h"]
    fmt = sku["format"]["label_format"]
    narrow = fmt == "DROPPER"
    tall = fmt in ("STRIPS", "POUCH")
    short = fmt == "JAR"

    left, right_ = tx + MARGIN, tx + w - MARGIN
    cw = right_ - left
    top = ty + h - MARGIN
    bot_safe = ty + STRIP_H + 2

    # Background + ceiling
    c.setFillColor(C["bg"]); c.rect(tx-BLEED, ty-BLEED, w+2*BLEED, h+2*BLEED, fill=1, stroke=0)
    c.setFillColor(accent); c.rect(tx-BLEED, ty+h-2, w+2*BLEED, 2, fill=1, stroke=0)

    cy = top - 2 - (4 if not short else 2)

    # Zone 1: Brand + Module
    bsz = 12 if not narrow else 8
    if short: bsz = 10
    _dt(c, left, cy-bsz, "GenoMAX\u00b2", "PlexMono-Bold", bsz, C["t1"], 0.18, mw=cw*0.65)
    _dr(c, right_, cy-(6 if not narrow else 5), sku["front_panel"]["zone_1"]["module_code"], "PlexMono-Medium", 6 if not narrow else 5, C["t3"])
    cy -= bsz + (3 if not short else 2)

    # Brand rule
    c.saveState(); c.setStrokeColor(C["t1"]); c.setLineWidth(0.5); c.setStrokeAlpha(0.25)
    c.line(left, cy, right_, cy); c.restoreState()
    cy -= (4 if not short else 2)

    # Zone 2
    z2s = 7 if not narrow else 5.5
    if short: z2s = 6
    _dt(c, left, cy-z2s, sku["front_panel"]["zone_2"]["text"], "PlexMono-Medium", z2s, C["t2"], 0.18, mw=cw)
    cy -= z2s + (6 if not short else 3)

    # Zone 3: Product Name
    pf, ps = "PlexCondensed-Bold", dims["pn_pt"]
    pn = sku["front_panel"]["zone_3"]["ingredient_name"]
    lines = _w(pn, pf, ps, cw)
    ml = 3 if tall else 2
    if len(lines) > ml:
        ps = ps * 0.7; lines = _w(pn, pf, ps, cw)
    for ln in lines[:ml]:
        _dc(c, left, cy-ps, ln, pf, ps, C["t1"], cw); cy -= ps * 0.95
    cy -= 3

    # Zone 4: Descriptor + Bio System
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

    # Zone 5: Variant + Accent Rule
    vs = 12 if not narrow else 8
    if short: vs = 9
    _dc(c, left, cy-vs, sku["front_panel"]["zone_5"]["variant_name"], "PlexSans-SemiBold", vs, C["t1"], cw)
    cy -= vs + 2
    c.setFillColor(accent); c.rect(left, cy-2, 70 if not narrow else 40, 2, fill=1, stroke=0)
    cy -= 2 + (6 if not short else 3)

    # Zone 6: Metadata
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

    # Zone 7: Dark Strip
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
# BACK LABEL — V4 CLINICAL (pre-formatted text block)
# ═══════════════════════════════════════════════════════════════════════════
def render_back(c, sku, dims, accent, tx, ty):
    w, h = dims["w"], dims["h"]
    fmt = sku["format"]["label_format"]
    narrow = fmt == "DROPPER"
    tall = fmt in ("STRIPS", "POUCH")
    tier = dims.get("tier", 1)

    left, right_ = tx + MARGIN, tx + w - MARGIN
    cw = right_ - left
    top = ty + h - MARGIN

    # Background + ceiling
    c.setFillColor(C["bg"]); c.rect(tx-BLEED, ty-BLEED, w+2*BLEED, h+2*BLEED, fill=1, stroke=0)
    c.setFillColor(accent); c.rect(tx-BLEED, ty+h-2, w+2*BLEED, 2, fill=1, stroke=0)

    # ── Strip (bottom) ──
    bsh = STRIP_H if not narrow else 20
    c.setFillColor(C["strip_bg"]); c.rect(tx-BLEED, ty-BLEED, w+2*BLEED, bsh+BLEED, fill=1, stroke=0)
    strip_ssz = 5.5 if not narrow else 4
    if narrow:
        st = ty + bsh - 3 - strip_ssz
        _dc(c, left, st, "genomax.ai", "PlexMono", strip_ssz, C["strip_tx"], cw)
        _dc(c, left, st-strip_ssz-2, "Distributed by Genomax LLC", "PlexMono", strip_ssz, C["strip_tx"], cw)
    else:
        sty = ty + (bsh - strip_ssz) / 2
        _dc(c, left, sty, "genomax.ai \u00b7 support@genomax.ai", "PlexMono", strip_ssz, C["strip_tx"], cw*0.5)
        _dr(c, right_, sty, "Distributed by Genomax LLC", "PlexMono", strip_ssz, C["strip_tx"])

    strip_top = ty + bsh

    # ── QR code setup ──
    qr_sz = 40 if not narrow else 28
    mc = sku["_meta"]["module_code"]
    osn = sku["_meta"]["os"].replace("\u00b2","2").replace("²","2").lower()
    qr_img = make_qr(f"https://genomax.ai/module/{osn}/{mc.lower()}")

    has_qr_side = not narrow and not tall
    qr_reserve = qr_sz + 8 if has_qr_side else 0
    text_w = cw - qr_reserve

    # ── Brand header ──
    cy = top - 2 - 4
    bbsz = 8 if not narrow else 6
    _dt(c, left, cy-bbsz, "GenoMAX\u00b2", "PlexMono-Bold", bbsz, C["t1"], 0.18, mw=cw*0.6)
    cy -= bbsz + 3

    # Brand rule
    c.saveState(); c.setStrokeColor(C["t1"]); c.setLineWidth(0.5); c.setStrokeAlpha(0.25)
    c.line(left, cy, right_, cy); c.restoreState()
    cy -= 4

    # ── QR placement for wide formats ──
    if has_qr_side:
        qr_x = right_ - qr_sz
        qr_y = cy - qr_sz - 4
        if qr_y < strip_top + 4: qr_y = strip_top + 4
        c.drawImage(qr_img, qr_x, qr_y, qr_sz, qr_sz)
        cta_w = _tw("SCAN FOR INFO", "PlexMono", 5)
        _d(c, qr_x + (qr_sz-cta_w)/2, qr_y-7, "SCAN FOR INFO", "PlexMono", 5, C["t3"])

    # ── Parse and render Back Label Text ──
    raw_text = sku.get("back_panel", {}).get("back_label_text", "")
    if not raw_text:
        return

    # Split into logical paragraphs
    paragraphs = raw_text.split('\n')

    # Font sizing based on tier and format
    if tier == 2 or narrow:
        body_f, body_s = "PlexSans", 6
        head_f, head_s = "PlexMono-Medium", 5.5
    else:
        body_f, body_s = "PlexSans", 6.5
        head_f, head_s = "PlexMono-Medium", 6

    warn_s = 6  # minimum for warnings
    line_gap = 1
    para_gap = 4
    section_heads = {"Suggested Use:", "Warnings:", "Ingredients:"}

    # Calculate floor: strip + small margin
    floor_y = strip_top + 4

    # For narrow/tall: reserve QR space at bottom
    if not has_qr_side:
        floor_y += qr_sz + 12  # QR + label + gap

    # Render paragraphs top-down
    for para in paragraphs:
        para = para.strip()
        if not para:
            cy -= para_gap
            continue

        if cy < floor_y:
            break

        # Skip [QR] placeholder — we render actual QR
        if para == "[QR]":
            continue

        # Skip "Scan to begin" — replaced by actual QR
        if para.lower() == "scan to begin":
            continue

        # Skip "genomax.ai" standalone — in strip
        if para.lower() == "genomax.ai":
            continue

        # Skip "Distributed by Genomax LLC" — in strip
        if para.lower().startswith("distributed by"):
            continue

        # Detect section headers
        is_head = para in section_heads or para.endswith(":")

        if is_head:
            cy -= 2  # extra space before header
            if cy < floor_y: break
            _dt(c, left, cy-head_s, para.rstrip(":").upper(), head_f, head_s, C["t3"], 0.08, mw=text_w)
            cy -= head_s + 2

            # Draw divider after section header
            c.setStrokeColor(C["div"]); c.setLineWidth(0.35)
            c.line(left, cy, left+text_w, cy)
            cy -= 2
        else:
            # Determine font size: warnings get minimum 6pt
            fs = warn_s if "not intended" in para.lower() or "not been evaluated" in para.lower() or "caution" in para.lower() or "use with caution" in para.lower() else body_s

            # "This is not your full protocol" gets special treatment
            if para == "This is not your full protocol.":
                _dc(c, left, cy-body_s, para, "PlexSans-SemiBold", body_s, C["t1"], text_w)
                cy -= body_s + para_gap
                # Divider after context anchor
                c.setStrokeColor(C["div"]); c.setLineWidth(0.35)
                c.line(left, cy, left+text_w, cy)
                cy -= 3
                continue

            # Wrap and render
            wrapped = _w(para, body_f, fs, text_w)
            for ln in wrapped:
                if cy < floor_y: break
                _dc(c, left, cy-fs, ln, body_f, fs, C["t2"] if fs == warn_s else C["t1"], text_w)
                cy -= fs + line_gap

    # ── QR for narrow/tall formats (at bottom, above strip) ──
    if not has_qr_side:
        qr_y = strip_top + 4
        qr_x = left
        c.drawImage(qr_img, qr_x, qr_y, qr_sz, qr_sz)
        _d(c, qr_x+qr_sz+4, qr_y+qr_sz/2-2, "SCAN FOR INFO", "PlexMono", 5, C["t3"])


# ═══════════════════════════════════════════════════════════════════════════
# RENDER PIPELINE
# ═══════════════════════════════════════════════════════════════════════════
def render_sku(sku, system_name, output_base=None):
    meta = sku["_meta"]
    fmt = sku["format"]["label_format"]
    if fmt not in FORMAT_DIMS: return None

    dims = FORMAT_DIMS[fmt]
    accent = C["ax_mo"] if "MAXimo" in meta["os"] else C["ax_ma"]

    base = output_base or OUTPUT_BASE
    out_dir = base / system_name / fmt / meta["module_code"]
    out_dir.mkdir(parents=True, exist_ok=True)

    ing = sku["front_panel"]["zone_3"]["ingredient_name"]
    safe = ing.replace("/","-").replace("\\","-").replace(":","")[:40].strip().replace(" ","_")
    fb = f"{meta['module_code']}_{safe}_{fmt}"

    cm = 20
    pw, ph = dims["w"]+2*BLEED+2*cm, dims["h"]+2*BLEED+2*cm
    tx, ty_ = cm+BLEED, cm+BLEED

    for side in ["front", "back"]:
        pdf_p = out_dir / f"{fb}_{side}.pdf"
        cv = canvas.Canvas(str(pdf_p), pagesize=(pw, ph))
        cv.setAuthor("GenoMAX\u00b2 V4 Clinical"); cv.setTitle(f"{meta['module_code']} {ing} {fmt} {side}")
        cv.setFillColor(C["white"]); cv.rect(0,0,pw,ph,fill=1,stroke=0)

        if side == "front": render_front(cv, sku, dims, accent, tx, ty_)
        else: render_back(cv, sku, dims, accent, tx, ty_)

        crop_marks(cv, tx, ty_, dims["w"], dims["h"])
        info = f"GenoMAX\u00b2 | {meta['module_code']} | {meta['os']} | {fmt} | {side.upper()} | V4-CLINICAL | CMYK | 3mm bleed"
        _d(cv, tx, ty_-BLEED-10, info, "PlexMono", 3.5, C["t3"])
        cv.save()

    return out_dir


def main():
    print("=" * 60)
    print("GenoMAX\u00b2 V4 CLINICAL — Final Production Renderer")
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

    print(f"\nDONE: {total} SKUs, {total*2} PDFs → {OUTPUT_BASE}")

    # Copy to Google Drive if available
    if DRIVE_BASE.parent.exists():
        import shutil
        v4_drive = DRIVE_BASE.parent / "V4-clinical-production"
        if v4_drive.exists():
            shutil.rmtree(v4_drive)
        shutil.copytree(OUTPUT_BASE, v4_drive)
        print(f"Copied to Drive: {v4_drive}")


if __name__ == "__main__":
    main()
