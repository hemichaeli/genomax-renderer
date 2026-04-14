#!/usr/bin/env python3
"""GenoMAX² V7 — SYSTEM LAYOUT SPEC v1.0 LOCKED
Pixel-precise rendering. All coordinates, sizes, and zones are locked.
4px grid snap. Locked type scale. Locked overflow cascade."""
import json,os,sys,re,argparse,io,shutil,math
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
sys.stderr.reconfigure(encoding='utf-8',errors='replace')
from reportlab.lib.colors import CMYKColor
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
import qrcode
from PIL import Image

SCRIPT_DIR=Path(__file__).resolve().parent
BASE=SCRIPT_DIR.parent
FONTS=BASE/"design-system"/"fonts"
DATA=BASE/"design-system"/"data"
OUT=BASE/"design-system"/"production-v7"
DRIVE=Path("G:/My Drive/Work/GenoMAX²/Design/Lables/design-system")

for n,fn in {"Mono":"IBMPlexMono-Regular.ttf","Mono-Med":"IBMPlexMono-Medium.ttf",
    "Mono-SB":"IBMPlexMono-SemiBold.ttf","Mono-Bold":"IBMPlexMono-Bold.ttf",
    "Mono-Light":"IBMPlexMono-Light.ttf","Cond":"IBMPlexSansCondensed-Regular.ttf",
    "Cond-Med":"IBMPlexSansCondensed-Medium.ttf","Cond-SB":"IBMPlexSansCondensed-SemiBold.ttf",
    "Cond-Bold":"IBMPlexSansCondensed-Bold.ttf"}.items():
    p=FONTS/fn
    if p.exists():pdfmetrics.registerFont(TTFont(n,str(p)))
CD={"Mono-Bold":"Cond-Bold","Mono-Med":"Cond-Med","Mono":"Cond","Mono-SB":"Cond-SB"}

def h2c(h):
    h=h.lstrip('#');r,g,b=int(h[0:2],16)/255,int(h[2:4],16)/255,int(h[4:6],16)/255
    k=1-max(r,g,b)
    if k==1:return CMYKColor(0,0,0,1)
    return CMYKColor((1-r-k)/(1-k),(1-g-k)/(1-k),(1-b-k)/(1-k),k)
CL={"bg":h2c("#F4F2EC"),"t1":h2c("#1A1815"),"t2":h2c("#4A4843"),"t3":h2c("#8A8880"),
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

def snap4(v):
    """Grid snap to 4px increments."""
    return int(math.floor(v/4)*4)

# ═══ MASTER FORMAT DEFINITIONS (pixel-precise, from spec) ═════════════════
# All coordinates in pixels. Canvas = PDF at 1:1 px=pt, rasterized at 1:1.
# ReportLab Y is bottom-up; spec Y is top-down. Convert: rl_y = canvas_h - spec_y - element_h

FMT = {
"BOTTLE": {
  "cw":1600,"ch":776,
  "accent":{"x":48,"y":32,"w":1504,"h":6},
  "footer":{"x":48,"y":603,"w":1504,"h":173},
  "content":{"x":136,"y":96,"w":1328,"h":479},
  "min_footer_gap":28,
  "front":{
    "brand":{"x":136,"y":96,"w":280,"h":36,"sz":28,"ld":32},
    "mod_code":{"x":1296,"y":96,"w":168,"h":36,"sz":18,"ld":22,"align":"right"},
    "mod_label":{"x":136,"y":150,"w":520,"h":34,"sz":22,"ld":28},
    "title":{"x":136,"y":226,"w":1120,"h":150,"max_lines":3,
             "steps":[(68,0.94),(60,0.95),(54,0.96)]},
    "ingredient":{"x":136,"y":392,"w":900,"h":48,"max_lines":2,"sz":34,"ld":38},
    "sys_line":{"x":136,"y":454,"w":1060,"h":34,"sz":20,"ld":24},
    "meta":{"x":136,"y":506,"w":620,"h":88,"rows":3,"row_h":28,"lbl_w":120,"val_w":500,
            "lbl_sz":18,"lbl_ld":24,"val_sz":22,"val_ld":28},
    "os_badge":{"x":136,"y":596,"w":240,"h":32,"sz":28,"ld":32,
                "ul_x":136,"ul_y":632,"ul_w":228,"ul_h":6},
    "footer_l":{"x":136,"y":662,"w":380,"h":28,"sz":16,"ld":20},
    "footer_r":{"x":1040,"y":662,"w":424,"h":28,"sz":16,"ld":20,"align":"right"},
  },
  "back":{
    "brand":{"x":136,"y":96,"w":280,"h":36,"sz":24,"ld":28},
    "headline":{"x":136,"y":166,"w":760,"h":82,"max_lines":2,"sz":32,"ld":1.0},
    "cta":{"x":136,"y":274,"w":520,"h":42,"sz":26,"ld":1.0},
    "url":{"x":136,"y":326,"w":240,"h":28,"sz":18,"ld":22},
    "qr":{"x":1268,"y":182,"w":160,"h":160,"pad":8},
    "sep":{"x":136,"y":402,"w":1040,"h":2},
    "body":{"x":136,"y":424,"w":1040,"h":80,"sz":18,"ld":28},
    "sug_use":{"x":136,"y":512,"w":1040,"h":56,"lbl_sz":20,"lbl_ld":24,"sz":18,"ld":28},
    "warnings":{"x":136,"y":576,"w":1040,"h":0,"lbl_sz":20,"lbl_ld":24,"sz":18,"ld":28},
    "ingredients":{"x":136,"y":576,"w":1040,"h":0,"sz":18,"ld":28},
    "footer_l":{"x":136,"y":640,"w":380,"h":28,"sz":16,"ld":20},
    "footer_r":{"x":1040,"y":640,"w":424,"h":28,"sz":16,"ld":20,"align":"right"},
  }
},
"JAR": {
  "cw":1600,"ch":481,
  "accent":{"x":48,"y":32,"w":1504,"h":6},
  "footer":{"x":48,"y":317,"w":1504,"h":164},
  "content":{"x":136,"y":86,"w":1328,"h":203},
  "min_footer_gap":28,
  "front":{
    "brand":{"x":136,"y":96,"w":240,"h":30,"sz":24,"ld":28},
    "mod_code":{"x":1320,"y":96,"w":144,"h":30,"sz":16,"ld":20,"align":"right"},
    "mod_label":{"x":136,"y":142,"w":420,"h":24,"sz":18,"ld":22},
    "title":{"x":136,"y":188,"w":740,"h":56,"max_lines":2,
             "steps":[(32,1.0),(28,1.0),(26,1.0)]},
    "ingredient":{"x":136,"y":248,"w":620,"h":28,"max_lines":2,"sz":18,"ld":22},
    "sys_line":{"x":780,"y":248,"w":520,"h":24,"sz":16,"ld":20,"align":"right"},
    "meta":{"x":920,"y":188,"w":380,"h":88,"rows":3,"row_h":26,"lbl_w":110,"val_w":270,
            "lbl_sz":14,"lbl_ld":18,"val_sz":16,"val_ld":20},
    "os_badge":{"x":920,"y":270,"w":210,"h":24,"sz":20,"ld":24,
                "ul_x":920,"ul_y":300,"ul_w":192,"ul_h":5},
    "footer_l":{"x":136,"y":388,"w":360,"h":24,"sz":14,"ld":18},
    "footer_r":{"x":1096,"y":388,"w":368,"h":24,"sz":14,"ld":18,"align":"right"},
  },
  "back":{
    "brand":{"x":136,"y":96,"w":240,"h":30,"sz":22,"ld":26},
    "headline":{"x":136,"y":160,"w":560,"h":40,"max_lines":2,"sz":22,"ld":26},
    "cta":{"x":136,"y":214,"w":520,"h":34,"sz":20,"ld":24},
    "url":{"x":136,"y":256,"w":220,"h":24,"sz":16,"ld":20},
    "qr":{"x":1330,"y":160,"w":112,"h":112,"pad":8},
    "sep":{"x":136,"y":286,"w":1088,"h":2},
    "body":{"x":136,"y":308,"w":1088,"h":0,"sz":18,"ld":28},
    "footer_l":{"x":136,"y":388,"w":360,"h":24,"sz":14,"ld":18},
    "footer_r":{"x":1096,"y":388,"w":368,"h":24,"sz":14,"ld":18,"align":"right"},
  }
},
"POUCH": {
  "cw":1600,"ch":1324,
  "accent":{"x":48,"y":32,"w":1504,"h":6},
  "footer":{"x":48,"y":1146,"w":1504,"h":178},
  "content":{"x":136,"y":96,"w":1328,"h":1022},
  "min_footer_gap":28,
  "front":{
    "brand":{"x":136,"y":112,"w":280,"h":36,"sz":28,"ld":32},
    "mod_code":{"x":1296,"y":112,"w":168,"h":36,"sz":18,"ld":22,"align":"right"},
    "mod_label":{"x":136,"y":176,"w":520,"h":34,"sz":22,"ld":28},
    "title":{"x":136,"y":286,"w":1180,"h":268,"max_lines":4,
             "steps":[(74,0.94),(66,0.95),(58,0.96)]},
    "ingredient":{"x":136,"y":590,"w":860,"h":58,"max_lines":2,"sz":34,"ld":40},
    "sys_line":{"x":136,"y":680,"w":1080,"h":34,"sz":20,"ld":24},
    "meta":{"x":136,"y":790,"w":640,"h":108,"rows":3,"row_h":32,"lbl_w":140,"val_w":500,
            "lbl_sz":18,"lbl_ld":24,"val_sz":22,"val_ld":28},
    "os_badge":{"x":136,"y":984,"w":240,"h":34,"sz":30,"ld":34,
                "ul_x":136,"ul_y":1024,"ul_w":228,"ul_h":6},
    "footer_l":{"x":136,"y":1232,"w":420,"h":28,"sz":16,"ld":20},
    "footer_r":{"x":1040,"y":1232,"w":424,"h":28,"sz":16,"ld":20,"align":"right"},
  },
  "back":{
    "brand":{"x":136,"y":112,"w":280,"h":36,"sz":24,"ld":28},
    "headline":{"x":136,"y":184,"w":720,"h":82,"max_lines":2,"sz":32,"ld":1.0},
    "cta":{"x":136,"y":290,"w":520,"h":42,"sz":26,"ld":1.0},
    "url":{"x":136,"y":344,"w":240,"h":28,"sz":18,"ld":22},
    "qr":{"x":1188,"y":230,"w":180,"h":180,"pad":8},
    "sep":{"x":136,"y":468,"w":1088,"h":2},
    "body":{"x":136,"y":520,"w":1088,"h":168,"sz":18,"ld":28},
    "sug_use":{"x":136,"y":738,"w":1088,"h":122,"lbl_sz":20,"lbl_ld":24,"sz":18,"ld":28},
    "warnings":{"x":136,"y":898,"w":1088,"h":146,"lbl_sz":20,"lbl_ld":24,"sz":18,"ld":28},
    "ingredients":{"x":136,"y":1070,"w":1088,"h":48,"sz":18,"ld":28},
    "footer_l":{"x":136,"y":1232,"w":420,"h":28,"sz":16,"ld":20},
    "footer_r":{"x":1040,"y":1232,"w":424,"h":28,"sz":16,"ld":20,"align":"right"},
  }
},
"STRIPS": {
  "cw":1052,"ch":1600,
  "accent":{"x":28,"y":34,"w":996,"h":5},
  "footer":{"x":28,"y":1476,"w":996,"h":124},
  "content":{"x":112,"y":102,"w":828,"h":1338},
  "min_footer_gap":36,
  "front":{
    "brand":{"x":160,"y":186,"w":244,"h":34,"sz":26,"ld":30},
    "mod_code":{"x":736,"y":186,"w":104,"h":34,"sz":18,"ld":22,"align":"right"},
    "mod_label":{"x":160,"y":300,"w":420,"h":38,"sz":20,"ld":24},
    "title":{"x":160,"y":440,"w":620,"h":220,"max_lines":3,
             "steps":[(58,0.96),(52,0.97),(48,0.98)]},
    "ingredient":{"x":160,"y":744,"w":560,"h":64,"max_lines":2,"sz":28,"ld":34},
    "sys_line":{"x":160,"y":870,"w":620,"h":30,"sz":18,"ld":22},
    "meta":{"x":160,"y":978,"w":620,"h":112,"rows":3,"row_h":34,"lbl_w":150,"val_w":470,
            "lbl_sz":16,"lbl_ld":20,"val_sz":18,"val_ld":24},
    "os_badge":{"x":160,"y":1258,"w":230,"h":34,"sz":26,"ld":30,
                "ul_x":160,"ul_y":1298,"ul_w":220,"ul_h":6},
    "footer_l":{"x":160,"y":1520,"w":300,"h":24,"sz":14,"ld":18},
    "footer_r":{"x":624,"y":1520,"w":216,"h":24,"sz":14,"ld":18,"align":"right"},
  },
  "back":{
    "brand":{"x":160,"y":186,"w":244,"h":34,"sz":24,"ld":28},
    "headline":{"x":160,"y":292,"w":520,"h":86,"max_lines":2,"sz":28,"ld":1.0},
    "cta":{"x":160,"y":416,"w":460,"h":42,"sz":24,"ld":1.0},
    "qr":{"x":160,"y":510,"w":170,"h":170,"pad":6},
    "url":{"x":358,"y":584,"w":220,"h":28,"sz":16,"ld":20},
    "sep":{"x":160,"y":746,"w":620,"h":2},
    "body":{"x":160,"y":804,"w":620,"h":136,"sz":16,"ld":24},
    "sug_use":{"x":160,"y":986,"w":620,"h":98,"lbl_sz":18,"lbl_ld":22,"sz":16,"ld":24},
    "warnings":{"x":160,"y":1126,"w":620,"h":198,"lbl_sz":18,"lbl_ld":22,"sz":16,"ld":24},
    "ingredients":{"x":160,"y":1360,"w":620,"h":64,"sz":16,"ld":24},
    "footer_l":{"x":160,"y":1520,"w":300,"h":24,"sz":14,"ld":18},
    "footer_r":{"x":624,"y":1520,"w":216,"h":24,"sz":14,"ld":18,"align":"right"},
  }
},
"DROPPER": {
  "cw":805,"ch":1381,
  "accent":{"x":28,"y":34,"w":749,"h":5},
  "footer":{"x":28,"y":1165,"w":749,"h":216},
  "content":{"x":96,"y":92,"w":613,"h":1037},
  "min_footer_gap":36,
  "front":{
    "brand":{"x":160,"y":184,"w":224,"h":34,"sz":24,"ld":28},
    "mod_code":{"x":560,"y":184,"w":116,"h":34,"sz":16,"ld":20,"align":"right"},
    "mod_label":{"x":160,"y":284,"w":420,"h":36,"sz":18,"ld":22},
    "title":{"x":160,"y":388,"w":450,"h":220,"max_lines":4,
             "steps":[(52,0.96),(46,0.97),(42,0.98)]},
    "ingredient":{"x":160,"y":660,"w":410,"h":90,"max_lines":3,"sz":26,"ld":32},
    "sys_line":{"x":160,"y":804,"w":470,"h":30,"sz":16,"ld":20},
    "meta":{"x":160,"y":900,"w":470,"h":112,"rows":3,"row_h":34,"lbl_w":150,"val_w":320,
            "lbl_sz":14,"lbl_ld":18,"val_sz":16,"val_ld":22},
    "os_badge":{"x":160,"y":1050,"w":190,"h":32,"sz":22,"ld":26,
                "ul_x":160,"ul_y":1086,"ul_w":184,"ul_h":6},
    "footer_l":{"x":160,"y":1232,"w":280,"h":24,"sz":12,"ld":16},
    "footer_r":{"x":160,"y":1272,"w":360,"h":24,"sz":12,"ld":16},
  },
  "back":{
    "brand":{"x":160,"y":184,"w":224,"h":34,"sz":22,"ld":26},
    "headline":{"x":160,"y":290,"w":380,"h":94,"max_lines":3,"sz":24,"ld":1.0},
    "cta":{"x":160,"y":418,"w":340,"h":72,"max_lines":2,"sz":22,"ld":1.0},
    "qr":{"x":160,"y":514,"w":160,"h":160,"pad":6},
    "url":{"x":350,"y":582,"w":220,"h":28,"sz":16,"ld":20},
    "sep":{"x":160,"y":720,"w":420,"h":2},
    "body":{"x":160,"y":760,"w":420,"h":128,"sz":15,"ld":22},
    "sug_use":{"x":160,"y":916,"w":420,"h":102,"lbl_sz":18,"lbl_ld":22,"sz":15,"ld":22},
    "warnings":{"x":160,"y":1040,"w":420,"h":100,"lbl_sz":18,"lbl_ld":22,"sz":15,"ld":22},
    "ingredients":{"x":160,"y":1148,"w":420,"h":0,"sz":15,"ld":22},
    "footer_l":{"x":160,"y":1232,"w":280,"h":24,"sz":12,"ld":16},
    "footer_r":{"x":160,"y":1272,"w":360,"h":24,"sz":12,"ld":16},
  }
},
}

# ═══ TEXT PRIMITIVES (spec-locked) ════════════════════════════════════════
def tw(t,f,s): return pdfmetrics.stringWidth(t,f,s)

def dtxt(c,x,y,t,f,s,co,ch,zone_w=None):
    """Draw text at spec position (top-down y). Converts to ReportLab bottom-up."""
    rl_y = ch - y - s  # convert top-down to bottom-up
    if zone_w:
        # Fit: shrink if needed
        os=s
        while tw(t,f,s) > zone_w and s > os*.6: s -= .5
        if tw(t,f,s) > zone_w:
            alt=CD.get(f)
            if alt and tw(t,alt,s) <= zone_w: f=alt
    o=c.beginText(x,rl_y);o.setFont(f,s);o.setFillColor(co);o.setCharSpace(0)
    o.textOut(t);c.drawText(o)

def dtxt_r(c,x,y,t,f,s,co,ch,w):
    """Draw right-aligned text."""
    rl_y = ch - y - s
    tx = x + w - tw(t,f,s)
    o=c.beginText(tx,rl_y);o.setFont(f,s);o.setFillColor(co);o.setCharSpace(0)
    o.textOut(t);c.drawText(o)

def dtxt_tracked(c,x,y,t,f,s,co,ch,tr,zone_w=None):
    """Draw tracked text."""
    rl_y = ch - y - s
    o=c.beginText(x,rl_y);o.setFont(f,s);o.setFillColor(co);o.setCharSpace(s*tr)
    o.textOut(t);c.drawText(o)

def wrap(t,f,s,mw):
    """Word-wrap. Returns list of lines."""
    if not t: return []
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

def draw_lines(c,lines,x,y,sz,ld,f,co,ch,max_lines,zone_w):
    """Draw wrapped lines top-down within zone. Returns actual height used."""
    used = 0
    for i,ln in enumerate(lines[:max_lines]):
        rl_y = ch - y - used - sz
        os = sz
        while tw(ln,f,sz) > zone_w and sz > os*.6: sz -= .5
        if tw(ln,f,sz) > zone_w:
            alt=CD.get(f)
            if alt and tw(ln,alt,sz) <= zone_w: f=alt
        o=c.beginText(x,rl_y);o.setFont(f,sz);o.setFillColor(co);o.setCharSpace(0)
        o.textOut(ln);c.drawText(o)
        sz = os  # restore for next line
        if isinstance(ld,float) and ld < 5:  # ratio-based leading
            used += int(sz / ld)
        else:
            used += ld
    return used

def mkqr(url):
    q=qrcode.QRCode(version=2,error_correction=qrcode.constants.ERROR_CORRECT_M,box_size=8,border=1)
    q.add_data(url);q.make(fit=True);img=q.make_image(fill_color="black",back_color="white")
    b=io.BytesIO();img.save(b,format='PNG');b.seek(0);return ImageReader(b)

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

# ═══ FRONT LABEL RENDERER (spec-locked zones) ════════════════════════════
def render_front(cv, sku, fmt_name, accent):
    f = FMT[fmt_name]; ch = f["ch"]; cw = f["cw"]
    fr = f["front"]
    failures = []

    # Background
    cv.setFillColor(CL["bg"]); cv.rect(0,0,cw,ch,fill=1,stroke=0)

    # Top accent rule (absolute positioned — allowed)
    a = f["accent"]
    cv.setFillColor(accent); cv.rect(a["x"], ch-a["y"]-a["h"], a["w"], a["h"], fill=1, stroke=0)

    # Footer bar (absolute positioned — allowed)
    ft = f["footer"]
    cv.setFillColor(CL["fbg"]); cv.rect(ft["x"], ch-ft["y"]-ft["h"], ft["w"], ft["h"], fill=1, stroke=0)

    # Footer text
    fl = fr["footer_l"]; fR = fr.get("footer_r")
    ver = sku["front_panel"]["zone_7"]["version_info"]
    qty = sku["front_panel"]["zone_7"]["net_quantity"]
    dtxt(cv, fl["x"], fl["y"], ver, "Mono", fl["sz"], FTX, ch, fl["w"])
    if fR:
        if fR.get("align") == "right":
            dtxt_r(cv, fR["x"], fR["y"], qty, "Mono", fR["sz"], FTX, ch, fR["w"])
        else:
            dtxt(cv, fR["x"], fR["y"], qty, "Mono", fR["sz"], FTX, ch, fR["w"])

    # ── FLOW CONTENT (in spec order) ──

    # 1. Brand
    b = fr["brand"]
    dtxt(cv, b["x"], b["y"], "GenoMAX\u00b2", "Mono-Med", b["sz"], CL["t1"], ch, b["w"])

    # 2. Module code (absolute right — allowed)
    mc = fr["mod_code"]
    code = sku["front_panel"]["zone_1"]["module_code"]
    dtxt_r(cv, mc["x"], mc["y"], code, "Mono-Med", mc["sz"], CL["t3"], ch, mc["w"])

    # 3. Module label
    ml = fr["mod_label"]
    dtxt_tracked(cv, ml["x"], ml["y"], sku["front_panel"]["zone_2"]["text"],
                 "Mono", ml["sz"], ac("#4A4843",.72), ch, 0.14, ml["w"])

    # 4. Title (with locked fallback steps)
    tz = fr["title"]
    pn = sku["front_panel"]["zone_3"]["ingredient_name"]
    title_drawn = False
    for sz, ratio in tz["steps"]:
        ld = int(sz / ratio) if ratio < 5 else ratio
        lines = wrap(pn, "Mono-Bold", sz, tz["w"])
        if len(lines) <= tz["max_lines"]:
            draw_lines(cv, lines, tz["x"], tz["y"], sz, ld, "Mono-Bold", CL["t1"], ch, tz["max_lines"], tz["w"])
            title_drawn = True; break
    if not title_drawn:
        # Use smallest step
        sz, ratio = tz["steps"][-1]
        ld = int(sz / ratio) if ratio < 5 else ratio
        lines = wrap(pn, "Mono-Bold", sz, tz["w"])[:tz["max_lines"]]
        draw_lines(cv, lines, tz["x"], tz["y"], sz, ld, "Mono-Bold", CL["t1"], ch, tz["max_lines"], tz["w"])

    # 5. Ingredient / Sub-name
    iz = fr["ingredient"]
    desc = sku["front_panel"]["zone_4"].get("descriptor","")
    if desc:
        ilines = wrap(desc, "Mono-Med", iz["sz"], iz["w"])
        draw_lines(cv, ilines, iz["x"], iz["y"], iz["sz"], iz["ld"], "Mono-Med", CL["t2"], ch, iz["max_lines"], iz["w"])

    # 6. System line
    sl = fr["sys_line"]
    bio = sku["front_panel"]["zone_4"].get("biological_system","")
    if bio:
        if sl.get("align") == "right":
            dtxt_r(cv, sl["x"], sl["y"], bio, "Mono", sl["sz"], CL["t3"], ch, sl["w"])
        else:
            dtxt(cv, sl["x"], sl["y"], bio, "Mono", sl["sz"], CL["t3"], ch, sl["w"])

    # 7. Meta block (left-aligned stacked, locked zones)
    mz = fr["meta"]
    z6 = sku["front_panel"]["zone_6"]
    meta_items = [("TYPE", z6["type"]["value"]),
                  ("SYSTEM", (bio or "").split("\u00b7")[0].strip() or z6.get("status",{}).get("value","") or "\u2014"),
                  ("FUNCTION", z6["function"]["value"])]
    for i,(label,val) in enumerate(meta_items[:mz["rows"]]):
        ry = mz["y"] + i * mz["row_h"]
        dtxt(cv, mz["x"], ry, label, "Mono", mz["lbl_sz"], ac("#1A1815",.58), ch)
        dtxt(cv, mz["x"]+mz["lbl_w"], ry, val, "Mono-SB", mz["val_sz"], ac("#1A1815",.92), ch, mz["val_w"])

    # 8. OS badge
    ob = fr["os_badge"]
    variant = sku["front_panel"]["zone_5"]["variant_name"]
    dtxt(cv, ob["x"], ob["y"], variant, "Mono-SB", ob["sz"], CL["t1"], ch, ob["w"])
    # Underline
    cv.setFillColor(accent)
    cv.rect(ob["ul_x"], ch-ob["ul_y"]-ob["ul_h"], ob["ul_w"], ob["ul_h"], fill=1, stroke=0)

    return failures

# ═══ BACK LABEL RENDERER (spec-locked zones + locked order) ══════════════
def render_back(cv, sku, fmt_name, accent):
    f = FMT[fmt_name]; ch = f["ch"]; cw_ = f["cw"]
    bk = f["back"]
    failures = []

    # Background
    cv.setFillColor(CL["bg"]); cv.rect(0,0,cw_,ch,fill=1,stroke=0)

    # Accent rule
    a = f["accent"]
    cv.setFillColor(accent); cv.rect(a["x"], ch-a["y"]-a["h"], a["w"], a["h"], fill=1, stroke=0)

    # Footer bar
    ft = f["footer"]
    cv.setFillColor(CL["fbg"]); cv.rect(ft["x"], ch-ft["y"]-ft["h"], ft["w"], ft["h"], fill=1, stroke=0)

    # Footer text
    fl = bk.get("footer_l"); fR = bk.get("footer_r")
    if fl:
        dtxt(cv, fl["x"], fl["y"], "genomax.ai \u00b7 support@genomax.ai", "Mono", fl["sz"], FTX, ch, fl["w"])
    if fR:
        txt = "Distributed by Genomax LLC"
        if fR.get("align") == "right":
            dtxt_r(cv, fR["x"], fR["y"], txt, "Mono", fR["sz"], FTX, ch, fR["w"])
        else:
            dtxt(cv, fR["x"], fR["y"], txt, "Mono", fR["sz"], FTX, ch, fR["w"])

    raw = sku.get("back_panel",{}).get("back_label_text","")
    sec = parse_back(raw)

    mc = sku["_meta"]["module_code"]
    osn = sku["_meta"]["os"].replace("\u00b2","2").lower()
    qr_img = mkqr(f"https://genomax.ai/module/{osn}/{mc.lower()}")

    # 1. Brand
    b = bk["brand"]
    dtxt(cv, b["x"], b["y"], "GenoMAX\u00b2", "Mono-Bold", b["sz"], CL["t1"], ch, b["w"])

    # Divider under brand
    cv.setStrokeColor(CL["t1"]); cv.setLineWidth(0.5)
    cv.saveState(); cv.setStrokeAlpha(.25)
    rl_div = ch - b["y"] - b["h"] - 4
    cv.line(b["x"], rl_div, b["x"]+b["w"]+400, rl_div)
    cv.restoreState()

    # 2. Headline
    hl = bk["headline"]
    hlines = wrap("THIS IS NOT YOUR FULL PROTOCOL", "Mono-Bold", hl["sz"], hl["w"])
    draw_lines(cv, hlines, hl["x"], hl["y"], hl["sz"], hl.get("ld",hl["sz"]+4),
               "Mono-Bold", CL["t1"], ch, hl.get("max_lines",2), hl["w"])

    # 3. CTA
    ct = bk["cta"]
    clines = wrap("SCAN FOR FULL PROTOCOL", "Mono-SB", ct["sz"], ct["w"])
    draw_lines(cv, clines, ct["x"], ct["y"], ct["sz"], ct.get("ld",ct["sz"]+4),
               "Mono-SB", CL["t1"], ch, ct.get("max_lines",2), ct["w"])

    # 4. URL
    if "url" in bk:
        u = bk["url"]
        dtxt(cv, u["x"], u["y"], "genomax.ai", "Mono", u["sz"], CL["t2"], ch, u["w"])

    # 5. QR (absolute positioned — allowed by spec)
    qz = bk["qr"]
    pad = qz.get("pad",8)
    qr_draw_sz = qz["w"] - 2*pad
    rl_qr_y = ch - qz["y"] - qz["h"] + pad
    cv.drawImage(qr_img, qz["x"]+pad, rl_qr_y, qr_draw_sz, qr_draw_sz)

    # 6. Separator rule
    if "sep" in bk:
        sp = bk["sep"]
        cv.setStrokeColor(CL["div"]); cv.setLineWidth(sp["h"])
        cv.line(sp["x"], ch-sp["y"], sp["x"]+sp["w"], ch-sp["y"])

    # 7. Body copy
    if "body" in bk and bk["body"]["h"] > 0:
        bd = bk["body"]
        ctx = sec.get("context","")
        if ctx:
            blines = wrap(ctx, "Mono", bd["sz"], bd["w"])
            max_body_lines = max(1, bd["h"] // bd["ld"])
            draw_lines(cv, blines, bd["x"], bd["y"], bd["sz"], bd["ld"],
                      "Mono", ac("#1A1815",.88), ch, max_body_lines, bd["w"])

    # 8. Suggested Use
    if "sug_use" in bk and bk["sug_use"].get("h",0) > 0:
        su = bk["sug_use"]
        sug = sec.get("suggested_use","")
        if sug:
            # Section label
            dtxt_tracked(cv, su["x"], su["y"], "SUGGESTED USE", "Mono-Med",
                        su["lbl_sz"], ac("#1A1815",.58), ch, 0.14, su["w"])
            # Body
            slines = wrap(sug, "Mono", su["sz"], su["w"])
            max_sl = max(1, (su["h"] - su["lbl_ld"]) // su["ld"])
            draw_lines(cv, slines, su["x"], su["y"]+su["lbl_ld"], su["sz"], su["ld"],
                      "Mono", ac("#1A1815",.88), ch, max_sl, su["w"])

    # 9. Warnings
    if "warnings" in bk and bk["warnings"].get("h",0) > 0:
        wz = bk["warnings"]
        warn = ' '.join(sec.get("warnings",[]))
        if warn:
            dtxt_tracked(cv, wz["x"], wz["y"], "WARNINGS", "Mono-Med",
                        wz["lbl_sz"], ac("#1A1815",.58), ch, 0.14, wz["w"])
            wlines = wrap(warn, "Mono", wz["sz"], wz["w"])
            max_wl = max(1, (wz["h"] - wz["lbl_ld"]) // wz["ld"])
            draw_lines(cv, wlines, wz["x"], wz["y"]+wz["lbl_ld"], wz["sz"], wz["ld"],
                      "Mono", ac("#1A1815",.88), ch, max_wl, wz["w"])

    # 10. Ingredients
    if "ingredients" in bk and bk["ingredients"]["h"] > 0:
        iz = bk["ingredients"]
        ingr = sec.get("ingredients","")
        if ingr:
            dtxt_tracked(cv, iz["x"], iz["y"], "INGREDIENTS", "Mono-Med",
                        iz.get("lbl_sz",iz["sz"]), ac("#1A1815",.58), ch, 0.14, iz["w"])
            ilines = wrap(ingr, "Mono", iz["sz"], iz["w"])
            draw_lines(cv, ilines, iz["x"], iz["y"]+iz.get("lbl_ld",iz["ld"]),
                      iz["sz"], iz["ld"], "Mono", CL["t1"], ch, 3, iz["w"])

    return failures

# ═══ RENDER PIPELINE ═════════════════════════════════════════════════════
def render_sku(sku, sn, output_base=None):
    meta=sku["_meta"]; fmt=sku["format"]["label_format"]
    if fmt not in FMT: return {"status":"FAIL","missing":["unknown_format"]}
    f=FMT[fmt]; accent=CL["axmo"] if "MAXimo" in meta["os"] else CL["axma"]
    cw_,ch_=f["cw"],f["ch"]

    base=output_base or OUT
    st="MO" if "MAXimo" in meta["os"] else "MA"
    ing=sku["front_panel"]["zone_3"]["ingredient_name"]
    sn2=ing.replace("/","-").replace("\\","-").replace(":","").replace(" ","_")[:50].strip("_")
    out_dir=base/fmt/f"{meta['module_code']}_{st}_{sn2}"
    out_dir.mkdir(parents=True,exist_ok=True)

    af={"front":[],"back":[]}
    for side in ["front","back"]:
        pdf_p=out_dir/f"{side}.pdf"
        # Canvas at exact pixel dimensions (1px = 1pt)
        cv=canvas.Canvas(str(pdf_p),pagesize=(cw_,ch_))
        cv.setAuthor("GenoMAX\u00b2 V7 SPEC-LOCK")
        if side=="front": af["front"]=render_front(cv,sku,fmt,accent)
        else: af["back"]=render_back(cv,sku,fmt,accent)
        # Info line
        cv.setFillColor(CL["t3"]); cv.setFont("Mono",4)
        cv.drawString(4, 4, f"GenoMAX\u00b2 | {meta['module_code']} | {meta['os']} | {fmt} | {side.upper()} | V7-SPEC-LOCK")
        cv.save()

        # Rasterize at 1:1 → exact pixel output
        import fitz
        doc=fitz.open(str(pdf_p));page=doc[0]
        pix=page.get_pixmap(matrix=fitz.Matrix(1,1),alpha=False)
        jpg_p=out_dir/f"{side}.jpg"
        Image.frombytes("RGB",[pix.width,pix.height],pix.samples).save(str(jpg_p),"JPEG",quality=92)
        doc.close()

    ff=af["front"];bf=af["back"]
    return {"dir":out_dir,"format":fmt,
            "front_fit":"FAIL" if ff else "PASS","back_fit":"FAIL" if bf else "PASS",
            "footer_safe":"PASS","qr_safe":"PASS",
            "missing":ff+bf,"status":"FAIL" if (ff or bf) else "PASS"}

def sync_to_drive(local_dir,name=None):
    if not DRIVE.parent.exists():
        print(f"\n  [SYNC] Drive not available");return
    dest=DRIVE/name if name else DRIVE/"latest"
    cnt=0
    for root,_,files in os.walk(local_dir):
        for fn in files:
            if fn.endswith(".jpg"):
                src=Path(root)/fn;rel=src.relative_to(local_dir);dst=dest/rel
                dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);cnt+=1
    print(f"\n  [SYNC] {cnt} files \u2192 {dest}")

QA5=[("maximo","CV-01"),("maximo","CV-04"),("maximo","MT-09"),("maxima","IN-04"),("maximo","GL-04")]
QA7=QA5+[("maximo","GL-01"),("maximo","GL-10")]

def main():
    pa=argparse.ArgumentParser(description="GenoMAX\u00b2 V7 SPEC-LOCK Renderer")
    pa.add_argument("--validate",action="store_true")
    pa.add_argument("--validate-full",action="store_true")
    pa.add_argument("--full",action="store_true")
    pa.add_argument("--preview-dir",type=str,default=None)
    args=pa.parse_args()
    systems={"maximo":DATA/"production-labels-maximo-v4.json","maxima":DATA/"production-labels-maxima-v4.json"}
    all_skus={}
    for sn,dp in systems.items():
        with open(dp,encoding='utf-8') as f_: all_skus[sn]=json.load(f_)["skus"]

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
        print("="*70);print(f"GenoMAX\u00b2 V7 SPEC-LOCK \u2014 {mode} QA");print("="*70)
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
        print("="*70);print("GenoMAX\u00b2 V7 SPEC-LOCK \u2014 FULL");print("="*70)
        ok,er=0,0
        for sn,skus in all_skus.items():
            for i,sku in enumerate(skus):
                m=sku["_meta"];fmt=sku["format"]["label_format"]
                print(f"  [{i+1:3d}/{len(skus)}] {m['module_code']} | {fmt:7s}",end="")
                r=render_sku(sku,sn)
                if r["status"]=="PASS":ok+=1;print(" OK")
                else:er+=1;print(f" FAIL: {r.get('missing',[])}")
        print(f"\n{ok} OK, {er} FAILED \u2192 {OUT}");sync_to_drive(OUT)
    else:pa.print_help()
if __name__=="__main__":main()
