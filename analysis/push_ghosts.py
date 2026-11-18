# Push test on existing recordings: in steady-heading stretches (you facing a wall, pushing the phone in and out),
# follow each echo from reading to reading (nearest within 3 cm), keep tracks lasting >= 1.5 s, and regress each
# track's distance on the near wall's distance (the reference: the nearest long track). Expected movement ratio:
# real surface ahead ~1 (cos of its angle), room-width ghost 0, phone-bounce ghost 2, floor/ceiling ~0.
# Ghost predictions use the session's room box (whole-session fit): room width = D_j + D_opp, 2x = twice the wall echo.
import json, glob, math, sys, numpy as np, importlib.util
sys.argv = ['x', 'none']
spec = importlib.util.spec_from_file_location('rf', 'roomfit.py'); rf = importlib.util.module_from_spec(spec); spec.loader.exec_module(rf)
ARM = 0.25
def ad(a, b): return (a - b + 540) % 360 - 180
def tracks(frames, gate=0.03, min_len=15):
    act = []; done = []
    for k, f in enumerate(frames):
        rs = sorted(set(round(e[0], 3) for e in f['e'] if e[0] > 0.35)); used = set()
        for tr in act:
            last_k, last_r = tr[-1]
            if k - last_k > 3: continue
            best = min(((abs(r - last_r), r) for r in rs if r not in used), default=None)
            if best and best[0] < gate: tr.append((k, best[1])); used.add(best[1])
        for r in rs:
            if r not in used: act.append([(k, r)])
        still = []
        for tr in act:
            (still if k - tr[-1][0] <= 3 else done).append(tr)
        act = still
    return [t for t in done + act if len(t) >= min_len]
allrows = []
for f in sorted(glob.glob('logs/sweep-20261118-*-sonar_log.json')):
    try: d = json.load(open(f))
    except Exception: continue
    fr = d['frames']
    if len(fr) < 100: continue
    T0 = fr[0]['t']; t = np.array([(x['t'] - T0) / 1000 for x in fr]); h = np.array([x['h'] for x in fr])
    # room box (only if the session turned all the way)
    box = None
    if np.ptp(h) > 300:
        hh = []; rr = []
        for x in fr:
            for e in x['e']:
                if len(e) > 12 and e[10] and e[0] > 0.35: hh.append(x['h']); rr.append(e[0] - (e[12] or 0) / 100)
        if len(rr) > 200: p, _, _ = rf.fit_vote(np.array(hh), np.array(rr)); box = (p[0], p[1:5])
    i = 0
    while i < len(fr):
        j = i
        while j + 1 < len(fr) and abs(ad(h[j + 1], h[i])) < 8: j += 1
        if t[j] - t[i] < 4: i += 1; continue
        seg = fr[i:j + 1]; T = tracks(seg)
        i = j + 1
        if not T: continue
        ref = max(T, key=lambda tr: len(tr) - 30 * np.median([r for _, r in tr]))   # long and near
        refd = dict(ref); rr = np.array(list(refd.values()))
        pp = np.percentile(rr, 95) - np.percentile(rr, 5)
        if pp < 0.04: continue                     # no real push in this stretch
        width = None
        if box:
            rot, D = box; hd = np.median(h[i - len(seg):i])
            for jw in range(4):
                if abs(ad(hd, rot + 90 * jw)) < 25: width = D[jw] + D[(jw + 2) % 4]
        for tr in T:
            if tr is ref: continue
            ks = [k for k, _ in tr if k in refd]
            if len(ks) < 12: continue
            x = np.array([refd[k] for k in ks]); y = np.array([dict(tr)[k] for k in ks])
            if np.ptp(x) < 0.03: continue
            sl, ic = np.polyfit(x - x.mean(), y, 1); cc = np.corrcoef(x, y)[0, 1]
            r0 = float(np.median(y)); m0 = float(np.median(x))
            kind = 'other'
            if width and abs(r0 - (width - ARM)) < 0.08: kind = 'room-width ghost?'
            elif abs(r0 - 2 * m0) < 0.08: kind = '2x near wall?'
            allrows.append((f[19:29], d['settings']['ping'][:9], round(t[i - len(seg)]), round(m0, 2), round(pp * 100), round(r0, 2), round(sl, 2), round(cc, 2), len(ks), kind))
print('session   ping      start  wall m  push cm | echo m  move ratio  corr  readings  label')
for row in allrows: print('%s %-9s %4ds  %5.2f  %4d    | %5.2f   %5.2f      %5.2f  %4d      %s' % row)
sl = np.array([r[6] for r in allrows]); print('\nmove ratio of all other echoes: ' + ' '.join(f'{lo}-{hi}: {int(np.sum((sl>=lo)&(sl<hi)))}' for lo, hi in ((-9, -0.3), (-0.3, 0.3), (0.3, 0.7), (0.7, 1.3), (1.3, 1.7), (1.7, 2.3), (2.3, 9))))
