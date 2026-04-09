"""Capture unified back label renders — all 5 formats, same Berberine data."""
import subprocess, time, os

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "design-system", "outputs", "renders-back-unified")
os.makedirs(OUTPUT_DIR, exist_ok=True)

server = subprocess.Popen(
    "npx serve design-system -l 4999",
    cwd=os.path.dirname(os.path.dirname(__file__)),
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    shell=True
)
time.sleep(3)

NAMES = ["01_BOTTLE", "02_POUCH", "03_STRIPS", "04_DROPPER", "05_JAR"]

try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1000, "height": 800}, device_scale_factor=2)
        page.goto("http://localhost:4999/outputs/back-label-unified.html", wait_until="networkidle")
        time.sleep(2)

        labels = page.query_selector_all(".bl")
        for i, lbl in enumerate(labels):
            if i < len(NAMES):
                lbl.screenshot(path=os.path.join(OUTPUT_DIR, f"{NAMES[i]}.png"))
                print(f"Saved: {NAMES[i]}.png")

        browser.close()
finally:
    server.terminate()
    server.wait()

print("Done.")
