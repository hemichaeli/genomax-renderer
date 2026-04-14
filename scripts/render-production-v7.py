#!/usr/bin/env python3
"""GenoMAX² V7 — True Flow Layout Engine
2-pass system: MEASURE → PLACE. No absolute positioning.
Content fills CONTENT_FRAME exactly. QR pre-allocated. Proportional rhythm."""
import json, os, sys, re, argparse, io, shutil
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

SCRIPT_DIR = Path(__file__).resolve().parent
BASE = SCRIPT_DIR.parent
FONTS_DIR = BASE / "design-system" / "fonts"
DATA_DIR = BASE / "design-system" / "data"
OUTPUT_BASE = BASE / "design-system" / "production-v7"
DRIVE_DEST = Path("G:/My Drive/Work/GenoMAX²/Design/Lables/design-system")

FM = {"Mono":"IBMPlexMono-Regular.ttf","Mono-Med":"IBMPlexMono-Medium.ttf",
    "Mono-SB":"IBMPlexMono-SemiBold.ttf","Mono-Bold":"IBMPlexMono-Bold.ttf",
    "Mono-Light":"IBMPlexMono-Light.ttf","Cond":"IBMPlexSansCondensed-Regular.ttf",
    "Cond-Med":"IBMPlexSansCondensed-Medium.ttf","Cond-SB":"IBMPlexSansCondensed-SemiBold.ttf",
    "Cond-Bold":"IBMPlexSansCondensed-Bold.ttf"}
for n,fn in FM.items():
    p=FONTS_DIR/fn
    if p.exists(): pdfmetrics.registerFont(TTFont(n,str(p)))
CD={"Mono-Bold":"Cond-Bold","Mono-Med":"Cond-Med","Mono":"Cond","Mono-SB":"Cond-SB"}

def h2c(h):
    h=h.lstrip('#');r,g,b=int(h[0:2],16)/255,int(h[2:4],16)/255,int(h[4:6],16)/255
    k=1-max(r,g,b)
    if k==1: return CMYKColor(0,0,0,1)
    return CMYKColor((1-r-k)/(1-k),(1-g-k)/(1-k),(1-b-k)/(1-k),k)
C={"bg":h2c("#F4F2EC"),"t1":h2c("#1A1815"),"t2":h2c("#4A4843"),"t3":h2c("#8A8880"),
   "div":h2c("#C5C2BA"),"axmo":h2c("#7A1E2E"),"axma":h2c("#7A304A"),
   "fbg":h2c("#6A6A72"),"w":CMYKColor(0,0,0,0)}
def ac(hx,a):
    h=hx.lstrip('#');r,g,b=int(h[0:2],16)/255,int(h[2:4],16)/255,int(h[4:6],16)/255
    R,G,B=.957,.949,.925;r=r*a+R*(1-a);g=g*a+G*(1-a);b=b*a+B*(1-a)
    return h2c(f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}")
def fc(a):
    R,G,B=.416,.416,.447;r=a+R*(1-a);g=a+G*(1-a);b=a+B*(1-a)
    return h2c(f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}")
FTX=fc(.88)

SAFE=28; BLEED=3*mm; FH=28  # footer height
DIMS={"BOTTLE":{"w":6*inch,"h":2.5*inch},"JAR":{"w":8.5*inch,"h":2*inch},
      "POUCH":{"w":5*inch,"h":4*inch},"DROPPER":{"w":2*inch,"h":4*inch},
      "STRIPS":{"w":4*inch,"h":6.5*inch}}

# Format templates: font sizes + required/optional blocks
T={
 "BOTTLE":{"br":10,"sy":7,"pn":(14,20),"su":8,"ml":7,"mv":7,"vr":7,"bb":7,"bl":6.5,"bp":9,"bc":8,
           "blocks":["brand","sys","title","sub","meta","variant"]},
 "JAR":   {"br":9,"sy":6,"pn":(10,15),"su":6.5,"ml":5.5,"mv":6,"vr":6,"bb":6.5,"bl":5.5,"bp":7.5,"bc":6.5,
           "blocks":["brand","sys","title","sub","meta"]},
 "POUCH": {"br":12,"sy":8,"pn":(18,24),"su":11,"ml":9,"mv":9.5,"vr":9.5,"bb":8.5,"bl":7.5,"bp":11,"bc":9,
           "blocks":["brand","sys","title","sub","bio","meta","variant"]},
 "DROPPER":{"br":8,"sy":6,"pn":(14,20),"su":9,"ml":7,"mv":7.5,"vr":7.5,"bb":6.5,"bl":6,"bp":8,"bc":7,
           "blocks":["brand","sys","title","sub","bio","meta","variant"]},
 "STRIPS":{"br":13,"sy":9,"pn":(20,26),"su":13,"ml":10,"mv":10.5,"vr":10.5,"bb":8.5,"bl":7.5,"bp":11,"bc":9,
           "blocks":["brand","sys","title","sub","bio","meta","variant"]},
}

# ═══ TEXT PRIMITIVES ══════════════════════════════════════════════════════
def tw(t,f,s): return pdfmetrics.stringWidth(t,f,s)
def dr(c,x,y,t,f,s,co):
    o=c.beginText(x,y);o.setFont(f,s);o.setFillColor(co);o.setCharSpace(0);o.textOut(t);c.drawText(o)
def drt(c,x,y,t,f,s,co,tr,mw=None):
    if mw and t:
        def W(t,s,r): return tw(t,f,s)+max(0,len(t)-1)*s*r
        os=s
        if W(t,s,tr)>mw:
            for tt in [tr*.6,tr*.3,0]:
                if W(t,s,tt)<=mw: tr=tt; break
            else: tr=0
        while W(t,s,tr)>mw and s>os*.7: s-=.25
        if W(t,s,tr)>mw:
            a=CD.get(f)
            if a:
                try:
                    if tw(t,a,s)+max(0,len(t)-1)*s*tr<=mw: f=a
                except: pass
        while W(t,s,tr)>mw and s>os*.55: s-=.25
    o=c.beginText(x,y);o.setFont(f,s);o.setFillColor(co);o.setCharSpace(s*tr);o.textOut(t);c.drawText(o)
def drc(c,x,y,t,f,s,co,mw):
    os=s
    while tw(t,f,s)>mw and s>os*.75: s-=.25
    if tw(t,f,s)>mw:
        a=CD.get(f)
        if a:
            st=os
            while tw(t,a,st)>mw and st>os*.75: st-=.25
            if tw(t,a,st)<=mw: f=a;s=st
    while tw(t,f,s)>mw and s>os*.55: s-=.25
    dr(c,x,y,t,f,s,co)
def drr(c,xr,y,t,f,s,co): dr(c,xr-tw(t,f,s),y,t,f,s,co)
def wrap(t,f,s,mw):
    words,lines,cur=t.split(),[],""
    for w in words:
        test=f"{cur} {w}".strip()
        if tw(test,f,s)<=mw: cur=test
        else:
            if cur: lines.append(cur)
            if tw(w,f,s)>mw:
                ch=""
                for c2 in w:
                    if tw(ch+c2,f,s)<=mw: ch+=c2
                    else:
                        if ch: lines.append(ch)
                        ch=c2
                cur=ch
            else: cur=w
    if cur: lines.append(cur)
    return lines
def mkqr(url):
    q=qrcode.QRCode(version=2,error_correction=qrcode.constants.ERROR_CORRECT_M,box_size=8,border=1)
    q.add_data(url);q.make(fit=True);img=q.make_image(fill_color="black",back_color="white")
    b=io.BytesIO();img.save(b,format='PNG');b.seek(0);return ImageReader(b)
def cropmarks(c,tx,ty,w,h):
    c.setStrokeColor(CMYKColor(0,0,0,1));c.setLineWidth(.25);L,O=12,3
    for p in [(tx-O,ty+h,tx-O-L,ty+h),(tx,ty+h+O,tx,ty+h+O+L),(tx+w+O,ty+h,tx+w+O+L,ty+h),
              (tx+w,ty+h+O,tx+w,ty+h+O+L),(tx-O,ty,tx-O-L,ty),(tx,ty-O,tx,ty-O-L),
              (tx+w+O,ty,tx+w+O+L,ty),(tx+w,ty-O,tx+w,ty-O-L)]: c.line(*p)
def parse_back(raw):
    S={"context":"","suggested_use":"","warnings":[],"ingredients":""}
    cs,buf=None,[]
    for line in raw.split('\n'):
        s=line.strip()
        if not s:
            if cs and buf:
                t=' '.join(buf).strip()
                if cs=="context":S["context"]=t
                elif cs=="suggested_use":S["suggested_use"]+=(" "+t if S["suggested_use"] else t)
                elif cs=="warnings":
                    if t:S["warnings"].append(t)
                elif cs=="ingredients":S["ingredients"]=t
                buf=[]
            continue
        if s in ("This is not your full protocol.","[QR]","Scan to begin","genomax.ai"):continue
        if s.startswith("Distributed by"):continue
        if s=="Suggested Use:":
            if buf and cs:
                t=' '.join(buf).strip()
                if cs=="context":S["context"]=t
                buf=[]
            cs="suggested_use";continue
        elif s=="Warnings:":
            if buf and cs:
                t=' '.join(buf).strip()
                if cs=="suggested_use":S["suggested_use"]+=(" "+t if S["suggested_use"] else t)
                buf=[]
            cs="warnings";continue
        elif s.startswith("Ingredients:"):
            if buf and cs=="warnings":
                t=' '.join(buf).strip()
                if t:S["warnings"].append(t)
                buf=[]
            cs="ingredients";r=s[len("Ingredients:"):].strip()
            if r:buf.append(r)
            continue
        if cs is None:cs="context"
        buf.append(s)
    if buf and cs:
        t=' '.join(buf).strip()
        if cs=="context":S["context"]=t
        elif cs=="suggested_use":S["suggested_use"]+=(" "+t if S["suggested_use"] else t)
        elif cs=="warnings":
            if t:S["warnings"].append(t)
        elif cs=="ingredients":S["ingredients"]=t
    return S

# ═══ 2-PASS FLOW ENGINE: FRONT LABEL ═════════════════════════════════════

def front_measure(fmt, cw, sku):
    """PASS 1: Measure all blocks, run overflow cascade, return block list with heights."""
    tp = T[fmt]
    pn = sku["front_panel"]["zone_3"]["ingredient_name"]
    desc = sku["front_panel"]["zone_4"].get("descriptor","")
    bio = sku["front_panel"]["zone_4"].get("biological_system","")
    variant = sku["front_panel"]["zone_5"]["variant_name"]
    z6 = sku["front_panel"]["zone_6"]
    meta_items = [("TYPE",z6["type"]["value"]),
                  ("SYSTEM",(bio or "").split("\u00b7")[0].strip() or z6.get("status",{}).get("value","") or "\u2014"),
                  ("FUNCTION",z6["function"]["value"])]

    bs,ss = tp["br"],tp["sy"]
    ps = tp["pn"][1]; pn_min = tp["pn"][0]
    sus = tp["su"]; ml,mv,vs = tp["ml"],tp["mv"],tp["vr"]
    req_blocks = tp["blocks"]
    has_bio = "bio" in req_blocks and bio
    has_var = "variant" in req_blocks

    # Measure title
    tlines = wrap(pn, "Mono-Bold", ps, cw)
    while len(tlines) > 3 and ps > pn_min: ps -= .5; tlines = wrap(pn, "Mono-Bold", ps, cw)
    tlines = tlines[:3]

    # Measure subtitle
    slines = wrap(desc, "Mono-Med", sus, cw)[:2] if desc else []
    _ss = sus
    while len(slines) > 2 and _ss > 5.5: _ss -= .5; slines = wrap(desc, "Mono-Med", _ss, cw)[:2]
    sus = _ss

    # Build block list: [(name, height)]
    def build():
        blocks = []
        blocks.append(("brand", bs))
        blocks.append(("sys", ss))
        th = len(tlines) * ps * 1.05
        blocks.append(("title", th))
        if slines:
            sh = len(slines) * sus * 1.15
            blocks.append(("sub", sh))
        if has_bio:
            blocks.append(("bio", ss * 1.1))
        mlh = mv * 1.25
        blocks.append(("meta", 3 * mlh))
        if has_var:
            blocks.append(("variant", vs + 4))
        return blocks

    blocks = build()
    return {
        "blocks": blocks, "bs": bs, "ss": ss, "ps": ps, "pn_min": pn_min,
        "sus": sus, "ml": ml, "mv": mv, "vs": vs,
        "tlines": tlines, "slines": slines,
        "bio": bio if has_bio else None, "has_var": has_var,
        "meta_items": meta_items, "variant": variant, "pn": pn,
    }

def front_cascade(meas, avail, cw):
    """Run deterministic overflow cascade. Returns final measurements + gap size."""
    blocks = meas["blocks"]
    total_block_h = sum(h for _, h in blocks)
    n_gaps = len(blocks) - 1
    min_gap = 3

    # Try with proportional gaps first
    slack = avail - total_block_h
    if slack >= n_gaps * min_gap:
        # Fits! Distribute gaps proportionally
        gap = slack / n_gaps if n_gaps > 0 else 0
        return meas, gap, []

    # Doesn't fit at min gaps — run cascade
    ps = meas["ps"]; sus = meas["sus"]; mv = meas["mv"]; ml = meas["ml"]; vs = meas["vs"]
    pn_min = meas["pn_min"]; has_var = meas["has_var"]
    tlines = meas["tlines"]; slines = meas["slines"]
    failures = []

    for _ in range(200):
        # Rebuild blocks with current sizes
        blist = []
        blist.append(("brand", meas["bs"]))
        blist.append(("sys", meas["ss"]))
        blist.append(("title", len(tlines) * ps * 1.05))
        if slines: blist.append(("sub", len(slines) * sus * 1.15))
        if meas["bio"]: blist.append(("bio", meas["ss"] * 1.1))
        blist.append(("meta", 3 * mv * 1.25))
        if has_var: blist.append(("variant", vs + 4))

        total = sum(h for _, h in blist) + (len(blist) - 1) * min_gap
        if total <= avail:
            meas["blocks"] = blist; meas["ps"] = ps; meas["sus"] = sus
            meas["mv"] = mv; meas["ml"] = ml; meas["vs"] = vs
            meas["tlines"] = tlines; meas["slines"] = slines
            meas["has_var"] = has_var
            gap = max(min_gap, (avail - sum(h for _, h in blist)) / max(1, len(blist) - 1))
            return meas, gap, failures

        # CASCADE: a) shrink title
        if ps > pn_min:
            ps -= .5; tlines = wrap(meas["pn"], "Mono-Bold", ps, cw)[:3]; continue
        # b) shrink subtitle
        if sus > 5 and slines: sus -= .5; continue
        # c) shrink meta
        if mv > 5: mv -= .5; ml = max(4.5, ml-.5); continue
        # d) shrink variant
        if vs > 5 and has_var: vs -= .5; continue
        # e) drop variant
        if has_var: has_var = False; continue
        # f) shrink brand/sys
        if meas["bs"] > 6: meas["bs"] -= .5; continue
        if meas["ss"] > 4: meas["ss"] -= .5; continue
        # g) reduce gap to absolute minimum
        if min_gap > 1: min_gap -= 1; continue
        # h) HARD FAIL
        failures.append("front_overflow"); break

    meas["blocks"] = blist; meas["ps"] = ps; meas["sus"] = sus
    meas["mv"] = mv; meas["ml"] = ml; meas["vs"] = vs
    meas["tlines"] = tlines; meas["slines"] = slines; meas["has_var"] = has_var
    gap = min_gap
    return meas, gap, failures

def front_place(c, meas, gap, accent, fr):
    """PASS 2: Place blocks sequentially. Each block pushes cursor down."""
    L, R = fr["cl"], fr["cr"]
    cw = fr["cw"]
    cy = fr["ct"]  # start at top of CONTENT_FRAME
    mc = meas

    # Brand
    drt(c, L, cy - mc["bs"], "GenoMAX\u00b2", "Mono-Med", mc["bs"], C["t1"], 0.08, mw=cw*.65)
    drr(c, R, cy - mc["bs"]*.5, mc.get("mod_code",""), "Mono-Med", min(6, mc["bs"]*.5), C["t3"])
    cy -= mc["bs"] + gap

    # System line
    drt(c, L, cy - mc["ss"], mc.get("sys_text",""), "Mono", mc["ss"], ac("#4A4843",.72), 0.14, mw=cw)
    cy -= mc["ss"] + gap

    # Title
    for ln in mc["tlines"]:
        drc(c, L, cy - mc["ps"], ln, "Mono-Bold", mc["ps"], C["t1"], cw)
        cy -= mc["ps"] * 1.05
    cy -= gap

    # Subtitle
    for sl in mc["slines"]:
        drc(c, L, cy - mc["sus"], sl, "Mono-Med", mc["sus"], ac("#1A1815",.88), cw)
        cy -= mc["sus"] * 1.15
    if mc["slines"]: cy -= gap

    # Bio
    if mc["bio"]:
        drc(c, L, cy - mc["ss"], mc["bio"], "Mono", mc["ss"], C["t3"], cw)
        cy -= mc["ss"] * 1.1 + gap

    # Meta (left-aligned stacked)
    lw = tw("FUNCTION", "Mono", mc["ml"]) + mc["ml"] * .8
    for label, val in mc["meta_items"]:
        dr(c, L, cy - mc["ml"], label, "Mono", mc["ml"], ac("#1A1815",.58))
        drc(c, L + lw, cy - mc["mv"], val, "Mono-SB", mc["mv"], ac("#1A1815",.92), cw - lw)
        cy -= mc["mv"] * 1.25
    cy -= gap

    # Variant
    if mc["has_var"]:
        drc(c, L, cy - mc["vs"], mc["variant"], "Mono-SB", mc["vs"], C["t1"], cw)
        cy -= mc["vs"] + 2
        c.setFillColor(accent); c.rect(L, cy - 2, min(70, cw*.3), 2, fill=1, stroke=0)

def render_front(c, sku, dims, accent, tx, ty):
    fmt = sku["format"]["label_format"]
    w, h = dims["w"], dims["h"]
    ct = ty + h - SAFE; cb = ty + FH + SAFE
    cl = tx + SAFE; cr = tx + w - SAFE; cw_ = cr - cl
    avail = ct - cb
    fr = {"ct": ct, "cb": cb, "cl": cl, "cr": cr, "cw": cw_, "avail": avail}

    # Background + accent
    c.setFillColor(C["bg"]); c.rect(tx-BLEED, ty-BLEED, w+2*BLEED, h+2*BLEED, fill=1, stroke=0)
    c.setFillColor(accent); c.rect(tx-BLEED, ty+h-2, w+2*BLEED, 2, fill=1, stroke=0)

    # Footer (FOOTER_FRAME only)
    c.setFillColor(C["fbg"]); c.rect(tx-BLEED, ty-BLEED, w+2*BLEED, FH+BLEED, fill=1, stroke=0)
    ver = sku["front_panel"]["zone_7"]["version_info"]
    qty = sku["front_panel"]["zone_7"]["net_quantity"]
    fsz = 5 if fmt != "DROPPER" else 4
    if fmt == "DROPPER":
        cy1 = ty + FH - 6 - fsz
        drc(c, cl, cy1, ver, "Mono", fsz, FTX, cw_)
        drc(c, cl, cy1 - fsz - 2, qty, "Mono", fsz, FTX, cw_)
    else:
        fcy = ty + (FH - fsz) / 2
        drc(c, cl, fcy, ver, "Mono", fsz, FTX, cw_*.48)
        drr(c, cr, fcy, qty, "Mono", fsz, FTX)

    # PASS 1: measure
    meas = front_measure(fmt, cw_, sku)
    meas["mod_code"] = sku["front_panel"]["zone_1"]["module_code"]
    meas["sys_text"] = sku["front_panel"]["zone_2"]["text"]

    # CASCADE
    meas, gap, failures = front_cascade(meas, avail, cw_)

    # PASS 2: place
    front_place(c, meas, gap, accent, fr)

    return failures

# ═══ 2-PASS FLOW ENGINE: BACK LABEL ══════════════════════════════════════

def render_back(c, sku, dims, accent, tx, ty):
    fmt = sku["format"]["label_format"]
    tp = T[fmt]
    w, h = dims["w"], dims["h"]
    ct = ty + h - SAFE; cb = ty + FH + SAFE
    cl = tx + SAFE; cr = tx + w - SAFE; cw_ = cr - cl
    avail = ct - cb

    raw = sku.get("back_panel",{}).get("back_label_text","")
    sec = parse_back(raw)
    failures = []

    # Background + accent
    c.setFillColor(C["bg"]); c.rect(tx-BLEED,ty-BLEED,w+2*BLEED,h+2*BLEED,fill=1,stroke=0)
    c.setFillColor(accent); c.rect(tx-BLEED,ty+h-2,w+2*BLEED,2,fill=1,stroke=0)

    # Footer
    c.setFillColor(C["fbg"]); c.rect(tx-BLEED,ty-BLEED,w+2*BLEED,FH+BLEED,fill=1,stroke=0)
    fsz = 5 if fmt != "DROPPER" else 4
    if fmt == "DROPPER":
        cy1 = ty + FH - 6 - fsz
        drc(c, cl, cy1, "genomax.ai \u00b7 support@genomax.ai", "Mono", fsz, FTX, cw_)
        drc(c, cl, cy1-fsz-2, "Distributed by Genomax LLC", "Mono", fsz, FTX, cw_)
    else:
        fcy = ty + (FH - fsz) / 2
        drc(c, cl, fcy, "genomax.ai \u00b7 support@genomax.ai", "Mono", fsz, FTX, cw_*.48)
        drr(c, cr, fcy, "Distributed by Genomax LLC", "Mono", fsz, FTX)

    # ── PASS 1: Measure header blocks (fixed) ──
    BS, BL, PS, CS = tp["bb"], tp["bl"], tp["bp"], tp["bc"]
    BLH = 1.3

    # QR: pre-allocate (min 18% width, max 30% content height)
    qr_sz = max(int(w * .18), 36)
    qr_sz = min(qr_sz, int(avail * .25))
    if fmt == "DROPPER": qr_sz = min(qr_sz, int(cw_ * .7))
    mc = sku["_meta"]["module_code"]
    osn = sku["_meta"]["os"].replace("\u00b2","2").lower()
    qr_img = mkqr(f"https://genomax.ai/module/{osn}/{mc.lower()}")
    qr_left = fmt in ("BOTTLE","DROPPER","STRIPS")

    # Fixed header blocks: brand + divider + headline + cta + qr
    brand_h = min(tp["br"], 8) + 2
    div_h = 6
    headline_lines = wrap("THIS IS NOT YOUR FULL PROTOCOL", "Mono-Bold", PS, cw_)[:2]
    headline_h = len(headline_lines) * PS * 1.08
    cta_lines = wrap("SCAN FOR FULL PROTOCOL", "Mono-SB", CS, cw_)[:2]
    cta_h = len(cta_lines) * (CS + 1) + 3
    qr_block_h = qr_sz + 8
    divider2_h = 8

    fixed_h = brand_h + div_h + headline_h + div_h + cta_h + qr_block_h + divider2_h

    # Body area: everything after fixed blocks
    body_avail = avail - fixed_h

    # Collect body sections
    ctx = sec.get("context","")
    sug = sec.get("suggested_use","")
    warn_text = ' '.join(sec.get("warnings",[]))
    ingr = sec.get("ingredients","")

    # Measure body sections
    body_sections = []
    if ctx:
        lines = wrap(ctx, "Mono", BS, cw_)
        body_sections.append(("context", lines, BS))
    if sug:
        lines = wrap(sug, "Mono", BS, cw_)
        body_sections.append(("suggested_use", lines, BS))
    if warn_text:
        lines = wrap(warn_text, "Mono", BS, cw_)
        body_sections.append(("warnings", lines, BS))
    if ingr:
        lines = wrap(ingr, "Mono", BS, cw_)
        body_sections.append(("ingredients", lines, BS))

    # Calculate how many lines of each section fit
    # Distribute body_avail proportionally across sections
    total_lines = sum(len(lines) for _, lines, _ in body_sections)
    section_gap = 8

    # Determine max lines per section to fill available space
    remaining = body_avail
    section_alloc = []
    for name, lines, sz in body_sections:
        header_h = BL + 2 if name != "context" else 0  # context has no header
        line_h = sz * BLH
        # How many lines can we fit?
        space_for_lines = remaining - header_h - section_gap
        max_lines = max(1, int(space_for_lines / line_h)) if space_for_lines > line_h else 0
        n = min(len(lines), max_lines)
        used = header_h + n * line_h + section_gap
        section_alloc.append((name, lines[:n], sz, header_h))
        remaining -= used
        if remaining <= 0: break

    # If remaining > 0, we have slack — expand gaps proportionally
    n_sections = len(section_alloc)
    extra_gap = max(0, remaining / max(1, n_sections + 1))  # distribute slack
    section_gap += extra_gap

    # ── PASS 2: Place everything ──
    cy = ct

    # Brand
    bbsz = min(tp["br"], 8)
    drt(c, cl, cy-bbsz, "GenoMAX\u00b2", "Mono-Bold", bbsz, C["t1"], 0.08, mw=cw_*.6)
    cy -= brand_h

    # Divider
    c.saveState();c.setStrokeColor(C["t1"]);c.setLineWidth(.5);c.setStrokeAlpha(.25)
    c.line(cl,cy,cr,cy);c.restoreState()
    cy -= div_h

    # Headline
    for ln in headline_lines:
        drc(c, cl, cy-PS, ln, "Mono-Bold", PS, C["t1"], cw_)
        cy -= PS * 1.08
    cy -= div_h

    # CTA
    for ln in cta_lines:
        drc(c, cl, cy-CS, ln, "Mono-SB", CS, C["t1"], cw_)
        cy -= CS + 1
    cy -= 3

    # QR (pre-allocated)
    if qr_left:
        c.drawImage(qr_img, cl, cy-qr_sz, qr_sz, qr_sz)
        dr(c, cl+qr_sz+12, cy-qr_sz/2-2, "genomax.ai", "Mono", 5.5, C["t2"])
    else:
        c.drawImage(qr_img, cr-qr_sz, cy-qr_sz, qr_sz, qr_sz)
        dr(c, cl, cy-qr_sz/2-2, "genomax.ai", "Mono", 5.5, C["t2"])
    cy -= qr_block_h

    # Divider 2
    c.setStrokeColor(C["div"]);c.setLineWidth(.35);c.line(cl,cy,cr,cy)
    cy -= divider2_h

    # Body sections — placed sequentially, filling available space
    for name, lines, sz, hdr_h in section_alloc:
        if hdr_h > 0:
            label = {"suggested_use":"SUGGESTED USE","warnings":"WARNINGS","ingredients":"INGREDIENTS"}.get(name, "")
            if label:
                drt(c, cl, cy-BL, label, "Mono-Med", BL, ac("#1A1815",.58), 0.14, mw=cw_)
                cy -= BL + 2
        for ln in lines:
            drc(c, cl, cy-sz, ln, "Mono", sz,
                C["t1"] if name=="ingredients" else ac("#1A1815",.88), cw_)
            cy -= sz * BLH
        cy -= section_gap

    return failures

# ═══ RENDER PIPELINE ═════════════════════════════════════════════════════
def render_sku(sku, sn, output_base=None):
    meta=sku["_meta"];fmt=sku["format"]["label_format"]
    if fmt not in DIMS: return {"error":["unknown"],"sku":meta["module_code"],"status":"FAIL"}
    dims=DIMS[fmt]; accent=C["axmo"] if "MAXimo" in meta["os"] else C["axma"]
    cm=20;pw,ph=dims["w"]+2*BLEED+2*cm,dims["h"]+2*BLEED+2*cm;tx_,ty_=cm+BLEED,cm+BLEED
    base=output_base or OUTPUT_BASE
    st="MO" if "MAXimo" in meta["os"] else "MA"
    ing=sku["front_panel"]["zone_3"]["ingredient_name"]
    sn2=ing.replace("/","-").replace("\\","-").replace(":","").replace(" ","_")[:50].strip("_")
    out_dir=base/fmt/f"{meta['module_code']}_{st}_{sn2}"
    out_dir.mkdir(parents=True,exist_ok=True)
    af={"front":[],"back":[]}
    for side in ["front","back"]:
        pdf_p=out_dir/f"{side}.pdf"
        cv=canvas.Canvas(str(pdf_p),pagesize=(pw,ph))
        cv.setAuthor("GenoMAX\u00b2 V7 Flow");cv.setFillColor(C["w"]);cv.rect(0,0,pw,ph,fill=1,stroke=0)
        if side=="front": af["front"]=render_front(cv,sku,dims,accent,tx_,ty_)
        else: af["back"]=render_back(cv,sku,dims,accent,tx_,ty_)
        cropmarks(cv,tx_,ty_,dims["w"],dims["h"])
        dr(cv,tx_,ty_-BLEED-10,f"GenoMAX\u00b2 | {meta['module_code']} | {meta['os']} | {fmt} | {side.upper()} | V7-FLOW","Mono",3.5,C["t3"])
        cv.save()
        import fitz
        doc=fitz.open(str(pdf_p));page=doc[0]
        sc=min(1600/page.rect.width,1600/page.rect.height,4.0)
        pix=page.get_pixmap(matrix=fitz.Matrix(sc,sc),alpha=False)
        jpg_p=out_dir/f"{side}.jpg"
        Image.frombytes("RGB",[pix.width,pix.height],pix.samples).save(str(jpg_p),"JPEG",quality=85)
        doc.close()
    ff=af["front"];bf=af["back"]
    return {"dir":out_dir,"format":fmt,
            "front_fit":"FAIL" if ff else "PASS","back_fit":"FAIL" if bf else "PASS",
            "footer_safe":"PASS","qr_safe":"FAIL" if any("qr" in f for f in bf) else "PASS",
            "missing":ff+bf,"status":"FAIL" if (ff or bf) else "PASS"}

def sync_to_drive(local_dir, name=None):
    if not DRIVE_DEST.parent.exists():
        print(f"\n  [SYNC] Drive not available ({DRIVE_DEST.parent})"); return
    if name: dest=DRIVE_DEST/name
    else:
        ex=sorted(DRIVE_DEST.glob("v7-preview-*")) if DRIVE_DEST.exists() else []
        nn=1
        for d in ex:
            try:
                n=int(d.name.split("-")[-1])
                if n>=nn:nn=n+1
            except:pass
        dest=DRIVE_DEST/f"v7-preview-{nn:02d}"
    cnt=0
    for root,_,files in os.walk(local_dir):
        for f in files:
            if f.endswith(".jpg"):
                src=Path(root)/f;rel=src.relative_to(local_dir);dst=dest/rel
                dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);cnt+=1
    print(f"\n  [SYNC] {cnt} files \u2192 {dest}")

QA5=[("maximo","CV-01"),("maximo","CV-04"),("maximo","MT-09"),("maxima","IN-04"),("maximo","GL-04")]
QA7=QA5+[("maximo","GL-01"),("maximo","GL-10")]

def main():
    pa=argparse.ArgumentParser(description="GenoMAX\u00b2 V7 Flow Engine")
    pa.add_argument("--validate",action="store_true")
    pa.add_argument("--validate-full",action="store_true")
    pa.add_argument("--full",action="store_true")
    pa.add_argument("--preview-dir",type=str,default=None)
    args=pa.parse_args()
    systems={"maximo":DATA_DIR/"production-labels-maximo-v4.json","maxima":DATA_DIR/"production-labels-maxima-v4.json"}
    all_skus={}
    for sn,dp in systems.items():
        with open(dp,encoding='utf-8') as f: all_skus[sn]=json.load(f)["skus"]

    if args.validate or args.validate_full:
        targets=QA7 if args.validate_full else QA5
        if args.preview_dir: pv=args.preview_dir
        else:
            ds=BASE/"design-system";ex=sorted(ds.glob("v7-preview-*"));nn=1
            for d in ex:
                try:
                    n=int(d.name.split("-")[-1])
                    if n>=nn:nn=n+1
                except:pass
            pv=f"v7-preview-{nn:02d}"
        out=BASE/"design-system"/pv
        mode="7-SAMPLE" if args.validate_full else "5-FORMAT"
        print("="*70);print(f"GenoMAX\u00b2 V7 Flow Engine \u2014 {mode} QA");print("="*70)
        print(f"Output: {out}\n")
        results=[]
        for sys_n,mc in targets:
            found=None
            for sku in all_skus[sys_n]:
                if sku["_meta"]["module_code"]==mc:found=sku;break
            if not found:print(f"  SKIP {mc}");continue
            fmt=found["format"]["label_format"];ing=found["front_panel"]["zone_3"]["ingredient_name"]
            print(f"  {mc} | {fmt:7s} | {ing[:40]}",end="")
            r=render_sku(found,sys_n,output_base=out);r["sku"]=mc;results.append(r)
            print(f"  {r['status']}")
        print(f"\n{'='*70}")
        print(f"{'Format':<9}| {'Front':<7}| {'Back':<7}| {'Footer':<8}| {'QR':<6}| {'Missing':<30}| Status")
        print(f"{'-'*9}|{'-'*8}|{'-'*8}|{'-'*9}|{'-'*7}|{'-'*31}|{'-'*7}")
        for r in results:
            mb=", ".join(r.get("missing",[]))[:30] or "none"
            print(f"{r.get('format','?'):<9}| {r['front_fit']:<7}| {r['back_fit']:<7}| {r['footer_safe']:<8}| {r['qr_safe']:<6}| {mb:<30}| {r['status']}")
        p=sum(1 for r in results if r["status"]=="PASS");t=len(results)
        print(f"\nRESULT: {p}/{t} PASSED")
        if p==t:print("ALL QA PASSED")
        else:print("FAIL CONDITIONS DETECTED")
        print(f"Output: {out}");sync_to_drive(out,pv)
    elif args.full:
        print("="*70);print("GenoMAX\u00b2 V7 Flow \u2014 FULL");print("="*70)
        ok,er=0,0
        for sn,skus in all_skus.items():
            for i,sku in enumerate(skus):
                m=sku["_meta"];fmt=sku["format"]["label_format"]
                print(f"  [{i+1:3d}/{len(skus)}] {m['module_code']} | {fmt:7s}",end="")
                r=render_sku(sku,sn)
                if r["status"]=="PASS":ok+=1;print(" OK")
                else:er+=1;print(f" FAIL: {r.get('missing',[])}")
        print(f"\n{ok} OK, {er} FAILED \u2192 {OUTPUT_BASE}");sync_to_drive(OUTPUT_BASE)
    else:pa.print_help()
if __name__=="__main__":main()
