"""Setback test: does buying upgrades after a lost virus actually help? And how much does DNA move the wall?

Part 1: whenever a virus dies (and the run isn't over), the game state is saved and the next virus is played
twice from that exact point with the same dice rolls: once after spending all lifeforce (cheapest first), once
without buying. Two player types:
  eager = buys the moment anything is affordable (so has little left when a virus dies)
  saver = only shops between viruses
Part 2: best world reached at different DNA perk levels (Potent genome and Rich genome).

Usage:  python tools/setbacks.py [runs per case]
"""
import asyncio, pathlib, sys, statistics
from playwright.async_api import async_playwright

PAGE = (pathlib.Path(__file__).resolve().parent.parent / "www" / "index.html").as_uri()
RUNS = int(sys.argv[1]) if len(sys.argv) > 1 else 4

COMMON = """
  const H = window.__host, G = H.G, DT = 0.25;
  let seed = 1;   // seeded dice, so both branches of an experiment see the same rolls
  Math.random = () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
  const setup = (lvl, runSeed) => {
    seed = runSeed;
    for (const k in G.p) G.p[k] = 0;
    G.p.potency = lvl; G.p.yield = lvl; G.p.headstart = Math.min(15, lvl); G.p.incubate = Math.min(4, lvl >> 2);
    for (const k in G.auto) { G.auto[k].owned = true; G.auto[k].on = k !== 'autoBuy'; }
    G.settings.autoChoose = true; H.startNewRun(); H.setSilent(true);
  };
  const keys = Object.keys(H.UP), cost = k => H.runCost(H.UP[k], H.R.lv[k]);
  const shop = () => { let n = 0; for (let g = 0; g < 400; g++) { let pick = null, bc = Infinity;
    for (const k of keys) { if (H.R.lv[k] >= H.UP[k].max) continue; const c = cost(k); if (c < bc) { bc = c; pick = k; } }
    if (!pick || H.R.lf < bc || !H.buy(pick, false, true)) break; n++; } return n; };
  const dead = () => H.R.hosts.filter(h => h.dead).length;
"""

PART1 = "([lvl, style, runSeed]) => {" + COMMON + """
  setup(lvl, runSeed);
  // play one virus from a 'pick' state until it dies, the world falls, or the run ends
  const playVirus = () => { const w = H.R.world, lives = H.R.lives, d0 = dead(), alive0 = H.R.hosts.filter(h => !h.dead && !h.vacc).length; let t = 0;
    while (t < 1800) { if (H.R.phase === 'run') H.step(DT); H.autoTick(DT); t += DT;
      if (H.R.world !== w || H.R.phase === 'over' || H.R.phase === 'cards' || H.R.lives < lives) break; }
    const cleared = H.R.world !== w || H.R.phase === 'cards';
    return { kills: cleared ? alive0 : dead() - d0, cleared, secs: t }; };
  const events = []; const start = G.runs; let t = 0;
  while (t < 3600 && G.runs === start) {
    const lives = H.R.lives, w = H.R.world;
    if (H.R.phase === 'run') { H.step(DT); if (style === 'eager') shop(); }
    if (H.R.phase === 'pick' && H.R.lives < lives && H.R.world === w) {
      const snap = H.snapshot(), s = seed, lf = H.R.lf;
      const levels = shop(); const bought = playVirus();
      H.restore(snap); seed = s;
      const plain = playVirus();
      H.restore(snap); seed = s; shop();       // the real game continues with the purchases made
      events.push({ world: w, lf, levels, bought, plain });
    }
    H.autoTick(DT); t += DT;
  }
  H.setSilent(false); return events; }"""

PART2 = "([lvl, runSeed]) => {" + COMMON + """
  setup(lvl, runSeed); const start = G.runs; let t = 0, w = 1;
  while (t < 3600 && G.runs === start) { if (H.R.phase === 'run') { H.step(DT); shop(); } H.autoTick(DT); t += DT; if (G.runs === start) w = H.R.world; }
  H.setSilent(false); return w; }"""

async def run(browser, sem, js, arg):
    async with sem:
        pg = await browser.new_page(); await pg.goto(PAGE); await pg.wait_for_timeout(200)
        r = await pg.evaluate(js, arg); await pg.close(); return arg, r

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(); sem = asyncio.Semaphore(8)
        cases1 = [(lvl, style, 1000 + i) for lvl in (0, 10, 20) for style in ("eager", "saver") for i in range(RUNS)]
        cases2 = [(lvl, 5000 + i) for lvl in (0, 5, 10, 15, 20, 25, 30) for i in range(RUNS)]
        res1, res2 = await asyncio.gather(
            asyncio.gather(*[run(browser, sem, PART1, list(c)) for c in cases1]),
            asyncio.gather(*[run(browser, sem, PART2, list(c)) for c in cases2]))
        await browser.close()

    print(f"Part 1: next virus after a lost one, spending all lifeforce vs spending nothing ({RUNS} runs per case)\n")
    print(f"{'perks':>5} {'player':6} | {'losses':>6} | {'levels bought':>13} | {'kills, bought vs not':>21} | {'next virus clears world':>24} | {'buying did better':>17}")
    for lvl in (0, 10, 20):
        for style in ("eager", "saver"):
            ev = [e for (a, evs) in res1 if a[0] == lvl and a[1] == style for e in evs]
            if not ev:
                print(f"{lvl:>5} {style:6} | {0:>6} | (no lost viruses)"); continue
            lv = statistics.median(e["levels"] for e in ev)
            kb = statistics.mean(e["bought"]["kills"] for e in ev); kp = statistics.mean(e["plain"]["kills"] for e in ev)
            cb = sum(e["bought"]["cleared"] for e in ev); cp = sum(e["plain"]["cleared"] for e in ev)
            better = sum(e["bought"]["kills"] > e["plain"]["kills"] or (e["bought"]["cleared"] and not e["plain"]["cleared"]) for e in ev)
            print(f"{lvl:>5} {style:6} | {len(ev):>6} | {lv:>13g} | {kb:>9.1f} vs {kp:<9.1f} | {cb:>9} vs {cp:<12} | {better:>6} of {len(ev):<8}")
    print(f"\nPart 2: best world reached by DNA perk level (Potent + Rich genome, {RUNS} runs each)\n")
    for lvl in (0, 5, 10, 15, 20, 25, 30):
        ws = sorted(r for (a, r) in res2 if a[0] == lvl)
        print(f"  perks {lvl:>2}: median world {statistics.median(ws):g}, range {ws[0]} to {ws[-1]}")

asyncio.run(main())
