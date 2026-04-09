"""Capture DROPPER and JAR at 3x resolution for print readability check."""
import subprocess, time, os

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "design-system", "outputs", "readability-check")
os.makedirs(OUTPUT_DIR, exist_ok=True)

server = subprocess.Popen(
    "npx serve design-system -l 4999",
    cwd=os.path.dirname(os.path.dirname(__file__)),
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    shell=True
)
time.sleep(3)

try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        # 3x scale for print-level detail
        page = browser.new_page(viewport={"width": 1000, "height": 800}, device_scale_factor=3)
        page.goto("http://localhost:4999/outputs/back-label-unified.html", wait_until="networkidle")
        time.sleep(2)

        labels = page.query_selector_all(".bl")
        # Index 3 = DROPPER, Index 4 = JAR
        for idx, name in [(3, "DROPPER_3x"), (4, "JAR_3x")]:
            if idx < len(labels):
                labels[idx].screenshot(path=os.path.join(OUTPUT_DIR, f"{name}_full.png"))
                print(f"Saved: {name}_full.png")

        # Now crop specific zones at even higher detail
        # DROPPER: warnings + ingredients area (bottom half)
        dropper = labels[3]
        box = dropper.bounding_box()
        # Bottom 40% of dropper
        page.screenshot(
            path=os.path.join(OUTPUT_DIR, "DROPPER_3x_bottom.png"),
            clip={"x": box["x"], "y": box["y"] + box["height"]*0.55, "width": box["width"], "height": box["height"]*0.45}
        )
        print("Saved: DROPPER_3x_bottom.png")

        # DROPPER: CTA area (middle)
        page.screenshot(
            path=os.path.join(OUTPUT_DIR, "DROPPER_3x_cta.png"),
            clip={"x": box["x"], "y": box["y"] + box["height"]*0.38, "width": box["width"], "height": box["height"]*0.25}
        )
        print("Saved: DROPPER_3x_cta.png")

        # DROPPER: context anchor
        page.screenshot(
            path=os.path.join(OUTPUT_DIR, "DROPPER_3x_context.png"),
            clip={"x": box["x"], "y": box["y"] + box["height"]*0.28, "width": box["width"], "height": box["height"]*0.12}
        )
        print("Saved: DROPPER_3x_context.png")

        # JAR: full + bottom half (warnings/ingredients)
        jar = labels[4]
        jbox = jar.bounding_box()
        page.screenshot(
            path=os.path.join(OUTPUT_DIR, "JAR_3x_bottom.png"),
            clip={"x": jbox["x"], "y": jbox["y"] + jbox["height"]*0.5, "width": jbox["width"], "height": jbox["height"]*0.5}
        )
        print("Saved: JAR_3x_bottom.png")

        # JAR: context anchor
        page.screenshot(
            path=os.path.join(OUTPUT_DIR, "JAR_3x_context.png"),
            clip={"x": jbox["x"], "y": jbox["y"] + jbox["height"]*0.25, "width": jbox["width"], "height": jbox["height"]*0.15}
        )
        print("Saved: JAR_3x_context.png")

        browser.close()
finally:
    server.terminate()
    server.wait()

print("Done.")
