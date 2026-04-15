#!/usr/bin/env python3
"""
GENOMAX2_HERO_12_PRODUCTION_LOCKED
Renders 12 Hero SKUs x MAXimo²/MAXima² with function-first naming.
"""
import json, sys, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import importlib.util
_spec = importlib.util.spec_from_file_location("v7", str(Path(__file__).parent / "render-production-v7.py"))
v7 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(v7)
FMT = v7.FMT; render_front = v7.render_front; render_back = v7.render_back; CL = v7.CL
from reportlab.pdfgen import canvas
from PIL import Image

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "design-system" / "data"

HERO_CONFIG = {
    "CV-01": {"fn": "Lipid Regulation Module",         "fmt": "BOTTLE"},
    "CV-02": {"fn": "Calcium Regulation Module",       "fmt": "BOTTLE"},
    "GL-01": {"fn": "Glucose Regulation Module",       "fmt": "DROPPER"},
    "GL-02": {"fn": "Insulin Sensitivity Module",      "fmt": "BOTTLE"},
    "MT-01": {"fn": "Cellular Energy Module",          "fmt": "BOTTLE"},
    "MT-09": {"fn": "Muscle Protein Synthesis Module",  "fmt": "POUCH"},
    "IN-01": {"fn": "Inflammatory Response Module",    "fmt": "BOTTLE"},
    "IN-02": {"fn": "Systemic Inflammation Module",    "fmt": "BOTTLE"},
    "SL-01": {"fn": "Sleep Initiation Module",         "fmt": "BOTTLE"},
    "HR-01": {"fn": "Cortisol Regulation Module",      "fmt": "BOTTLE"},
}

def find_hero_skus():
    """Find Hero SKUs in JSON data, both MAXimo and MAXima."""
    results = []
    for sys_name in ["maximo", "maxima"]:
        fp = DATA / f"production-labels-{sys_name}-v4.json"
        with open(fp, encoding="utf-8") as f:
            data = json.load(f)
        seen = set()
        for sku in data["skus"]:
            mc = sku["_meta"]["module_code"]
            fmt = sku["format"]["label_format"]
            if mc in HERO_CONFIG and fmt == HERO_CONFIG[mc]["fmt"]:
                key = f"{sys_name}_{mc}"
                if key not in seen:
                    seen.add(key)
                    results.append((sys_name, sku))
    return results

def render_hero_sku(sku, sys_name, out_base):
    """Render one Hero SKU with function-first naming."""
    mc = sku["_meta"]["module_code"]
    hero = HERO_CONFIG[mc]
    fmt = sku["format"]["label_format"]
    if fmt not in FMT: return None

    f = FMT[fmt]
    accent = CL["axmo"] if "MAXimo" in sku["_meta"]["os"] else CL["axma"]
    cw, ch = f["cw"], f["ch"]
    st = "MO" if "MAXimo" in sku["_meta"]["os"] else "MA"
    fn_safe = hero["fn"].replace(" ", "_")[:40]
    out_dir = out_base / fmt / f"{mc}_{st}_{fn_safe}"
    out_dir.mkdir(parents=True, exist_ok=True)

    for side in ["front", "back"]:
        pdf_p = out_dir / f"{side}.pdf"
        cv = canvas.Canvas(str(pdf_p), pagesize=(cw, ch))
        cv.setAuthor("GenoMAX\u00b2 HERO_12 PRODUCTION LOCKED")
        if side == "front":
            render_front(cv, sku, fmt, accent)
        else:
            render_back(cv, sku, fmt, accent)
        cv.setFillColor(CL["t3"]); cv.setFont("Mono", 4)
        cv.drawString(4, 4, f"HERO_12 | {mc} | {sku['_meta']['os']} | {fmt} | {side.upper()} | {hero['fn']}")
        cv.save()

        import fitz
        doc = fitz.open(str(pdf_p)); page = doc[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
        jpg_p = out_dir / f"{side}.jpg"
        Image.frombytes("RGB", [pix.width, pix.height], pix.samples).save(str(jpg_p), "JPEG", quality=92)
        doc.close()

    return out_dir

def main():
    # Auto-number output directory
    ds = BASE / "design-system"
    existing = sorted(ds.glob("v7-preview-*"))
    nn = 1
    for d in existing:
        try:
            n = int(d.name.split("-")[-1])
            if n >= nn: nn = n + 1
        except: pass
    out_base = ds / f"v7-preview-{nn:02d}"

    print("=" * 70)
    print("GENOMAX2_HERO_12_PRODUCTION_LOCKED")
    print(f"Output: {out_base}")
    print("=" * 70)

    heroes = find_hero_skus()
    print(f"\nFound {len(heroes)} Hero SKUs to render\n")

    rendered = 0
    qa_table = []
    for sys_name, sku in sorted(heroes, key=lambda x: x[1]["_meta"]["module_code"]):
        mc = sku["_meta"]["module_code"]
        os_name = sku["_meta"]["os"]
        fmt = sku["format"]["label_format"]
        hero = HERO_CONFIG[mc]
        print(f"  {mc} | {os_name:8s} | {fmt:7s} | {hero['fn']}", end="")

        result = render_hero_sku(sku, sys_name, out_base)
        if result:
            rendered += 1
            qa_table.append({
                "module": mc, "os": os_name, "format": fmt,
                "function_name": hero["fn"], "status": "RENDERED",
            })
            print(" OK")
        else:
            print(" FAIL")

    # QA Summary
    print(f"\n{'='*70}")
    print(f"{'Module':<8}| {'OS':<10}| {'Format':<8}| {'Function Name':<35}| Status")
    print(f"{'-'*8}|{'-'*11}|{'-'*9}|{'-'*36}|{'-'*8}")
    for r in qa_table:
        print(f"{r['module']:<8}| {r['os']:<10}| {r['format']:<8}| {r['function_name']:<35}| {r['status']}")

    print(f"\nTOTAL: {rendered} labels rendered")
    print(f"Output: {out_base}")
    print(f"\nBatch: GENOMAX2_HERO_12_PRODUCTION_LOCKED")

if __name__ == "__main__":
    main()
