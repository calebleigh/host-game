"""Play-style simulator: fresh runs (no DNA perks) with different player habits, to see how often world 1
gets cleared, how long it takes in real time, and how far a run goes.

Habits:
  buying     eager = buy the cheapest upgrade the moment it's affordable
             auto  = the game's own auto-buyer
             slow  = shop (cheapest first) once every 30 seconds
             none  = never buy upgrades
  decisions  1s or 15s before a virus is placed or cards are picked (the world is paused while waiting,
             so this only changes real time, not difficulty)
  placement  easy   = the game's "Easiest targets" auto placement
             random = a random valid host (a worst case)

Usage:  python tools/playstyles.py [runs per style] [max minutes per run]
"""
import asyncio, pathlib, sys, statistics, itertools
from playwright.async_api import async_playwright

PAGE = (pathlib.Path(__file__).resolve().parent.parent / "www" / "index.html").as_uri()
RUNS = int(sys.argv[1]) if len(sys.argv) > 1 else 10
MAX_MIN = float(sys.argv[2]) if len(sys.argv) > 2 else 30

JS = """([buying, wait, placement, maxMin]) => {
  const H = window.__host, G = H.G, DT = 0.25;
  for (const k in G.p) G.p[k] = 0;
  for (const k in G.auto) { G.auto[k].owned = true; G.auto[k].on = k !== 'autoBuy' || buying === 'auto'; }
  G.settings.autoChoose = true; G.settings.placeStyle = 'easy';
  H.startNewRun(); H.setSilent(true);
  const keys = Object.keys(H.UP), cost = k => H.runCost(H.UP[k], H.R.lv[k]);
  const shop = () => { for (let g = 0; g < 400; g++) {
    let pick = null, bc = Infinity;
    for (const k of keys) { if (H.R.lv[k] >= H.UP[k].max) continue; const c = cost(k); if (c < bc) { bc = c; pick = k; } }
    if (!pick || H.R.lf < bc || !H.buy(pick, false, true)) break; } };
  const start = G.runs; let t = 0, waited = 0, shopT = 0, w1 = null, worldAt = 0;
  while (t < maxMin * 60 && G.runs === start) {
    const ph = H.R.phase;
    if (ph === 'run') {
      H.step(DT); H.autoTick(DT);
      if (buying === 'eager') shop();
      if (buying === 'slow' && (shopT += DT) >= 30) { shopT = 0; shop(); }
    } else if (ph === 'pick' || ph === 'cards' || ph === 'start') {
      // the player (or Auto) takes `wait` seconds to decide; the world is paused meanwhile
      if ((waited += DT) >= wait) {
        waited = 0;
        if (ph === 'pick' && placement === 'random') {
          const ok = H.R.hosts.filter(h => !h.dead && !h.vacc && !h.sentinel);
          H.place(ok[Math.floor(Math.random() * ok.length)]);
        } else H.autoTick(DT);
      }
    } else H.autoTick(DT);
    t += DT;
    if (H.R.world > 1 && w1 === null) w1 = t;
    if (G.runs === start) worldAt = H.R.world;
  }
  H.setSilent(false);
  return { w1, world: worldAt, minutes: t / 60, ended: G.runs !== start }; }"""

async def one(browser, style, sem):
    async with sem:
        pg = await browser.new_page()
        await pg.goto(PAGE); await pg.wait_for_timeout(200)
        r = await pg.evaluate(JS, [*style, MAX_MIN])
        await pg.close()
        return style, r

async def main():
    styles = list(itertools.product(["eager", "auto", "slow", "none"], [1, 15], ["easy", "random"]))
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        sem = asyncio.Semaphore(8)
        results = await asyncio.gather(*[one(browser, s, sem) for s in styles for _ in range(RUNS)])
        await browser.close()
    print(f"{RUNS} fresh runs per style (no DNA perks), runs capped at {MAX_MIN:g} minutes\n")
    print(f"{'buying':7} {'wait':>4} {'placement':9} | {'clears world 1':>14} | {'world 1 time (median, slowest)':>30} | {'run reaches (median, best)':>26}")
    for s in styles:
        rs = [r for st, r in results if st == s]
        cleared = [r["w1"] for r in rs if r["w1"] is not None]
        worlds = sorted(r["world"] for r in rs)
        fmt = lambda x: f"{int(x // 60)}m {int(x % 60):02d}s"
        t1 = f"{fmt(statistics.median(cleared))}, {fmt(max(cleared))}" if cleared else "never"
        print(f"{s[0]:7} {str(s[1]) + 's':>4} {s[2]:9} | {len(cleared):>6} of {len(rs):<5} | {t1:>30} | {'world ' + str(int(statistics.median(worlds))) + ', world ' + str(worlds[-1]):>26}")

asyncio.run(main())
