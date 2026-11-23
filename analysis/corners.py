import json, sys, numpy as np


L = sys.argv[1] if len(sys.argv) > 1 else 'logs/'  # folder holding the pulled sessions
OUT = './'
BIN = 0.03
HB = 5  # heading bin, degrees


def wrap(a): return ((a + 180) % 360) - 180


def load(s, fit=None, ts=None):
    d = json.load(open(L + s + '/sonar_log.json'))
    F = [f for f in d['frames'] if f.get('p') and (ts is None or f.get('ts') == ts)]
    if fit is None:
        rb = [f['rb'] for f in F if 'rb' in f]; fit = rb[-1]
    n = min(len(f['p']) for f in F)
    nh = 360 // HB
    acc = np.zeros((nh, n)); cnt = np.zeros(nh)
    for f in F:
        b = int((f['h'] % 360) // HB); acc[b] += 10 ** (np.array(f['p'][:n]) / 10); cnt[b] += 1
    ok = cnt >= 2
    img = np.full((nh, n), np.nan); img[ok] = 10 * np.log10(acc[ok] / cnt[ok, None] + 1e-30)
    return img, cnt, fit, n


def corners(fit):
    rot, D = fit[0], fit[1:5]
    out = []
    for w in range(4):  # corner between wall w and wall w+1 (clockwise)
        a, b = D[w], D[(w + 1) % 4]
        out.append(dict(name=f'{w}-{(w+1)%4}', h=(rot + 90 * w + np.degrees(np.arctan2(b, a))) % 360, r=float(np.hypot(a, b))))
    return out


def analyse(s, label, fit=None, ts=None):
    img, cnt, fit, n = load(s, fit, ts)
    rot, D = fit[0], fit[1:5]
    # remove what is heard all round (ceiling, floor, the phone's own ringing): subtract the median over headings
    rel = img - np.nanmedian(img, axis=0)
    hc = (np.arange(img.shape[0]) + 0.5) * HB
    res = []
    for c in corners(fit):
        i = int(round(c['r'] / BIN - 0.5))
        win = slice(max(0, i - 2), i + 3)
        dh = np.array([wrap(h - c['h']) for h in hc])
        near = (np.abs(dh) <= 30) & ~np.isnan(rel[:, 0])
        far = (np.abs(dh) >= 60) & ~np.isnan(rel[:, 0])
        # per heading bin: strongest level within +-2 bins of the predicted corner distance, and where it sits
        pk = np.nanmax(rel[:, win], axis=1)
        where = (np.nanargmax(np.nan_to_num(rel[:, win], nan=-99), axis=1) + win.start + 0.5) * BIN
        # walls at that heading would echo at D/cos; flag headings where a wall echo also lands within 0.1 m
        wall_close = []
        for k, h in enumerate(hc):
            hit = False
            for w in range(4):
                a = np.radians(wrap(h - (rot + 90 * w)))
                if abs(a) < np.radians(80) and abs(D[w] / np.cos(a) - c['r']) < 0.1: hit = True
            wall_close.append(hit)
        wall_close = np.array(wall_close)
        clean = near & ~wall_close
        span = []  # headings within +-45 where a peak >=3 dB sits at the corner distance
        for k in np.argsort(np.abs(dh)):
            if abs(dh[k]) > 45 or np.isnan(pk[k]): continue
            if pk[k] >= 3: span.append(dh[k])
        res.append(dict(c=c, near=float(np.nanmean(pk[near])) if near.any() else None,
                        clean=float(np.nanmean(pk[clean])) if clean.any() else None, nclean=int(clean.sum()),
                        far=float(np.nanmean(pk[far])) if far.any() else None,
                        span=(min(span), max(span), len(span)) if span else None,
                        rspread=float(np.nanstd(where[near & (pk >= 3)])) if (near & (pk >= 3)).sum() > 2 else None))
    # data-driven: ridges of constant distance spanning >= 25 deg of heading (any distance 1-5 m)
    ridges = []
    pkmask = np.zeros_like(rel, dtype=bool)
    for k in range(rel.shape[0]):
        row = rel[k]
        if np.isnan(row[0]): continue
        for i in range(2, n - 2):
            if row[i] >= 4 and row[i] == np.nanmax(row[i - 2:i + 3]): pkmask[k, i] = True
    nh = rel.shape[0]
    for i in range(int(1.0 / BIN), n - 1):
        col = pkmask[:, max(0, i - 1):i + 2].any(axis=1)
        if col.all(): continue
        start = int(np.argmin(col))  # begin scanning at a gap so runs do not wrap badly
        run = 0
        for j in range(1, nh + 1):
            k = (start + j) % nh
            if col[k]: run += 1
            else:
                if run * HB >= 25: ridges.append(((k - run) % nh * HB, run * HB, round((i + 0.5) * BIN, 2)))
                run = 0
        if run * HB >= 25: ridges.append(((start + nh + 1 - run) % nh * HB, run * HB, round((i + 0.5) * BIN, 2)))
    # merge neighbouring distance bins
    ridges.sort(key=lambda x: (x[0], x[2]))
    np.save(OUT+f'corners_{label}.npy', rel)
    return fit, res, ridges


if __name__ == '__main__':
    runs = [('sweep-20261119-193942-603', 'guided', [-6, 1.87, 1.47, 1.5, 2.48], None),
            ('sweep-20261119-190859-643', 'evening', None, None),
            ('sweep-20261119-152557-632', 'test2', None, None)]
    for s, lab, fit, ts in runs:
        fit, res, ridges = analyse(s, lab, fit, ts)
        print('====', lab, 'box rot', fit[0], 'D', [round(x, 2) for x in fit[1:5]])
        for r in res:
            c = r['c']
            print(f"  corner {c['name']}: heading {c['h']:.0f}, dist {c['r']:.2f} m | level at corner dist: within 30deg {r['near']:.1f} dB,"
                  f" away from walls {r['clean'] if r['clean'] is None else round(r['clean'],1)} ({r['nclean']} bins), other headings {r['far']:.1f} dB | peak span {r['span']} | dist spread {r['rspread']}")
        print('  constant-distance ridges >=25 deg (start heading, width, distance):')
        for x in ridges: print('   ', x)
