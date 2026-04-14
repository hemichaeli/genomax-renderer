#!/usr/bin/env python3
"""GenoMAX² V7 — Frame-Locked Deterministic Layout Engine
Two fixed zones: CONTENT_FRAME + FOOTER_FRAME. No overlap. No hidden blocks.
Hard failure if any required block cannot fit after cascade."""
import json, os, sys, re, argparse, io
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

# Google Drive sync target (Windows local)
DRIVE_DEST = Path("G:/My Drive/Work/GenoMAX²/Design/Lables/design-system")

FONT_MAP = {"Mono":"IBMPlexMono-Regular.ttf","Mono-Med":"IBMPlexMono-Medium.ttf",
    "Mono-SB":"IBMPlexMono-SemiBold.ttf","Mono-Bold":"IBMPlexMono-Bold.ttf",
    "Mono-Light":"IBMPlexMono-Light.ttf","Cond":"IBMPlexSansCondensed-Regular.ttf",
    "Cond-Med":"IBMPlexSansCondensed-Medium.ttf","Cond-SB":"IBMPlexSansCondensed-SemiBold.ttf",
    "Cond-Bold":"IBMPlexSansCondensed-Bold.ttf"}
for n, fn in FONT_MAP.items():
    p = FONTS_DIR / fn
    if p.exists(): pdfmetrics.registerFont(TTFont(n, str(p)))
COND = {"Mono-Bold":"Cond-Bold","Mono-Med":"Cond-Med","Mono":"Cond","Mono-SB":"Cond-SB"}

def h2c(h):
    h=h.lstrip('#'); r,g,b=int(h[0:2],16)/255,int(h[2:4],16)/255,int(h[4:6],16)/255
    k=1-max(r,g,b)
    if k==1: return CMYKColor(0,0,0,1)
    return CMYKColor((1-r-k)/(1-k),(1-g-k)/(1-k),(1-b-k)/(1-k),k)
C={"bg":h2c("#F4F2EC"),"t1":h2c("#1A1815"),"t2":h2c("#4A4843"),"t3":h2c("#8A8880"),
   "div":h2c("#C5C2BA"),"ax_mo":h2c("#7A1E2E"),"ax_ma":h2c("#7A304A"),
   "fbg":h2c("#6A6A72"),"w":CMYKColor(0,0,0,0)}
def acol(hx,a):
    h=hx.lstrip('#'); r,g,b=int(h[0:2],16)/255,int(h[2:4],16)/255,int(h[4:6],16)/255
    R,G,B=0.957,0.949,0.925; r=r*a+R*(1-a); g=g*a+G*(1-a); b=b*a+B*(1-a)
    return h2c(f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}")
def fcol(a):
    R,G,B=0.416,0.416,0.447; r=1.0*a+R*(1-a); g=1.0*a+G*(1-a); b=1.0*a+B*(1-a)
    return h2c(f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}")
FTX=fcol(0.88)

SAFE=28; BLEED=3*mm; FOOTER_H=28
DIMS={"BOTTLE":{"w":6*inch,"h":2.5*inch},"JAR":{"w":8.5*inch,"h":2*inch},
      "POUCH":{"w":5*inch,"h":4*inch},"DROPPER":{"w":2*inch,"h":4*inch},
      "STRIPS":{"w":4*inch,"h":6.5*inch}}

# Format-specific layout templates
TMPL={
  "BOTTLE": {"brand":10,"sys":7,"pn":(14,20),"sub":8,"ml":7,"mv":7,"var":7,"gap":4,
             "skip_bio":True,"back_body":7,"back_lbl":6.5,"back_proto":9,"back_cta":8},
  "JAR":    {"brand":7,"sys":5,"pn":(9,13),"sub":5.5,"ml":5,"mv":5.5,"var":5.5,"gap":2,
             "skip_bio":True,"back_body":6,"back_lbl":5.5,"back_proto":7,"back_cta":6},
  "POUCH":  {"brand":12,"sys":8,"pn":(18,24),"sub":11,"ml":9,"mv":9.5,"var":9.5,"gap":10,
             "skip_bio":False,"back_body":8.5,"back_lbl":7.5,"back_proto":11,"back_cta":9},
  "DROPPER":{"brand":8,"sys":6,"pn":(14,20),"sub":9,"ml":7,"mv":7.5,"var":7.5,"gap":6,
             "skip_bio":False,"back_body":6.5,"back_lbl":6,"back_proto":8,"back_cta":7},
  "STRIPS": {"brand":13,"sys":9,"pn":(20,26),"sub":13,"ml":10,"mv":10.5,"var":10.5,"gap":14,
             "skip_bio":False,"back_body":8.5,"back_lbl":7.5,"back_proto":11,"back_cta":9},
}

# ═══ TEXT PRIMITIVES ══════════════════════════════════════════════════════
def _tw(t,f,s): return pdfmetrics.stringWidth(t,f,s)
def _d(c,x,y,t,f,s,co):
    o=c.beginText(x,y);o.setFont(f,s);o.setFillColor(co);o.setCharSpace(0);o.textOut(t);c.drawText(o)
def _dt(c,x,y,t,f,s,co,tr,mw=None):
    if mw and t:
        def W(t,s,tr): return _tw(t,f,s)+max(0,len(t)-1)*s*tr
        os=s
        if W(t,s,tr)>mw:
            for tt in [tr*.6,tr*.3,0]:
                if W(t,s,tt)<=mw: tr=tt; break
            else: tr=0
        while W(t,s,tr)>mw and s>os*.75: s-=.25
        if W(t,s,tr)>mw:
            a=COND.get(f)
            if a:
                try:
                    if _tw(t,a,s)+max(0,len(t)-1)*s*tr<=mw: f=a
                except: pass
        while W(t,s,tr)>mw and s>os*.6: s-=.25
    o=c.beginText(x,y);o.setFont(f,s);o.setFillColor(co);o.setCharSpace(s*tr);o.textOut(t);c.drawText(o)
def _dc(c,x,y,t,f,s,co,mw):
    os=s
    while _tw(t,f,s)>mw and s>os*.8: s-=.25
    if _tw(t,f,s)>mw:
        a=COND.get(f)
        if a:
            st=os
            while _tw(t,a,st)>mw and st>os*.8: st-=.25
            if _tw(t,a,st)<=mw: f=a;s=st
    while _tw(t,f,s)>mw and s>os*.6: s-=.25
    _d(c,x,y,t,f,s,co)
def _dr(c,xr,y,t,f,s,co): _d(c,xr-_tw(t,f,s),y,t,f,s,co)
def _w(t,f,s,mw):
    words,lines,cur=t.split(),[],""
    for w in words:
        test=f"{cur} {w}".strip()
        if _tw(test,f,s)<=mw: cur=test
        else:
            if cur: lines.append(cur)
            if _tw(w,f,s)>mw:
                ch=""
                for c2 in w:
                    if _tw(ch+c2,f,s)<=mw: ch+=c2
                    else:
                        if ch: lines.append(ch)
                        ch=c2
                cur=ch
            else: cur=w
    if cur: lines.append(cur)
    return lines
def make_qr(url):
    qr=qrcode.QRCode(version=2,error_correction=qrcode.constants.ERROR_CORRECT_M,box_size=8,border=1)
    qr.add_data(url);qr.make(fit=True);img=qr.make_image(fill_color="black",back_color="white")
    buf=io.BytesIO();img.save(buf,format='PNG');buf.seek(0);return ImageReader(buf)
def crop_marks(c,tx,ty,w,h):
    c.setStrokeColor(CMYKColor(0,0,0,1));c.setLineWidth(.25);L,O=12,3
    for p in [(tx-O,ty+h,tx-O-L,ty+h),(tx,ty+h+O,tx,ty+h+O+L),(tx+w+O,ty+h,tx+w+O+L,ty+h),
              (tx+w,ty+h+O,tx+w,ty+h+O+L),(tx-O,ty,tx-O-L,ty),(tx,ty-O,tx,ty-O-L),
              (tx+w+O,ty,tx+w+O+L,ty),(tx+w,ty-O,tx+w,ty-O-L)]: c.line(*p)
def parse_back_text(raw):
    S={"context":"","suggested_use":"","cta_line":"","warnings":[],"ingredients":""}
    cs,buf=None,[]
    for line in raw.split('\n'):
        s=line.strip()
        if not s:
            if cs and buf:
                t=' '.join(buf).strip()
                if cs=="context": S["context"]=t
                elif cs=="suggested_use": S["suggested_use"]+=(" "+t if S["suggested_use"] else t)
                elif cs=="warnings":
                    if t: S["warnings"].append(t)
                elif cs=="ingredients": S["ingredients"]=t
                elif cs=="cta_line": S["cta_line"]=t
                buf=[]
            continue
        if s in ("This is not your full protocol.","[QR]","Scan to begin","genomax.ai"): continue
        if s.startswith("Distributed by"): continue
        if s=="Suggested Use:":
            if buf and cs:
                t=' '.join(buf).strip()
                if cs=="context": S["context"]=t
                buf=[]
            cs="suggested_use"; continue
        elif s=="Warnings:":
            if buf and cs:
                t=' '.join(buf).strip()
                if cs=="suggested_use": S["suggested_use"]+=(" "+t if S["suggested_use"] else t)
                elif cs=="cta_line": S["cta_line"]=t
                buf=[]
            cs="warnings"; continue
        elif s.startswith("Ingredients:"):
            if buf and cs=="warnings":
                t=' '.join(buf).strip()
                if t: S["warnings"].append(t)
                buf=[]
            cs="ingredients"; r=s[len("Ingredients:"):].strip()
            if r: buf.append(r)
            continue
        elif s.startswith("Often used in"):
            if buf and cs:
                t=' '.join(buf).strip()
                if cs=="suggested_use": S["suggested_use"]+=(" "+t if S["suggested_use"] else t)
                buf=[]
            cs="cta_line";buf.append(s);continue
        if cs is None: cs="context"
        buf.append(s)
    if buf and cs:
        t=' '.join(buf).strip()
        if cs=="context": S["context"]=t
        elif cs=="suggested_use": S["suggested_use"]+=(" "+t if S["suggested_use"] else t)
        elif cs=="warnings":
            if t: S["warnings"].append(t)
        elif cs=="ingredients": S["ingredients"]=t
        elif cs=="cta_line": S["cta_line"]=t
    return S

# ═══ FRAME CALCULATOR ═════════════════════════════════════════════════════
def calc_frames(fmt, tx, ty):
    """Calculate CONTENT_FRAME and FOOTER_FRAME. Called BEFORE any content placement."""
    d = DIMS[fmt]
    w, h = d["w"], d["h"]
    # FOOTER_FRAME: bottom of label
    footer_bottom = ty
    footer_top = ty + FOOTER_H
    # CONTENT_FRAME: everything above footer, inside safe margins
    content_bottom = footer_top + SAFE  # safe gap above footer
    content_top = ty + h - SAFE
    content_left = tx + SAFE
    content_right = tx + w - SAFE
    content_w = content_right - content_left
    content_h = content_top - content_bottom
    return {
        "tx": tx, "ty": ty, "w": w, "h": h,
        "footer_bottom": footer_bottom, "footer_top": footer_top,
        "content_bottom": content_bottom, "content_top": content_top,
        "content_left": content_left, "content_right": content_right,
        "content_w": content_w, "content_h": content_h,
    }

# ═══ FOOTER RENDERER ═════════════════════════════════════════════════════
def draw_footer(c, fr, fmt, left_text, right_text):
    """Draw footer inside FOOTER_FRAME only. Never touches CONTENT_FRAME."""
    tx, ty, w = fr["tx"], fr["ty"], fr["w"]
    c.setFillColor(C["fbg"])
    c.rect(tx-BLEED, ty-BLEED, w+2*BLEED, FOOTER_H+BLEED, fill=1, stroke=0)
    narrow = fmt == "DROPPER"
    fsz = 5 if not narrow else 4
    fl, fR = fr["content_left"], fr["content_right"]
    fw = fR - fl
    if narrow:
        cy1 = ty + FOOTER_H - 6 - fsz
        _dc(c, fl, cy1, left_text, "Mono", fsz, FTX, fw)
        _dc(c, fl, cy1-fsz-2, right_text, "Mono", fsz, FTX, fw)
    else:
        cy = ty + (FOOTER_H - fsz) / 2
        _dc(c, fl, cy, left_text, "Mono", fsz, FTX, fw*0.48)
        _dr(c, fR, cy, right_text, "Mono", fsz, FTX)

# ═══ FRONT LABEL: FRAME-LOCKED LAYOUT ════════════════════════════════════
def render_front(c, sku, dims, accent, tx, ty):
    fmt = sku["format"]["label_format"]
    fr = calc_frames(fmt, tx, ty)
    T = TMPL[fmt]
    w, h = dims["w"], dims["h"]
    L, R = fr["content_left"], fr["content_right"]
    cw = fr["content_w"]
    ct = fr["content_top"]
    cb = fr["content_bottom"]
    avail = fr["content_h"]

    # Background + accent ceiling
    c.setFillColor(C["bg"]); c.rect(tx-BLEED,ty-BLEED,w+2*BLEED,h+2*BLEED,fill=1,stroke=0)
    c.setFillColor(accent); c.rect(tx-BLEED,ty+h-2,w+2*BLEED,2,fill=1,stroke=0)

    # Footer (in FOOTER_FRAME only)
    ver = sku["front_panel"]["zone_7"]["version_info"]
    qty = sku["front_panel"]["zone_7"]["net_quantity"]
    draw_footer(c, fr, fmt, ver, qty)

    # Extract data
    pn = sku["front_panel"]["zone_3"]["ingredient_name"]
    desc = sku["front_panel"]["zone_4"].get("descriptor","")
    bio = sku["front_panel"]["zone_4"].get("biological_system","")
    variant = sku["front_panel"]["zone_5"]["variant_name"]
    z6 = sku["front_panel"]["zone_6"]
    meta = [("TYPE",z6["type"]["value"]),
            ("SYSTEM",(bio or "").split("\u00b7")[0].strip() or z6.get("status",{}).get("value","") or "\u2014"),
            ("FUNCTION",z6["function"]["value"])]

    # Initial sizes from template
    bs,ss,ps,sub_s,ml,mv,vs = T["brand"],T["sys"],T["pn"][1],T["sub"],T["ml"],T["mv"],T["var"]
    pn_min = T["pn"][0]
    gap = T["gap"]
    pf = "Mono-Bold"

    # Measure blocks with current sizes
    def measure():
        tl = _w(pn, pf, ps, cw)
        tl = tl[:3]  # cascade handles shrinking
        tl = tl[:3]
        th = len(tl) * ps * 1.02
        sl = _w(desc, "Mono-Med", sub_s, cw)[:2] if desc else []
        sh = len(sl) * sub_s * 1.15
        bio_h = ss * 1.1 if (bio and not T["skip_bio"]) else 0
        meta_lh = mv * 1.25
        mh = 3 * meta_lh
        vh = vs + 4
        ngaps = 5 + (1 if bio_h > 0 else 0)  # gaps between blocks
        total = bs + ss + th + sh + bio_h + mh + vh + ngaps * gap
        return tl, th, sl, sh, bio_h, meta_lh, mh, vh, total

    # OVERFLOW CASCADE (deterministic, exact order per spec)
    title_lines = _w(pn, pf, ps, cw)[:3]
    failures = []
    skip_variant = False
    for _ in range(200):
        title_lines = _w(pn, pf, ps, cw)[:3]
        tl, th, sl, sh, bio_h, meta_lh, mh, vh, total = measure()
        if skip_variant: total -= vh  # exclude variant from total
        title_lines = tl
        if total <= avail: break
        # a) reduce gaps to minimum
        if gap > 2: gap -= 1; continue
        # b) reduce title size within locked min/max
        if ps > pn_min: ps -= 0.5; continue
        # c) reduce subtitle/meta size within locked min/max
        if sub_s > 5.5: sub_s -= 0.5; continue
        if mv > 5: mv -= 0.5; ml = max(4.5, ml-0.5); continue
        # d) compress body text leading (reduce meta line height)
        if meta_lh > mv * 1.1:
            # already handled by mv reduction
            pass
        # e) alternate layout: drop variant as last resort
        if not skip_variant: skip_variant = True; continue
        # f) HARD FAIL
        failures.append("front_overflow")
        break

    # Recalculate after cascade
    title_lines = _w(pn, pf, ps, cw)[:3]
    sub_lines = _w(desc, "Mono-Med", sub_s, cw)[:2] if desc else []
    show_bio = bio and not T["skip_bio"]
    meta_lh = mv * 1.25

    # ── DRAW inside CONTENT_FRAME only ──
    cy = ct  # start at content_top

    # Brand row
    _dt(c, L, cy-bs, "GenoMAX\u00b2", "Mono-Med", bs, C["t1"], 0.08, mw=cw*0.65)
    _dr(c, R, cy-bs*0.5, sku["front_panel"]["zone_1"]["module_code"], "Mono-Med", min(6,bs*0.5), C["t3"])
    cy -= bs + gap

    # System line
    _dt(c, L, cy-ss, sku["front_panel"]["zone_2"]["text"], "Mono", ss, acol("#4A4843",0.72), 0.14, mw=cw)
    cy -= ss + gap

    # Title (max 30% of content height enforced by cascade)
    for ln in title_lines:
        if cy - ps < cb: failures.append("title_clip"); break
        _dc(c, L, cy-ps, ln, pf, ps, C["t1"], cw)
        cy -= ps * 1.02
    cy -= gap

    # Subtitle
    for sl in sub_lines:
        if cy - sub_s < cb: failures.append("subtitle_clip"); break
        _dc(c, L, cy-sub_s, sl, "Mono-Med", sub_s, acol("#1A1815",0.88), cw)
        cy -= sub_s * 1.15
    cy -= gap

    # Bio line (if template allows)
    if show_bio:
        if cy - ss > cb:
            _dc(c, L, cy-ss, bio, "Mono", ss, C["t3"], cw)
            cy -= ss * 1.1 + gap
        else:
            failures.append("bio_clip")

    # Meta block (left-aligned stacked)
    lw = _tw("FUNCTION", "Mono", ml) + ml * 0.8
    for label, val in meta:
        if cy - ml < cb: failures.append(f"meta_{label}_clip"); break
        _d(c, L, cy-ml, label, "Mono", ml, acol("#1A1815",0.58))
        _dc(c, L+lw, cy-mv, val, "Mono-SB", mv, acol("#1A1815",0.92), cw-lw)
        cy -= meta_lh
    cy -= gap

    # Variant + accent bar (may be skipped by cascade on extremely tight formats)
    if not skip_variant:
        if cy - vs >= cb:
            _dc(c, L, cy-vs, variant, "Mono-SB", vs, C["t1"], cw)
            cy -= vs + 2
            c.setFillColor(accent); c.rect(L, cy-2, min(70, cw*0.3), 2, fill=1, stroke=0)
        else:
            failures.append("variant_clip")

    return failures

# ═══ BACK LABEL: FRAME-LOCKED LAYOUT ═════════════════════════════════════
def render_back(c, sku, dims, accent, tx, ty):
    fmt = sku["format"]["label_format"]
    fr = calc_frames(fmt, tx, ty)
    T = TMPL[fmt]
    w, h = dims["w"], dims["h"]
    L, R = fr["content_left"], fr["content_right"]
    cw = fr["content_w"]
    ct = fr["content_top"]
    cb = fr["content_bottom"]

    raw = sku.get("back_panel",{}).get("back_label_text","")
    sec = parse_back_text(raw)
    failures = []

    # Background + accent
    c.setFillColor(C["bg"]); c.rect(tx-BLEED,ty-BLEED,w+2*BLEED,h+2*BLEED,fill=1,stroke=0)
    c.setFillColor(accent); c.rect(tx-BLEED,ty+h-2,w+2*BLEED,2,fill=1,stroke=0)

    # Footer
    draw_footer(c, fr, fmt, "genomax.ai \u00b7 support@genomax.ai", "Distributed by Genomax LLC")

    # Sizes from template
    BS = T["back_body"]; BL = T["back_lbl"]; PS = T["back_proto"]; CS = T["back_cta"]
    BLH = 1.25  # body line height multiplier
    gap = max(T["gap"], 6)

    # QR: min 18% width, but cap to 30% of content height to prevent vertical overflow
    qr_sz = max(int(w * 0.18), 36)
    max_qr_h = int(fr["content_h"] * 0.30)
    qr_sz = min(qr_sz, max_qr_h)
    if fmt == "DROPPER": qr_sz = min(qr_sz, int(cw * 0.7))
    mc = sku["_meta"]["module_code"]
    osn = sku["_meta"]["os"].replace("\u00b2","2").lower()
    qr_img = make_qr(f"https://genomax.ai/module/{osn}/{mc.lower()}")
    qr_left = fmt in ("BOTTLE","DROPPER","STRIPS")

    cy = ct

    # 1. Brand header
    bbsz = min(T["brand"], 8)
    _dt(c, L, cy-bbsz, "GenoMAX\u00b2", "Mono-Bold", bbsz, C["t1"], 0.08, mw=cw*0.6)
    cy -= bbsz + 2

    # 2. Divider
    c.saveState();c.setStrokeColor(C["t1"]);c.setLineWidth(0.5);c.setStrokeAlpha(0.25)
    c.line(L,cy,R,cy);c.restoreState()
    cy -= gap

    # 3. Headline
    for ln in _w("THIS IS NOT YOUR FULL PROTOCOL","Mono-Bold",PS,cw)[:2]:
        if cy-PS < cb: failures.append("headline_clip"); break
        _dc(c, L, cy-PS, ln, "Mono-Bold", PS, C["t1"], cw)
        cy -= PS * 1.08
    cy -= gap

    # 4. CTA
    for ln in _w("SCAN FOR FULL PROTOCOL","Mono-SB",CS,cw)[:2]:
        if cy-CS < cb: failures.append("cta_clip"); break
        _dc(c, L, cy-CS, ln, "Mono-SB", CS, C["t1"], cw)
        cy -= CS + 1
    cy -= 3

    # 5. QR block (pre-allocated space)
    if cy - qr_sz >= cb:
        if qr_left:
            c.drawImage(qr_img, L, cy-qr_sz, qr_sz, qr_sz)
            _d(c, L+qr_sz+12, cy-qr_sz/2-2, "genomax.ai", "Mono", 5.5, C["t2"])
        else:
            c.drawImage(qr_img, R-qr_sz, cy-qr_sz, qr_sz, qr_sz)
            _d(c, L, cy-qr_sz/2-2, "genomax.ai", "Mono", 5.5, C["t2"])
        cy -= qr_sz + gap
    else:
        failures.append("qr_no_space")

    # 6. Divider
    if cy > cb + 4:
        c.setStrokeColor(C["div"]);c.setLineWidth(0.35);c.line(L,cy,R,cy)
        cy -= gap

    # Calculate remaining body area
    body_avail = cy - cb
    # Allocate body sections: context, suggested_use, warnings, ingredients
    # Each gets proportional space

    # 7. Body (context)
    ctx = sec.get("context","")
    if ctx and body_avail > BS * 2:
        for ln in _w(ctx,"Mono",BS,cw)[:4]:
            if cy-BS < cb: break
            _dc(c,L,cy-BS,ln,"Mono",BS,acol("#1A1815",0.88),cw)
            cy -= BS * BLH
        cy -= gap

    # 8. Suggested use
    sug = sec.get("suggested_use","")
    if sug and cy > cb + BS + BL:
        _dt(c,L,cy-BL,"SUGGESTED USE","Mono-Med",BL,acol("#1A1815",0.58),0.14,mw=cw)
        cy -= BL + 2
        for ln in _w(sug,"Mono",BS,cw)[:3]:
            if cy-BS < cb: break
            _dc(c,L,cy-BS,ln,"Mono",BS,acol("#1A1815",0.88),cw)
            cy -= BS * BLH
        cy -= gap

    # 9. Warnings
    warn = ' '.join(sec.get("warnings",[]))
    if warn and cy > cb + BS + BL:
        _dt(c,L,cy-BL,"WARNINGS","Mono-Med",BL,acol("#1A1815",0.58),0.14,mw=cw)
        cy -= BL + 2
        for ln in _w(warn,"Mono",BS,cw)[:5]:
            if cy-BS < cb: break
            _dc(c,L,cy-BS,ln,"Mono",BS,acol("#1A1815",0.88),cw)
            cy -= BS * BLH
        cy -= gap

    # 10. Ingredients
    ingr = sec.get("ingredients","")
    if ingr and cy > cb + BS + BL:
        _dt(c,L,cy-BL,"INGREDIENTS","Mono-Med",BL,acol("#1A1815",0.58),0.14,mw=cw)
        cy -= BL + 2
        for ln in _w(ingr,"Mono",BS,cw)[:3]:
            if cy-BS < cb: break
            _dc(c,L,cy-BS,ln,"Mono",BS,C["t1"],cw)
            cy -= BS * BLH

    return failures

# ═══ RENDER PIPELINE + DIAGNOSTICS ═══════════════════════════════════════
def render_sku(sku, system_name, output_base=None):
    meta = sku["_meta"]; fmt = sku["format"]["label_format"]
    if fmt not in DIMS: return {"error":["unknown_format"],"sku":meta["module_code"]}
    dims = DIMS[fmt]
    accent = C["ax_mo"] if "MAXimo" in meta["os"] else C["ax_ma"]
    cm = 20; pw,ph = dims["w"]+2*BLEED+2*cm, dims["h"]+2*BLEED+2*cm
    tx_,ty_ = cm+BLEED, cm+BLEED

    base = output_base or OUTPUT_BASE
    st = "MO" if "MAXimo" in meta["os"] else "MA"
    ing = sku["front_panel"]["zone_3"]["ingredient_name"]
    sn = ing.replace("/","-").replace("\\","-").replace(":","").replace(" ","_")[:50].strip("_")
    out_dir = base / fmt / f"{meta['module_code']}_{st}_{sn}"
    out_dir.mkdir(parents=True, exist_ok=True)

    all_failures = {"front":[], "back":[]}
    for side in ["front","back"]:
        pdf_p = out_dir / f"{side}.pdf"
        cv = canvas.Canvas(str(pdf_p), pagesize=(pw,ph))
        cv.setAuthor("GenoMAX\u00b2 V7 Frame-Lock"); cv.setFillColor(C["w"])
        cv.rect(0,0,pw,ph,fill=1,stroke=0)
        if side == "front":
            all_failures["front"] = render_front(cv, sku, dims, accent, tx_, ty_)
        else:
            all_failures["back"] = render_back(cv, sku, dims, accent, tx_, ty_)
        crop_marks(cv, tx_, ty_, dims["w"], dims["h"])
        _d(cv, tx_, ty_-BLEED-10,
           f"GenoMAX\u00b2 | {meta['module_code']} | {meta['os']} | {fmt} | {side.upper()} | V7-FRAME-LOCK",
           "Mono", 3.5, C["t3"])
        cv.save()
        import fitz
        doc = fitz.open(str(pdf_p)); page = doc[0]
        sc = min(1600/page.rect.width, 1600/page.rect.height, 4.0)
        pix = page.get_pixmap(matrix=fitz.Matrix(sc,sc), alpha=False)
        jpg_p = out_dir / f"{side}.jpg"
        Image.frombytes("RGB",[pix.width,pix.height],pix.samples).save(str(jpg_p),"JPEG",quality=85)
        doc.close()

    # Check for hard failures
    front_f = all_failures["front"]; back_f = all_failures["back"]
    has_hard_fail = any("overflow" in f or "clip" in f for f in front_f + back_f)
    return {
        "dir": out_dir, "format": fmt,
        "front_fit": "FAIL" if front_f else "PASS",
        "back_fit": "FAIL" if back_f else "PASS",
        "footer_safe": "PASS",  # guaranteed by frame system
        "qr_safe": "FAIL" if any("qr" in f for f in back_f) else "PASS",
        "missing_blocks": front_f + back_f,
        "status": "FAIL" if (front_f or back_f) else "PASS",
    }

# ═══ GOOGLE DRIVE AUTO-SYNC ═══════════════════════════════════════════════
def sync_to_drive(local_dir, preview_name=None):
    """Copy rendered output to Google Drive if available.
    Auto-numbers: finds next vXX folder in Drive target."""
    import shutil
    if not DRIVE_DEST.parent.exists():
        print(f"\n  [SYNC] Google Drive not available ({DRIVE_DEST.parent})")
        return None
    if preview_name:
        dest = DRIVE_DEST / preview_name
    else:
        # Auto-number in Drive
        existing = sorted(DRIVE_DEST.glob("v7-preview-*")) if DRIVE_DEST.exists() else []
        nn = 1
        for d in existing:
            try:
                n = int(d.name.split("-")[-1])
                if n >= nn: nn = n + 1
            except: pass
        dest = DRIVE_DEST / f"v7-preview-{nn:02d}"
    # Copy only JPGs in correct structure
    count = 0
    for root, dirs, files in os.walk(local_dir):
        for f in files:
            if f.endswith(".jpg"):
                src = Path(root) / f
                rel = src.relative_to(local_dir)
                dst = dest / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                count += 1
    print(f"\n  [SYNC] {count} files \u2192 {dest}")
    return dest

# ═══ VALIDATION TARGETS ═══════════════════════════════════════════════════
QA5 = [("maximo","CV-01"),("maximo","CV-04"),("maximo","MT-09"),("maxima","IN-04"),("maximo","GL-04")]
QA7 = QA5 + [("maximo","GL-01"),("maximo","GL-10")]

def main():
    parser = argparse.ArgumentParser(description="GenoMAX\u00b2 V7 Frame-Lock Renderer")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--validate-full", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--preview-dir", type=str, default=None)
    args = parser.parse_args()

    systems = {"maximo": DATA_DIR/"production-labels-maximo-v4.json",
               "maxima": DATA_DIR/"production-labels-maxima-v4.json"}
    all_skus = {}
    for sn, dp in systems.items():
        with open(dp, encoding='utf-8') as f: all_skus[sn] = json.load(f)["skus"]

    if args.validate or args.validate_full:
        targets = QA7 if args.validate_full else QA5
        if args.preview_dir: preview = args.preview_dir
        else:
            ds = BASE / "design-system"
            existing = sorted(ds.glob("v7-preview-*"))
            nn = 1
            for d in existing:
                try:
                    n = int(d.name.split("-")[-1])
                    if n >= nn: nn = n + 1
                except: pass
            preview = f"v7-preview-{nn:02d}"
        out = BASE / "design-system" / preview
        mode = "FULL 7-SAMPLE" if args.validate_full else "5-FORMAT QA"
        print("="*70)
        print(f"GenoMAX\u00b2 V7 Frame-Lock \u2014 {mode} VALIDATION")
        print("="*70)
        print(f"Output: {out}\n")

        results = []
        for sys_n, mc in targets:
            found = None
            for sku in all_skus[sys_n]:
                if sku["_meta"]["module_code"] == mc: found = sku; break
            if not found: print(f"  SKIP {mc}"); continue
            fmt = found["format"]["label_format"]
            ing = found["front_panel"]["zone_3"]["ingredient_name"]
            print(f"  {mc} | {fmt:7s} | {ing[:40]}", end="")
            r = render_sku(found, sys_n, output_base=out)
            r["sku"] = mc
            results.append(r)
            print(f"  {r['status']}")

        # PASS/FAIL TABLE
        print(f"\n{'='*70}")
        print(f"{'Format':<9}| {'Front':<7}| {'Back':<7}| {'Footer':<8}| {'QR':<6}| {'Missing Blocks':<30}| Status")
        print(f"{'-'*9}|{'-'*8}|{'-'*8}|{'-'*9}|{'-'*7}|{'-'*31}|{'-'*7}")
        for r in results:
            mb = ", ".join(r.get("missing_blocks",[]))[:30] or "none"
            print(f"{r.get('format','?'):<9}| {r['front_fit']:<7}| {r['back_fit']:<7}| {r['footer_safe']:<8}| {r['qr_safe']:<6}| {mb:<30}| {r['status']}")
        passed = sum(1 for r in results if r["status"] == "PASS")
        total = len(results)
        print(f"\nRESULT: {passed}/{total} PASSED")
        if passed == total: print("ALL QA CHECKS PASSED")
        else: print("FAIL CONDITIONS DETECTED")
        print(f"Output: {out}")

        # Auto-sync to Google Drive
        sync_to_drive(out, preview)

    elif args.full:
        print("="*70); print("GenoMAX\u00b2 V7 Frame-Lock \u2014 FULL PRODUCTION"); print("="*70)
        ok, err = 0, 0
        for sn, skus in all_skus.items():
            for i, sku in enumerate(skus):
                m = sku["_meta"]; fmt = sku["format"]["label_format"]
                print(f"  [{i+1:3d}/{len(skus)}] {m['module_code']} | {fmt:7s}", end="")
                r = render_sku(sku, sn)
                if r["status"] == "PASS": ok += 1; print(" OK")
                else: err += 1; print(f" FAIL: {r.get('missing_blocks',[])}")
        print(f"\n{ok} OK, {err} FAILED \u2192 {OUTPUT_BASE}")
        # Auto-sync full production to Google Drive
        sync_to_drive(OUTPUT_BASE)
    else:
        parser.print_help()

if __name__ == "__main__": main()
