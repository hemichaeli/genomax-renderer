"""Capture label renders as PDF using Playwright + Chrome headless."""
import subprocess, time, os, signal

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "design-system", "outputs")

# Start the server
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
        page = browser.new_page()

        # Capture hi-res label renders as PDF
        page.goto("http://localhost:4999/outputs/label-renders-hires.html", wait_until="networkidle")
        page.pdf(
            path=os.path.join(OUTPUT_DIR, "label-renders-final.pdf"),
            format="A3",
            print_background=True,
            margin={"top": "0.5in", "bottom": "0.5in", "left": "0.5in", "right": "0.5in"}
        )
        print("PDF saved: label-renders-final.pdf")

        # Also capture as PNG screenshots for direct viewing
        page.set_viewport_size({"width": 900, "height": 6000})
        page.screenshot(
            path=os.path.join(OUTPUT_DIR, "label-renders-full.png"),
            full_page=True
        )
        print("PNG saved: label-renders-full.png")

        browser.close()
finally:
    server.terminate()
    server.wait()

print("Done.")
