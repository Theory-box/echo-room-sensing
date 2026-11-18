// Replay logged sessions through the app's own map + wall finder; record why each region was (not) accepted.
const OUT = [];
try {
  const files = (window.WR_FILES || []);
  for (const name of files) {
    const x = new XMLHttpRequest(); x.open('GET', name, false); x.send(); const d = JSON.parse(x.responseText); const fr = d.frames;
    clearMap(); const mk = +d.settings.mask, mR = +d.settings.range;
    const reasons = []; const orig = closeRun;
    closeRun = function (u, why) {
      const span = u.hi - u.lo;
      if (span >= 3) {
        const wl = wallOf(u);
        const edge = UHlo < u.lo - 5 && UHhi > u.hi + 5, cnt = u.nc >= 3 && u.n >= 5, sp = span >= RCD_MIN && span <= RCD_MAX;
        reasons.push({ r: wl.r, a: wl.a, span, n: u.n, nc: u.nc, why, edge, cnt, sp, ring: isRing(wl.r), floor: floorLike(wl.r) });
      }
      return orig(u, why);
    };
    const yaw0 = fr[0].yaw;
    for (const f of fr) {
      const kept = f.e.map(e => ({ r: e[0], l: e[1], dir: { a: 'ahead', s: 'side', b: 'behind', '?': '?' }[e[3]] || '?', tconf: !!e[10], cos: 0, lagOK: false }));
      updateMap(f.h, kept, mk, mR); updateWalls(f.h, kept, f.t);
    }
    closeRun = orig;
    const near = reasons.filter(z => z.r < 1.5), far = reasons.filter(z => z.r >= 1.5);
    const cat = arr => { const c = {}; for (const z of arr) { const k = z.why === 'wide' ? 'too wide (>150)' : !z.sp ? 'span <12' : !z.cnt ? 'too few detections' : !z.edge ? 'edge not looked past' : z.ring ? 'floor ring' : z.floor ? 'floor-like (same dist 3+ dirs)' : 'ACCEPTED'; c[k] = (c[k] || 0) + 1; } return JSON.stringify(c); };
    OUT.push(`${name}: near (<1.5 m) ${cat(near)}`);
    OUT.push(`   far (>=1.5 m) ${cat(far)}`);
    OUT.push(`   final walls: ${WALLS.filter(w => !wallHidden(w)).map(w => w.r.toFixed(2) + '@' + Math.round(w.a)).join(' ')}`);
    OUT.push(`   floor-like distances: WIDE ${JSON.stringify(WIDE.map(v => +v.toFixed(2)))}; REG near ${JSON.stringify([...new Set(REG.filter(g => g[0] < 2.2 && g[0] > 0.6 && floorLike(g[0])).map(g => +g[0].toFixed(2)))].sort())}`);
  }
} catch (e) { ERR.push(e.message + ' ' + e.stack); }
document.body.insertAdjacentHTML('beforeend', '<pre id=R>RESULT\n' + OUT.join('\n') + '\nerrors=' + JSON.stringify(ERR) + '</pre>');
