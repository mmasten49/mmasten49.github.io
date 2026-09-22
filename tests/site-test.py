from playwright.sync_api import sync_playwright

CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe"
BASE = "http://localhost:8765/"
OUT = "C:/Users/mastenm/AppData/Local/Temp/claude/c--Users-mastenm-OneDrive---Xavier-University-Desktop-mmasten49-github-io/66f57374-36b3-408d-9665-4b4862898d25/scratchpad/"

fails = []


def check(name, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + (("  -> " + str(detail)) if detail else ""))
    if not cond:
        fails.append(name)


with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME)

    # ---------- desktop ----------
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: errors.append("console." + m.type + ": " + m.text) if m.type == "error" else None)
    pg.goto(BASE + "index.html", wait_until="networkidle")

    print("\n[JS errors]")
    check("no page errors", not errors, errors)

    print("\n[filter]")
    bar = pg.locator(".filter-bar")
    check("filter bar injected", bar.count() == 1)
    btns = pg.locator(".filter-btn")
    check("four filter buttons", btns.count() == 4, btns.count())
    check("labels carry real counts",
          btns.nth(0).inner_text().strip().lower() == "all work (6)", btns.nth(0).inner_text())
    check("status starts at 6", "6 projects" in pg.locator(".filter-count").inner_text().lower(),
          pg.locator(".filter-count").inner_text())

    pg.locator('.filter-btn[data-key="own"]').click()
    visible = pg.locator(".work-card:visible").count()
    check("filtering to 'My Own' leaves 1 card", visible == 1, visible)
    check("status says 1 project", "1 project" in pg.locator(".filter-count").inner_text().lower(),
          pg.locator(".filter-count").inner_text())
    check("pressed state set",
          pg.locator('.filter-btn[data-key="own"]').get_attribute("aria-pressed") == "true")

    # the grid must not leave a glowing empty cell where a card used to be
    gridbg = pg.eval_on_selector(".work-grid", "el => getComputedStyle(el).backgroundColor")
    check("work-grid has no painted background", gridbg in ("rgba(0, 0, 0, 0)", "transparent"), gridbg)
    pg.locator(".work-grid").scroll_into_view_if_needed()
    pg.wait_for_timeout(250)
    pg.locator("#work").screenshot(path=OUT + "shot_filtered.png")

    pg.locator('.filter-btn[data-key="all"]').click()
    check("back to all shows 6", pg.locator(".work-card:visible").count() == 6,
          pg.locator(".work-card:visible").count())

    print("\n[lightbox]")
    check("lb-on set on <html>", "lb-on" in pg.locator("html").get_attribute("class"))
    pg.locator(".shot img").first.scroll_into_view_if_needed()
    pg.locator(".shot img").first.click()
    check("lightbox opens", pg.locator(".lightbox").count() == 1)
    check("dialog is modal", pg.locator(".lightbox").get_attribute("aria-modal") == "true")
    check("caption carried over", pg.locator(".lightbox .cap").count() == 1,
          pg.locator(".lightbox .cap").inner_text() if pg.locator(".lightbox .cap").count() else "MISSING")
    big = pg.locator(".lightbox img")
    bb = big.bounding_box()
    check("lightbox image is actually large", bb and bb["height"] > 400, bb)
    pg.keyboard.press("Escape")
    check("Escape closes it", pg.locator(".lightbox").count() == 0)

    print("\n[images]")
    for i in range(1, 14):
        pg.evaluate(f"window.scrollTo(0,{i*700})"); pg.wait_for_timeout(150)
    pg.wait_for_timeout(1200)
    pg.evaluate("window.scrollTo(0,0)"); pg.wait_for_timeout(300)
    bad = pg.evaluate("""() => [...document.images]
        .filter(i => !i.complete || i.naturalWidth === 0)
        .map(i => i.currentSrc || i.src)""")
    check("every image loaded", not bad, bad)
    natural = pg.evaluate("""() => [...document.images].map(i => ({
        src: (i.currentSrc||i.src).split('/').pop(),
        shown: Math.round(i.getBoundingClientRect().width),
        natural: i.naturalWidth }))""")
    for n in natural:
        if n["shown"]:
            print(f"      {n['src']:22} rendered {n['shown']}px  source {n['natural']}px")

    print("\n[layout: horizontal overflow]")
    for w in (1280, 860, 700, 500, 380):
        pg.set_viewport_size({"width": w, "height": 900})
        pg.wait_for_timeout(180)
        over = pg.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
        check(f"no sideways scroll at {w}px", over <= 0, f"{over}px overflow")
        if w == 380:
            pg.screenshot(path=OUT + "shot_mobile.png", full_page=False)

    # ---------- no-JS ----------
    print("\n[JavaScript disabled]")
    ctx = b.new_context(java_script_enabled=False, viewport={"width": 1280, "height": 900})
    nj = ctx.new_page()
    nj.goto(BASE + "index.html", wait_until="load")
    check("all 6 work cards visible", nj.locator(".work-card:visible").count() == 6,
          nj.locator(".work-card:visible").count())
    check("no filter bar offered", nj.locator(".filter-bar").count() == 0)
    check("no zoom cursor promised", "lb-on" not in (nj.locator("html").get_attribute("class") or ""))
    sections = nj.locator("main section:visible").count()
    check("every section still renders", sections >= 8, sections)
    check("real counter values shown", nj.locator(".num").first.inner_text().strip() == "5",
          nj.locator(".num").first.inner_text())
    check("photos still render", nj.locator(".shot img:visible").count() >= 5,
          nj.locator(".shot img:visible").count())

    b.close()

print("\n" + ("=" * 46))
print("ALL PASS" if not fails else f"{len(fails)} FAILING: " + ", ".join(fails))
