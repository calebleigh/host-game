"""Smoke test: loads the game at phone and desktop sizes, starts a run, picks cards, places a virus,
opens every screen, and saves screenshots to tools/shots/. Prints any page errors (should be none).

Usage:  python tools/smoke.py
"""
import asyncio, pathlib
from playwright.async_api import async_playwright

ROOT = pathlib.Path(__file__).resolve().parent
PAGE = (ROOT.parent / "www" / "index.html").as_uri()
SHOTS = ROOT / "shots"; SHOTS.mkdir(exist_ok=True)

async def run(b, w, h, name, scheme):
    pg = await b.new_page(viewport={"width": w, "height": h}, color_scheme=scheme)
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    await pg.goto(PAGE); await pg.wait_for_timeout(400)
    await pg.screenshot(path=str(SHOTS / f"{name}-1-intro.png"))
    await pg.click("#introGo"); await pg.wait_for_timeout(300)
    await pg.screenshot(path=str(SHOTS / f"{name}-2-menu.png"))
    await pg.click("#mSettings"); await pg.wait_for_timeout(200)
    await pg.screenshot(path=str(SHOTS / f"{name}-3-settings.png")); await pg.click("#settingsBack")
    await pg.click("#mCodex"); await pg.wait_for_timeout(200)
    await pg.screenshot(path=str(SHOTS / f"{name}-4-codex.png")); await pg.click("#codexBack")
    await pg.click(".bar-btn.primary"); await pg.wait_for_timeout(300)
    cards = await pg.locator(".pcard").all()
    await cards[0].click(); await (await pg.locator(".pcard").all())[3].click(); await pg.click("#cardsGo")
    await pg.wait_for_timeout(300)
    box = await pg.locator("#cv").bounding_box()
    for i in range(60):
        await pg.mouse.click(box["x"] + box["width"] * ((i * 0.137) % 1 * 0.8 + 0.1), box["y"] + box["height"] * ((i * 0.311) % 1 * 0.6 + 0.25))
        if await pg.evaluate("window.__host.R.phase") == "run": break
    await pg.wait_for_timeout(5000)
    await pg.screenshot(path=str(SHOTS / f"{name}-5-arena.png"))
    await pg.locator(".cardchip").first.click(); await pg.wait_for_timeout(200)
    await pg.screenshot(path=str(SHOTS / f"{name}-6-cards.png"))
    # abandon from the main menu (two taps), then Spend DNA on the run summary
    await pg.click("#settingsBtn"); await pg.click("#toMenu"); await pg.wait_for_timeout(200)
    ab = pg.locator(".bar-btn.quiet", has_text="Abandon"); await ab.click(); await ab.click(); await pg.wait_for_timeout(300)
    await pg.screenshot(path=str(SHOTS / f"{name}-7-runover.png"))
    await pg.click("#ovShop"); await pg.wait_for_timeout(200)
    await pg.screenshot(path=str(SHOTS / f"{name}-8-evolve.png"))
    print(name, "page errors:", errs or "none")
    await pg.close()

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        await run(b, 412, 900, "phone", "light")
        await run(b, 412, 560, "short-phone", "dark")
        await run(b, 1300, 820, "desktop", "light")
        await b.close()
asyncio.run(main())
