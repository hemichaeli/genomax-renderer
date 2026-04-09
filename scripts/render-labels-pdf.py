"""
GenoMAX² — Actual-Size Label PDF Renderer
==========================================
Renders 8 labels at real print dimensions using V3 signature system.
Output: design-system/outputs/label-renders.pdf
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, mm
from reportlab.lib.colors import HexColor, Color
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# ══ COLORS ══
BG = HexColor("#F4F2EC")
PRI = HexColor("#1A1815")
SEC = HexColor("#4A4843")
TER = HexColor("#8A8880")
DIV = HexColor("#C5C2BA")
MXO = HexColor("#7A1E2E")
MXA = HexColor("#7A304A")
STRIP_BG = HexColor("#1A1815")
STRIP_TEXT = HexColor("#C5C2BA")
WHITE = HexColor("#FFFFFF")

# ══ FONT REGISTRATION ══
# Use Helvetica as fallback (always available in reportlab)
# IBM Plex approximation via weight mapping

# ══ 8 LABEL DEFINITIONS ══
LABELS = [
    {
        "title": "BOTTLE · MAXimo² · Short name",
        "fmt": "BOTTLE", "w": 6*inch, "h": 2.5*inch,
        "os": "MAXimo²", "accent": MXO,
        "code": "GL-01", "name": "BERBERINE",
        "desc": "Berberine HCl",
        "bio": "METABOLIC SYSTEM · INSULIN SENSITIVITY",
        "form": "Capsules", "func": "Insulin Sensitivity",
        "qty": "0.2 lb (90 g)", "nameSize": 38,
    },
    {
        "title": "BOTTLE · MAXima² · Medium name",
        "fmt": "BOTTLE", "w": 6*inch, "h": 2.5*inch,
        "os": "MAXima²", "accent": MXA,
        "code": "IN-05", "name": "LIVER SUPPORT",
        "desc": "Milk Thistle + Liver Blend",
        "bio": "INFLAMMATION SYSTEM · HEPATIC DETOXIFICATION",
        "form": "Capsules", "func": "Hepatic Detoxification",
        "qty": "0.2 lb (90.72 g)", "nameSize": 34,
    },
    {
        "title": "BOTTLE · MAXimo² · Long name (46 chars)",
        "fmt": "BOTTLE", "w": 6*inch, "h": 2.5*inch,
        "os": "MAXimo²", "accent": MXO,
        "code": "MT-10", "name": "BCAA POST WORKOUT POWDER\n(HONEYDEW/WATERMELON)",
        "desc": "BCAAs",
        "bio": "MITOCHONDRIAL SYSTEM · MUSCLE RECOVERY",
        "form": "Powders", "func": "Muscle Recovery",
        "qty": "1 lb (454 g)", "nameSize": 22,
    },
    {
        "title": "POUCH · MAXimo² · Medium name",
        "fmt": "POUCH", "w": 5*inch, "h": 4*inch,
        "os": "MAXimo²", "accent": MXO,
        "code": "GL-12", "name": "L-GLUTAMINE\nPOWDER",
        "desc": "L-Glutamine",
        "bio": "METABOLIC SYSTEM · GUT MUCOSAL INTEGRITY",
        "form": "Powders", "func": "Gut Mucosal Integrity",
        "qty": "0.7 lb (317 g)", "nameSize": 36,
    },
    {
        "title": "DROPPER · MAXimo² · Medium name",
        "fmt": "DROPPER", "w": 2*inch, "h": 4*inch,
        "os": "MAXimo²", "accent": MXO,
        "code": "GL-01", "name": "NORMAL\nBLOOD SUGAR\nDROPS",
        "desc": "Berberine HCl",
        "bio": "METABOLIC · INSULIN",
        "form": "Drops", "func": "Insulin Sensitivity",
        "qty": "2.7 oz (75 g)", "nameSize": 16,
    },
    {
        "title": "STRIPS · MAXima² · Medium name",
        "fmt": "STRIPS", "w": 4*inch, "h": 6.5*inch,
        "os": "MAXima²", "accent": MXA,
        "code": "COG-01", "name": "MUSHROOM\nFOCUS STRIPS",
        "desc": "Bacopa + Nootropic Blend",
        "bio": "COGNITIVE SYSTEM · COGNITIVE CLARITY",
        "form": "Strips", "func": "Cognitive Clarity",
        "qty": "2 oz (60 g)", "nameSize": 40,
    },
    {
        "title": "JAR · MAXimo² · High density",
        "fmt": "JAR", "w": 8.5*inch, "h": 2*inch,
        "os": "MAXimo²", "accent": MXO,
        "code": "MT-01", "name": "ENERGY POWDER (FRUIT PUNCH)",
        "desc": "Beta-Alanine + Caffeine",
        "bio": "MITOCHONDRIAL SYSTEM · MITOCHONDRIAL ENERGY",
        "form": "Powders", "func": "Mitochondrial Energy",
        "qty": "6.42 oz (182 g)", "nameSize": 26,
    },
    {
        "title": "BOTTLE · MAXima² · Gummy product",
        "fmt": "BOTTLE", "w": 6*inch, "h": 2.5*inch,
        "os": "MAXima²", "accent": MXA,
        "code": "GL-13", "name": "HAIR SKIN & NAILS GUMMIES",
        "desc": "Biotin + Hair Nutrient Blend",
        "bio": "METABOLIC SYSTEM · KERATIN SYNTHESIS",
        "form": "Gummies", "func": "Keratin Synthesis",
        "qty": "6.63 oz (188 g)", "nameSize": 26,
    },
]

OUTPUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "design-system", "outputs", "label-renders.pdf")


def draw_label(c, x, y, label):
    """Draw one label at position (x, y) — bottom-left origin."""
    w = label["w"]
    h = label["h"]
    accent = label["accent"]
    is_narrow = label["fmt"] == "DROPPER"
    is_tall = label["fmt"] in ("STRIPS", "POUCH", "DROPPER")
    is_jar = label["fmt"] == "JAR"

    # Background
    c.setFillColor(BG)
    c.rect(x, y, w, h, fill=1, stroke=0)

    # Border
    c.setStrokeColor(DIV)
    c.setLineWidth(0.5)
    c.rect(x, y, w, h, fill=0, stroke=1)

    # ── BRAND CEILING ──
    c.setFillColor(accent)
    c.rect(x, y + h - 3, w, 3, fill=1, stroke=0)

    # Margins
    mx = 14 if is_narrow else 20
    top = y + h - 3  # below ceiling

    # ── BRAND ZONE ──
    brand_y = top - 14
    c.setFillColor(PRI)
    c.setFont("Helvetica-Bold", 10 if is_narrow else 14)
    c.drawString(x + mx, brand_y, "GenoMAX²")

    c.setFillColor(TER)
    c.setFont("Helvetica", 6 if is_narrow else 7)
    c.drawRightString(x + w - mx, brand_y, label["code"])

    # Brand rule
    rule_y = brand_y - 4
    c.setStrokeColor(Color(0.1, 0.09, 0.08, alpha=0.25))
    c.setLineWidth(0.5)
    c.line(x + mx, rule_y, x + w - mx, rule_y)

    # Content area
    cy = rule_y - 6
    cw = w - 2 * mx
    cx = x + mx + cw / 2  # center x

    # ── ZONE 2 ──
    c.setFillColor(SEC)
    c.setFont("Helvetica", 6 if is_narrow else (7 if is_jar else 8))
    c.drawCentredString(cx, cy, "B I O L O G I C A L   O S   M O D U L E")
    cy -= (10 if is_narrow else (8 if is_jar else 14))

    # ── ZONE 3: PRODUCT NAME ──
    c.setFillColor(PRI)
    ns = label["nameSize"]
    c.setFont("Helvetica-Bold", ns)
    lines = label["name"].split("\n")
    line_h = ns * 1.05
    for line in lines:
        c.drawCentredString(cx, cy, line)
        cy -= line_h
    cy -= (4 if is_jar else 6)

    # ── ZONE 4 ──
    c.setFillColor(SEC)
    c.setFont("Helvetica", 7 if is_narrow else (8 if is_jar else 10))
    c.drawCentredString(cx, cy, label["desc"])
    cy -= 10

    c.setFillColor(TER)
    c.setFont("Helvetica", 5 if is_narrow else (5.5 if is_jar else 7))
    c.drawCentredString(cx, cy, label["bio"])
    cy -= (12 if is_tall else (6 if is_jar else 10))

    # ── ZONE 5 ──
    c.setFillColor(PRI)
    c.setFont("Helvetica-Bold", 9 if is_narrow else (10 if is_jar else 14))
    c.drawCentredString(cx, cy, label["os"])
    cy -= 4

    # Accent rule
    aw = 30 if is_narrow else (50 if is_jar else 70)
    c.setFillColor(accent)
    c.rect(cx - aw/2, cy, aw, 2.5, fill=1, stroke=0)
    cy -= (10 if is_tall else (6 if is_jar else 12))

    # ── ZONE 6 ──
    meta = [
        ("TYPE", label["form"]),
        ("FUNCTION", label["func"]),
        ("STATUS", "Active"),
    ]

    if is_narrow:
        # Vertical stack
        for lbl, val in meta:
            c.setFillColor(TER)
            c.setFont("Helvetica", 4.5)
            c.drawString(x + mx, cy, lbl)
            c.setFillColor(PRI)
            c.setFont("Helvetica", 5.5)
            c.drawString(x + mx + 40, cy, val)
            cy -= 8
    else:
        # 3-column
        col_w = cw / 3
        for i, (lbl, val) in enumerate(meta):
            col_cx = x + mx + col_w * i + col_w / 2
            c.setFillColor(TER)
            c.setFont("Helvetica", 5 if is_jar else 6)
            c.drawCentredString(col_cx, cy + 7, lbl)
            c.setFillColor(PRI)
            c.setFont("Helvetica", 6 if is_jar else 7.5)
            c.drawCentredString(col_cx, cy - 2, val)

    # ── ZONE DIVIDER ──
    div_y = y + 18
    c.setStrokeColor(DIV)
    c.setLineWidth(0.5)
    c.line(x + mx, div_y, x + w - mx, div_y)

    # ── ZONE 7: DARK STRIP ──
    strip_h = 16
    c.setFillColor(STRIP_BG)
    c.rect(x, y, w, strip_h, fill=1, stroke=0)

    c.setFillColor(STRIP_TEXT)
    c.setFont("Helvetica", 5 if is_narrow else 6.5)
    c.drawString(x + mx, y + 5, f"v1.0 · {label['code']} · Clinical Grade")
    c.drawRightString(x + w - mx, y + 5, f"DIETARY SUPPLEMENT · {label['qty']}")


def main():
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    c = canvas.Canvas(OUTPUT, pagesize=letter)
    pw, ph = letter  # 612 x 792

    # ── PAGE 1: BOTTLE labels (4) ──
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(PRI)
    c.drawString(36, ph - 36, "GenoMAX² — LABEL RENDERS · ACTUAL SIZE · V3 SIGNATURE")
    c.setFont("Helvetica", 7)
    c.setFillColor(TER)
    c.drawString(36, ph - 48, "Page 1/3 · BOTTLE format (6\" × 2.5\") · 4 labels")

    bottles = [l for l in LABELS if l["fmt"] == "BOTTLE"]
    for i, label in enumerate(bottles):
        lx = 36
        ly = ph - 80 - (i * (2.5*inch + 24))

        # Title above label
        c.setFont("Helvetica", 7)
        c.setFillColor(TER)
        c.drawString(lx, ly + label["h"] + 6, label["title"])

        draw_label(c, lx, ly, label)

    c.showPage()

    # ── PAGE 2: POUCH + DROPPER + STRIPS ──
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(PRI)
    c.drawString(36, ph - 36, "GenoMAX² — LABEL RENDERS · ACTUAL SIZE · V3 SIGNATURE")
    c.setFont("Helvetica", 7)
    c.setFillColor(TER)
    c.drawString(36, ph - 48, "Page 2/3 · POUCH (5×4\") + DROPPER (2×4\") + STRIPS (4×6.5\")")

    # Pouch
    pouch = [l for l in LABELS if l["fmt"] == "POUCH"][0]
    c.setFont("Helvetica", 7)
    c.setFillColor(TER)
    c.drawString(36, ph - 66, pouch["title"])
    draw_label(c, 36, ph - 70 - pouch["h"], pouch)

    # Dropper (next to pouch)
    dropper = [l for l in LABELS if l["fmt"] == "DROPPER"][0]
    dx = 36 + 5*inch + 24
    c.setFont("Helvetica", 7)
    c.setFillColor(TER)
    c.drawString(dx, ph - 66, dropper["title"])
    draw_label(c, dx, ph - 70 - dropper["h"], dropper)

    # Strips (below, centered)
    strips = [l for l in LABELS if l["fmt"] == "STRIPS"][0]
    sy = ph - 70 - max(pouch["h"], dropper["h"]) - 24
    c.setFont("Helvetica", 7)
    c.setFillColor(TER)
    c.drawString(36, sy + 6, strips["title"])
    # Check if it fits on this page
    if sy - strips["h"] > 36:
        draw_label(c, 36, sy - strips["h"], strips)
    else:
        c.showPage()
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(PRI)
        c.drawString(36, ph - 36, "GenoMAX² — LABEL RENDERS · ACTUAL SIZE · V3 SIGNATURE")
        c.setFont("Helvetica", 7)
        c.setFillColor(TER)
        c.drawString(36, ph - 48, "Page 3 · STRIPS (4×6.5\")")
        c.drawString(36, ph - 66, strips["title"])
        draw_label(c, 36, ph - 70 - strips["h"], strips)

    c.showPage()

    # ── PAGE 3: JAR ──
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(PRI)
    c.drawString(36, ph - 36, "GenoMAX² — LABEL RENDERS · ACTUAL SIZE · V3 SIGNATURE")
    c.setFont("Helvetica", 7)
    c.setFillColor(TER)
    c.drawString(36, ph - 48, "JAR format (8.5\" × 2\")")

    jar = [l for l in LABELS if l["fmt"] == "JAR"][0]
    c.drawString(36, ph - 66, jar["title"])
    draw_label(c, 36, ph - 70 - jar["h"], jar)

    c.save()
    print(f"PDF saved: {OUTPUT}")
    print(f"Labels rendered: {len(LABELS)}")
    for l in LABELS:
        print(f"  {l['title']}: {l['os']} · {l['name'].replace(chr(10), ' ')}")


if __name__ == "__main__":
    main()
