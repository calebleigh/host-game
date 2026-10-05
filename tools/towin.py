"""How long until the game is won (all 25 worlds), playing nonstop and spending DNA after every run.
Prints the time each new best world is first reached, and the time of the first win.

Players: auto  = the game's auto-buyer for run upgrades
         eager = buys the cheapest run upgrade the moment it's affordable
DNA is spent after every run on the cheapest available perk, repeatedly (unlocks included).

Usage:  python tools/towin.py [max hours]
"""
import asyncio, os, pathlib, sys
from playwright.async_api import async_playwright

PAGE = pathlib.Path(os.environ.get("HOST_PAGE") or pathlib.Path(__file__).resolve().parent.parent / "www" / "index.html").resolve().as_uri()
HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 24

JS = """([player, hours]) => {
  const H = window.__host, G = H.G, DT = 0.25;
  for (const k in G.auto) { G.auto[k].owned = true; G.auto[k].on = k !== 'autoBuy' || player === 'auto'; }
  G.settings.autoChoose = true; H.startNewRun(); H.setSilent(true);
  const keys = Object.keys(H.UP), cost = k => H.runCost(H.UP[k], H.R.lv[k]);
  const shop = () => { for (let g = 0; g < 400; g++) { let pick = null, bc = Infinity;
    for (const k of keys) { if (H.R.lv[k] >= H.UP[k].max) continue; const c = cost(k); if (c < bc) { bc = c; pick = k; } }
    if (!pick || H.R.lf < bc || !H.buy(pick, false, true)) break; } };
  const spendDna = () => { for (let g = 0; g < 500; g++) { let best = null, bc = Infinity;
    for (const k in H.PERM) { const d = H.PERM[k]; if (G.p[k] >= d.max) continue; if (d.needsBoss !== undefined && !G.bosses[d.needsBoss]) continue;
      const c = H.upCost(d, G.p[k]); if (c < bc) { bc = c; best = k; } }
    if (!best || G.dna < bc) break; H.buyPerm(best); } };
  const marks = []; let t = 0, best = G.best, runs = G.runs, win = null;
  while (t < hours * 3600 && G.wins === 0) {
    if (H.R.phase === 'run') { H.step(DT); if (player === 'eager') shop(); }
    H.autoTick(DT); t += DT;
    if (G.runs !== runs) { runs = G.runs; spendDna(); }
    if (G.best > best) { best = G.best; marks.push([best, Math.round(t / 60), G.runs, G.p.potency]); }
  }
  if (G.wins > 0) win = Math.round(t / 60);
  H.setSilent(false);
  return { marks, win, best: G.best, runs: G.runs, minutes: Math.round(t / 60), perms: G.p }; }"""

async def one(browser, player):
    pg = await browser.new_page(); await pg.goto(PAGE); await pg.wait_for_timeout(200)
    r = await pg.evaluate(JS, [player, HOURS]); await pg.close(); return player, r

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        res = await asyncio.gather(*[one(browser, pl) for pl in ("auto", "eager")]); await browser.close()
    hm = lambda m: "%dh %02dm" % (m // 60, m % 60)
    for player, r in res:
        print(f"== {player} player: " + (f"WON after {hm(r['win'])} ({r['runs']} runs)" if r["win"] else f"no win within {HOURS:g} hours, best world {r['best']} after {r['runs']} runs"))
        for world, mins, runs, pot in r["marks"]:
            print(f"   world {world:>2} first reached at {hm(mins)}  (run {runs}, Potent genome {pot})")
        print("   final perks:", r["perms"])

asyncio.run(main())
