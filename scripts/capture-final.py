"""Capture V4 Final (Inter) labels as individual PNGs at 2x."""
import subprocess, time, os

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "design-system", "outputs", "renders-final")
os.makedirs(OUTPUT_DIR, exist_ok=True)

server = subprocess.Popen(
    "npx serve design-system -l 4999",
    cwd=os.path.dirname(os.path.dirname(__file__)),
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    shell=True
)
time.sleep(3)

NAMES = [
    "01_BOTTLE_MAXimo_BERBERINE",
    "02_BOTTLE_MAXima_LIVER_SUPPORT",
    "03_BOTTLE_MAXimo_BCAA_46char",
    "04_POUCH_MAXimo_L-GLUTAMINE",
    "05_DROPPER_MAXimo_BLOOD_SUGAR",
    "06_STRIPS_MAXima_MUSHROOM_FOCUS",
    "07_JAR_MAXimo_ENERGY_POWDER",
    "08_BOTTLE_MAXima_GUMMIES",
]

try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 800}, device_scale_factor=2)
        page.goto("http://localhost:4999/outputs/label-renders-v4.html", wait_until="networkidle")
        time.sleep(2)

        cards = page.query_selector_all(".card")
        for i, card in enumerate(cards):
            lbl = card.query_selector(".lbl")
            if lbl and i < len(NAMES):
                fname = f"{NAMES[i]}.png"
                lbl.screenshot(path=os.path.join(OUTPUT_DIR, fname))
                print(f"Saved: {fname}")

        browser.close()
finally:
    server.terminate()
    server.wait()

print("Done.")
