"""Balance simulator: plays Host fully automated (all automation owned, cheapest-first DNA spending)
for N simulated hours inside a headless browser and prints every run.

Usage:  python tools/sim.py 2        (simulate 2 hours)
Needs:  pip install playwright && python -m playwright install chromium
Reads:  www/index.html (uses the window.__host test hooks at the bottom of the game script)
"""
import asyncio, sys, pathlib
from playwright.async_api import async_playwright

# HOST_PAGE can point at a variant copy of the game to compare balance ideas before changing the real file
PAGE = pathlib.Path(__import__("os").environ.get("HOST_PAGE") or pathlib.Path(__file__).resolve().parent.parent / "www" / "index.html").resolve().as_uri()
BOT = """
(hours) => {
  const H = window.__host; const G = H.G;
  for (const k in G.auto) { G.auto[k].owned = true; G.auto[k].on = true; }
  G.settings.autoChoose = true; H.startNewRun();
  H.setSilent(true);
  const log = []; let t = 0, runs = G.runs, runStart = 0, w = 1, kills = 0, wT = 0, wtimes = [];
  while (t < hours * 3600) {
    if (H.R.phase === 'run') H.step(0.25);
    H.autoTick(0.25); t += 0.25;
    if (H.R.world !== w && G.runs === runs) { wtimes.push(Math.round(t - wT)); wT = t; }
    if (G.runs !== runs) {
      log.push({ run: runs, world: w, kills, min: Math.round((t - runStart) / 6) / 10, at_min: Math.round(t / 60), world_secs: wtimes.join(' ') });
      for (let g = 0; g < 200; g++) { let best = null, bc = Infinity;
        for (const k in H.PERM) { const d = H.PERM[k]; if (G.p[k] >= d.max) continue; if (d.needsBoss !== undefined && !G.bosses[d.needsBoss]) continue;
          const c = H.upCost(d, G.p[k]); if (c < bc) { bc = c; best = k; } }
        if (!best || G.dna < bc) break; H.buyPerm(best); }
      runs = G.runs; runStart = t; wT = t; wtimes = [];
    }
    w = H.R.world; kills = H.R.kills;
  }
  H.setSilent(false);
  return { log, perm: G.p, best: G.best, bosses: JSON.stringify(G.bosses), wins: G.wins };
}
"""
async def main():
    hours = float(sys.argv[1]) if len(sys.argv) > 1 else 1
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1200, "height": 800})
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto(PAGE); await pg.wait_for_timeout(500)
        r = await pg.evaluate(BOT, hours)
        for e in r["log"]: print(e)
        print("best world", r["best"], "bosses", r["bosses"], "wins", r["wins"])
        print("perms", r["perm"]); print("page errors", errs)
        await b.close()
asyncio.run(main())
