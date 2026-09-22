"""
Scroll-reveal regression test.

THE BUG THIS EXISTS TO CATCH
----------------------------
The reveal observer originally used `threshold: 0.15` — fire when 15% of the
section's area is on screen. That ratio is height-dependent: a section taller
than ~6.6x the viewport can never reach 15%, so the observer never fires, `.in`
is never added, and the CSS that hid the section is never undone. The section
stays at opacity:0 forever.

It shipped fine and then broke later, silently, when the Experience section grew
past 4,692px from added photos. On a 390x667 phone the entire section vanished.

A `:visible` check does NOT catch this — Playwright counts opacity:0 as visible.
This test asserts COMPUTED OPACITY, which is the only thing that actually tells
you a visitor can see the content.

Run:  python -m http.server 8765   (from the repo root)
      python tests/reveal-regression.py
"""
from playwright.sync_api import sync_playwright

CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe"
BASE = "http://localhost:8765/"
PAGES = ["index.html", "resume.html", "linkedin.html"]

# Short viewports are the dangerous ones: the shorter the window, the taller a
# section is relative to it, and the easier it is to starve a ratio threshold.
VIEWPORTS = [
    (1280, 900, "desktop"),
    (1512, 700, "laptop, short window"),
    (1280, 600, "very short window"),
    (768, 1024, "tablet"),
    (390, 844, "iPhone 14"),
    (390, 667, "iPhone SE"),
    (360, 640, "small android"),
]

failures = []

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME)
    for page_name in PAGES:
        print("\n" + page_name)
        for vw, vh, label in VIEWPORTS:
            pg = browser.new_page(viewport={"width": vw, "height": vh})
            pg.goto(BASE + page_name, wait_until="networkidle")

            # walk the page the way a person would, so every observer gets a chance
            height = pg.evaluate("() => document.body.scrollHeight")
            y = 0
            while y < height:
                y += int(vh * 0.6)
                pg.evaluate(f"window.scrollTo(0,{y})")
                pg.wait_for_timeout(70)
            pg.wait_for_timeout(700)

            hidden = pg.evaluate("""() => [...document.querySelectorAll('main section')]
                .filter(s => parseFloat(getComputedStyle(s).opacity) < 0.99)
                .map(s => s.id || s.className)""")
            tallest = pg.evaluate("""() => Math.max(...[...document.querySelectorAll('main section')]
                .map(s => Math.round(s.getBoundingClientRect().height)))""")

            ok = not hidden
            if not ok:
                failures.append(f"{page_name} @ {vw}x{vh}: {hidden}")
            print(f"  {'PASS' if ok else 'FAIL'}  {label:22} {vw}x{vh}"
                  f"  tallest section {tallest}px  hidden: {hidden or 'none'}")
            pg.close()
    browser.close()

print("\n" + "=" * 52)
if failures:
    print("REGRESSION — sections invisible to real visitors:")
    for f in failures:
        print("  " + f)
    raise SystemExit(1)
print("EVERY SECTION VISIBLE AT EVERY VIEWPORT")
