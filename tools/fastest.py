"""Fastest world 1 for a brand-new player (no DNA): tries several buying strategies and two placement
methods, with 1-second decisions, and reports how long world 1 takes.

Buying:     cheapest = cheapest upgrade first      damage = Virulence/Replication/Stacking/Tempo/Wither first
            spread   = Bounce/Reach/Contagion/Split first, then damage      auto = the game's auto-buyer
Placement:  easy = the game's "Easiest targets"
            best = try every host as patient zero (same dice each try) and keep the fastest clear

Usage:  python tools/fastest.py [maps per case]
"""
import asyncio, os, pathlib, sys, statistics
from playwright.async_api import async_playwright

PAGE = pathlib.Path(os.environ.get("HOST_PAGE") or pathlib.Path(__file__).resolve().parent.parent / "www" / "index.html").resolve().as_uri()
MAPS = int(sys.argv[1]) if len(sys.argv) > 1 else 8

JS = """([policy, placement, mapSeed]) => {
  const H = window.__host, G = H.G, DT = 0.25, WAIT = 1;
  let seed = mapSeed;
  Math.random = () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
  for (const k in G.p) G.p[k] = 0;
  for (const k in G.auto) { G.auto[k].owned = true; G.auto[k].on = k !== 'autoBuy' || policy === 'auto'; }
  G.settings.autoChoose = true; G.settings.placeStyle = 'easy';
  H.startNewRun(); H.setSilent(true);
  const keys = Object.keys(H.UP), cost = k => H.runCost(H.UP[k], H.R.lv[k]);
  const prefs = { damage: ['virulence', 'replication', 'stacking', 'tempo', 'wither'], spread: ['bounce', 'reach', 'contagion', 'split'] };
  const cheapestOf = list => { let pick = null, bc = Infinity; for (const k of list) { if (H.R.lv[k] >= H.UP[k].max) continue; const c = cost(k); if (c < bc) { bc = c; pick = k; } } return [pick, bc]; };
  const shop = () => { if (policy === 'auto') return; for (let g = 0; g < 400; g++) {
      let [pick, bc] = prefs[policy] ? cheapestOf(prefs[policy]) : [null, Infinity];
      if (policy === 'spread' && (!pick || H.R.lf < bc)) [pick, bc] = cheapestOf(prefs.damage);
      if (!pick || H.R.lf < bc) [pick, bc] = cheapestOf(keys);
      if (!pick || H.R.lf < bc || !H.buy(pick, false, true)) break; } };
  // play from now until world 1 falls or the run ends; returns seconds (wall clock, including 1s decisions)
  const play = (limit) => { let t = 0, waited = 0; const start = G.runs;
    while (t < limit && G.runs === start && H.R.world === 1) {
      const ph = H.R.phase;
      if (ph === 'run') { H.step(DT); shop(); H.autoTick(DT); }
      else if ((waited += DT) >= WAIT) { waited = 0; H.autoTick(DT); }
      t += DT; }
    return H.R.world > 1 ? t : null; };
  // the opening card pick, then the first placement
  let t0 = 0; while (H.R.phase === 'start') { t0 += WAIT; H.autoTick(WAIT); }
  t0 += WAIT;
  if (placement === 'best') {
    const snap = H.snapshot(), s0 = seed; let best = null, bestIdx = -1;
    H.R.hosts.forEach((h, i) => { if (h.dead || h.vacc || h.sentinel) return;
      H.restore(snap); seed = s0; H.place(H.R.hosts[i]); const t = play(best === null ? 1800 : best);
      if (t !== null && (best === null || t < best)) { best = t; bestIdx = i; } });
    H.restore(snap); seed = s0;
    if (bestIdx >= 0) H.place(H.R.hosts[bestIdx]);
  }
  const t = play(1800); H.setSilent(false);
  return t === null ? null : t + t0; }"""

async def one(browser, sem, case):
    async with sem:
        pg = await browser.new_page(); await pg.goto(PAGE); await pg.wait_for_timeout(200)
        r = await pg.evaluate(JS, list(case)); await pg.close(); return case, r

async def main():
    cases = [(pol, plc, 7000 + m) for pol in ("cheapest", "damage", "spread", "auto") for plc in ("easy", "best") for m in range(MAPS)]
    async with async_playwright() as p:
        browser = await p.chromium.launch(); sem = asyncio.Semaphore(8)
        res = await asyncio.gather(*[one(browser, sem, c) for c in cases]); await browser.close()
    fmt = lambda s: "%dm %02ds" % (s // 60, s % 60)
    print(f"World 1, brand-new player (no DNA), 1-second decisions, {MAPS} maps per case\n")
    print(f"{'buying':9} {'placement':9} | {'cleared':>7} | {'fastest':>8} | {'median':>8} | {'slowest':>8}")
    for pol in ("cheapest", "damage", "spread", "auto"):
        for plc in ("easy", "best"):
            ts = sorted(r for (c, r) in res if c[0] == pol and c[1] == plc and r is not None)
            n = sum(1 for (c, r) in res if c[0] == pol and c[1] == plc)
            print(f"{pol:9} {plc:9} | {len(ts):>3} of {n:<2}| " + (f"{fmt(ts[0]):>8} | {fmt(statistics.median(ts)):>8} | {fmt(ts[-1]):>8}" if ts else "never"))
    best = {}
    for (c, r) in res:
        if r is not None: best[c[2]] = min(best.get(c[2], 1e9), r)
    if best:
        v = sorted(best.values())
        print(f"\nBest of everything, per map: fastest {fmt(v[0])}, median {fmt(statistics.median(v))}, slowest {fmt(v[-1])}")

asyncio.run(main())
