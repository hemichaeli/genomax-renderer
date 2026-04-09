"""
GenoMAX² — Production PDF Renderer
====================================
Generates print-ready PDFs for all 168 SKUs using V4 Final (Inter) design.
Uses Playwright to render HTML labels at actual print dimensions.

Output:
  design-system/production/maximo/  (84 PDFs)
  design-system/production/maxima/  (84 PDFs)
  design-system/production/manifest.json
"""

import json
import os
import subprocess
import time
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROD_DIR = os.path.join(BASE, "design-system", "production")
DATA_DIR = os.path.join(BASE, "design-system", "data")

# Format dimensions at 96dpi
DIMS = {
    "BOTTLE":  {"w": 576, "h": 240, "w_in": 6, "h_in": 2.5},
    "JAR":     {"w": 816, "h": 192, "w_in": 8.5, "h_in": 2},
    "POUCH":   {"w": 480, "h": 384, "w_in": 5, "h_in": 4},
    "DROPPER": {"w": 192, "h": 384, "w_in": 2, "h_in": 4},
    "STRIPS":  {"w": 384, "h": 624, "w_in": 4, "h_in": 6.5},
}

# V4 Final type scale per format
SCALE = {
    "BOTTLE":  {"bn": 14, "bm": 7, "z2": 8, "ds": 10, "bio": 7, "vs": 15, "ml": 6, "mv": 8, "z7": 7, "aw": 90, "pad": "8px 24px 0", "cpad": "5px 24px 0", "z7pad": "6px 24px"},
    "JAR":     {"bn": 12, "bm": 6, "z2": 7, "ds": 9, "bio": 6, "vs": 13, "ml": 5, "mv": 7, "z7": 6.5, "aw": 80, "pad": "6px 20px 0", "cpad": "3px 20px 0", "z7pad": "5px 20px"},
    "POUCH":   {"bn": 14, "bm": 7, "z2": 8, "ds": 11, "bio": 7, "vs": 16, "ml": 6, "mv": 9, "z7": 7, "aw": 90, "pad": "10px 24px 0", "cpad": "8px 24px 0", "z7pad": "7px 24px"},
    "DROPPER": {"bn": 9, "bm": 5, "z2": 5, "ds": 7, "bio": 5, "vs": 11, "ml": 5, "mv": 6, "z7": 5, "aw": 50, "pad": "6px 14px 0", "cpad": "4px 14px 0", "z7pad": "5px 14px"},
    "STRIPS":  {"bn": 14, "bm": 7, "z2": 8, "ds": 11, "bio": 7, "vs": 18, "ml": 7, "mv": 10, "z7": 7, "aw": 90, "pad": "12px 24px 0", "cpad": "8px 24px 0", "z7pad": "7px 24px"},
}


def compute_name_size(name, fmt):
    nl = len(name)
    base = {"BOTTLE": 42, "JAR": 28, "POUCH": 38, "DROPPER": 20, "STRIPS": 44}
    ns = base.get(fmt, 42)
    is_narrow = fmt == "DROPPER"
    is_jar = fmt == "JAR"
    is_tall = fmt in ("STRIPS", "POUCH", "DROPPER")
    if nl > 38:
        ns = 10 if is_narrow else (20 if is_jar else (26 if is_tall else 22))
    elif nl > 25:
        ns = 14 if is_narrow else (24 if is_jar else (32 if is_tall else 28))
    elif nl > 18:
        ns = 16 if is_narrow else (26 if is_jar else (36 if is_tall else 36))
    return ns


def build_label_html(sku):
    fp = sku["front_panel"]
    fmt_key = sku["format"]["label_format"]
    fmt = DIMS.get(fmt_key, DIMS["BOTTLE"])
    sc = SCALE.get(fmt_key, SCALE["BOTTLE"])
    is_narrow = fmt_key == "DROPPER"
    is_jar = fmt_key == "JAR"
    is_tall = fmt_key in ("STRIPS", "POUCH", "DROPPER")

    os_name = fp["zone_5"]["variant_name"]
    ac = "mxo" if "MAXimo" in os_name else "mxa"
    code = fp["zone_1"]["module_code"]
    mod_prefix = code.split("-")[0] if "-" in code else code[:2]
    name = fp["zone_3"]["ingredient_name"]
    desc = fp["zone_4"]["descriptor"]
    bio = fp["zone_4"]["biological_system"]
    form_val = fp["zone_6"]["type"]["value"]
    func_val = fp["zone_6"]["function"]["value"]
    status_val = fp["zone_6"]["status"]["value"]
    version = fp["zone_7"]["version_info"]
    qty = fp["zone_7"]["net_quantity"]

    ns = compute_name_size(name, fmt_key)
    nl = len(name)
    lh = "1.02" if nl > 25 else "0.95"
    tracking = "-0.04em" if nl > 25 else "-0.03em"

    # Z6
    if is_narrow:
        func_short = " ".join(func_val.split()[:2])
        z6 = f'''<div class="z6 z6v">
          <div class="z6c" style="flex-direction:row;gap:5px;align-items:baseline"><span class="z6l" style="font-size:{sc["ml"]}px">TYPE</span><span class="z6x" style="font-size:{sc["mv"]}px">{form_val}</span></div>
          <div class="z6c" style="flex-direction:row;gap:5px;align-items:baseline"><span class="z6l" style="font-size:{sc["ml"]}px">FUNC</span><span class="z6x" style="font-size:{sc["mv"]}px">{func_short}</span></div>
          <div class="z6c" style="flex-direction:row;gap:5px;align-items:baseline"><span class="z6l" style="font-size:{sc["ml"]}px">STATUS</span><span class="z6x" style="font-size:{sc["mv"]}px">{status_val}</span></div>
        </div>'''
    else:
        z6 = f'''<div class="z6">
          <div class="z6c"><span class="z6l" style="font-size:{sc["ml"]}px">TYPE</span><span class="z6x" style="font-size:{sc["mv"]}px">{form_val}</span></div>
          <div class="z6c"><span class="z6l" style="font-size:{sc["ml"]}px">FUNCTION</span><span class="z6x" style="font-size:{sc["mv"]}px">{func_val}</span></div>
          <div class="z6c"><span class="z6l" style="font-size:{sc["ml"]}px">STATUS</span><span class="z6x" style="font-size:{sc["mv"]}px">{status_val}</span></div>
        </div>'''

    # Z5+Z6 combined for JAR
    if is_jar:
        z56 = f'''<div style="display:flex;justify-content:center;align-items:center;gap:28px">
          <div style="text-align:center"><div class="z5n" style="font-size:{sc["vs"]}px">{os_name}</div><div class="z5a {ac}" style="width:{sc["aw"]}px;height:8px"></div></div>
          <div class="z6" style="gap:20px">
            <div class="z6c"><span class="z6l" style="font-size:{sc["ml"]}px">TYPE</span><span class="z6x" style="font-size:{sc["mv"]}px">{form_val}</span></div>
            <div class="z6c"><span class="z6l" style="font-size:{sc["ml"]}px">FUNCTION</span><span class="z6x" style="font-size:{sc["mv"]}px">{func_val}</span></div>
            <div class="z6c"><span class="z6l" style="font-size:{sc["ml"]}px">STATUS</span><span class="z6x" style="font-size:{sc["mv"]}px">{status_val}</span></div>
          </div>
        </div>'''
    else:
        sp_z5 = 6 if is_narrow else (12 if is_tall else 6)
        z56 = f'''<div style="text-align:center"><div class="z5n" style="font-size:{sc["vs"]}px">{os_name}</div><div class="z5a {ac}" style="width:{sc["aw"]}px;height:8px"></div></div>
        <div style="height:{sp_z5}px"></div>
        {z6}'''

    # Z7
    if is_narrow:
        z7 = f'<div class="z7 z7s" style="font-size:{sc["z7"]}px;padding:{sc["z7pad"]}"><span>{version}</span><span>{qty.replace("DIETARY SUPPLEMENT · ", "")}</span></div>'
    else:
        z7 = f'<div class="z7" style="font-size:{sc["z7"]}px;padding:{sc["z7pad"]}"><span>{version}</span><span>{qty}</span></div>'

    sp_top = 3 if is_narrow else 5
    sp_z2 = 4 if is_narrow else (3 if is_jar else (8 if is_tall else 3))
    sp_z4 = 6 if is_narrow else (3 if is_jar else (12 if is_tall else 6))
    badge_size = max(sc["bm"], 5)

    html = f'''<div class="lbl" style="width:{fmt["w"]}px;height:{fmt["h"]}px">
      <div class="ceil {ac}" style="height:3px"></div>
      <div style="padding:{sc["pad"]}">
        <div class="bz">
          <span class="bn" style="font-size:{sc["bn"]}px">GenoMAX²</span>
          <span style="display:flex;align-items:baseline;gap:6px">
            <span class="mod-badge" style="font-size:{badge_size}px">{mod_prefix}</span>
            <span class="bm" style="font-size:{sc["bm"]}px">{code}</span>
          </span>
        </div>
        <div style="height:{sp_top}px"></div>
        <div class="br"></div>
      </div>
      <div style="padding:{sc["cpad"]};display:flex;flex-direction:column;flex:1">
        <div class="z2" style="font-size:{sc["z2"]}px">BIOLOGICAL OS MODULE</div>
        <div style="height:{sp_z2}px"></div>
        <div class="z3" style="font-size:{ns}px;line-height:{lh};letter-spacing:{tracking}">{name}</div>
        <div style="height:{1 if is_jar else 2}px"></div>
        <div class="z4d" style="font-size:{sc["ds"]}px">{desc}</div>
        <div style="height:1px"></div>
        <div class="z4s" style="font-size:{sc["bio"]}px">{bio}</div>
        <div style="height:{sp_z4}px"></div>
        {z56}
        <div style="flex:1"></div>
        <div class="zd"></div>
      </div>
      {z7}
    </div>'''

    return html


def main():
    # Start serve
    server = subprocess.Popen(
        "npx serve design-system/production -l 5111",
        cwd=BASE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True
    )
    time.sleep(3)

    try:
        from playwright.sync_api import sync_playwright

        # Read template
        tpl_path = os.path.join(PROD_DIR, "label-template.html")
        with open(tpl_path, "r", encoding="utf-8") as f:
            template = f.read()

        manifest = {"version": "V4-FINAL", "generated": "2026-04-07", "systems": {}}

        for system_name in ["maximo", "maxima"]:
            data_path = os.path.join(DATA_DIR, f"production-labels-{system_name}.json")
            with open(data_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            out_dir = os.path.join(PROD_DIR, system_name)
            os.makedirs(out_dir, exist_ok=True)
            skus = data["skus"]
            system_manifest = {"total": len(skus), "labels": []}

            print(f"\n{'='*60}")
            print(f"Rendering {system_name.upper()} — {len(skus)} SKUs")

            with sync_playwright() as p:
                browser = p.chromium.launch()

                for i, sku in enumerate(skus):
                    fp = sku["front_panel"]
                    code = fp["zone_1"]["module_code"]
                    fmt_key = sku["format"]["label_format"]
                    name = fp["zone_3"]["ingredient_name"]
                    fmt = DIMS.get(fmt_key, DIMS["BOTTLE"])

                    # Build HTML
                    label_html = build_label_html(sku)

                    # Inject into template
                    escaped = json.dumps({"html": label_html})
                    page_html = template.replace("/*DATA_PLACEHOLDER*/null", escaped)

                    # Write temp file
                    temp_path = os.path.join(PROD_DIR, "_temp_label.html")
                    with open(temp_path, "w", encoding="utf-8") as tf:
                        tf.write(page_html)

                    # Render
                    page = browser.new_page(
                        viewport={"width": fmt["w"] + 40, "height": fmt["h"] + 40},
                        device_scale_factor=2
                    )
                    page.goto(f"file:///{temp_path.replace(os.sep, '/')}", wait_until="networkidle")
                    time.sleep(0.3)

                    # Safe filename
                    safe_name = name[:40].replace("/", "-").replace("\\", "-").replace(":", "-").replace('"', '').replace("'", "").replace(" ", "_")
                    filename = f"{code}_{safe_name}_{fmt_key}"

                    # Screenshot as PNG
                    lbl_el = page.query_selector(".lbl")
                    if lbl_el:
                        png_path = os.path.join(out_dir, f"{filename}.png")
                        lbl_el.screenshot(path=png_path)

                    # PDF at actual size
                    pdf_path = os.path.join(out_dir, f"{filename}.pdf")
                    page.pdf(
                        path=pdf_path,
                        width=f"{fmt['w_in']}in",
                        height=f"{fmt['h_in']}in",
                        print_background=True,
                        margin={"top": "0", "bottom": "0", "left": "0", "right": "0"}
                    )

                    page.close()

                    system_manifest["labels"].append({
                        "code": code,
                        "name": name,
                        "format": fmt_key,
                        "pdf": f"{filename}.pdf",
                        "png": f"{filename}.png",
                    })

                    progress = f"[{i+1:3d}/{len(skus)}]"
                    print(f"  {progress} {code} | {fmt_key:7s} | {name[:45]}")

                browser.close()

            manifest["systems"][system_name] = system_manifest

        # Clean temp
        temp_path = os.path.join(PROD_DIR, "_temp_label.html")
        if os.path.exists(temp_path):
            os.remove(temp_path)

        # Write manifest
        manifest_path = os.path.join(PROD_DIR, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        total = sum(s["total"] for s in manifest["systems"].values())
        print(f"\n{'='*60}")
        print(f"PRODUCTION COMPLETE: {total} labels rendered")
        print(f"Manifest: {manifest_path}")

    finally:
        server.terminate()
        server.wait()


if __name__ == "__main__":
    main()
