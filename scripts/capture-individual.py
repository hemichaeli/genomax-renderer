"""Capture each label as individual PNG at 2x resolution."""
import subprocess, time, os

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "design-system", "outputs", "renders")
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
        page = browser.new_page(viewport={"width": 900, "height": 800}, device_scale_factor=2)

        page.goto("http://localhost:4999/outputs/label-renders-hires.html", wait_until="networkidle")

        renders = page.query_selector_all(".render")
        for i, r in enumerate(renders):
            tag = r.query_selector(".render-tag")
            tag_text = tag.inner_text().replace("\n", " ").strip() if tag else f"label_{i+1}"

            # Screenshot just the label-wrap (the actual label with shadow)
            label_wrap = r.query_selector(".label-wrap")
            if label_wrap:
                filename = f"{i+1:02d}_{tag_text[:40].replace(' ', '_').replace('·','').replace('"','')}.png"
                label_wrap.screenshot(path=os.path.join(OUTPUT_DIR, filename))
                print(f"Saved: {filename}")

        browser.close()
finally:
    server.terminate()
    server.wait()

print("Done — all individual label renders saved.")
