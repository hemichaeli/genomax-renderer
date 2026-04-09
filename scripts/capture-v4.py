"""Capture V4 calibration labels — both versions A (Plex) and B (Inter)."""
import subprocess, time, os

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "design-system", "outputs", "renders-v4")
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
        page = browser.new_page(viewport={"width": 1200, "height": 800}, device_scale_factor=2)
        page.goto("http://localhost:4999/outputs/label-renders-v4.html", wait_until="networkidle")
        time.sleep(2)

        # Capture each label in both sections
        sections = page.query_selector_all(".section")
        for si, sec in enumerate(sections):
            version = "A_Plex" if si == 0 else "B_Inter"
            cards = sec.query_selector_all(".card")
            for ci, card in enumerate(cards):
                lbl = card.query_selector(".lbl")
                if lbl:
                    fname = f"{version}_{ci+1:02d}.png"
                    lbl.screenshot(path=os.path.join(OUTPUT_DIR, fname))
                    print(f"Saved: {fname}")

        # Also full page
        page.set_viewport_size({"width": 1200, "height": 800})
        page.screenshot(path=os.path.join(OUTPUT_DIR, "full_page.png"), full_page=True)
        print("Saved: full_page.png")

        browser.close()
finally:
    server.terminate()
    server.wait()

print("Done.")
