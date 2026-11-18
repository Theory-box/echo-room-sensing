# Idea 1 test: does the high-band / low-band echo level ratio depend on how far off-axis the reflector is?
# Truth angle: walls the app found (regions of constant depth): rel = heading - wall's middle heading.
import json, math, sys, glob, collections
import numpy as np
from scipy.io import wavfile
SR, C = 48000, 343.0
def ad(a, b): return (a - b + 540) % 360 - 180

def chirp_piece(n, f0, f1, a, b):
    T = n / SR; t = np.arange(n) / SR
    ph = 2 * np.pi * (f0 * t + (f1 - f0) * t * t / (2 * T))
    s = np.zeros(n, complex); m = b - a
    s[a:b] = np.exp(1j * ph[a:b]) * (0.5 - 0.5 * np.cos(2 * np.pi * np.arange(m) / (m - 1)))
    return s
def mf(sig, tp):
    N = 1 << int(np.ceil(np.log2(len(sig) + len(tp))))
    return np.fft.ifft(np.fft.fft(sig, N) * np.conj(np.fft.fft(tp, N)))[:len(sig)]

rows = []
for logf in sorted(glob.glob('logs/sweep-20261118-1*-sonar_log.json')):
    wav = logf.replace('-sonar_log.json', '-raw_audio.wav')
    try: d = json.load(open(logf))
    except Exception: continue
    if not d.get('raw') or '|' not in str(d['raw']) or d['settings'].get('ping') != 'quietlong': continue
    fr = d['frames']
    if not fr or 'fr' not in fr[0]: continue
    try: sr, x = wavfile.read(wav)
    except Exception: continue
    x = x.astype(np.float64)
    end, nraw = int(d['raw'].split('|')[1]), int(d['raw'].split('|')[2]); start = end - nraw
    rate = int(d['settings']['rate']); P = round(SR / rate)
    rng = float(d['settings'].get('range', 5)); needNb = round(2 * rng / C * SR)
    n = round(max(0.01 * SR, min(0.5 * P, P - needNb - 300)))
    full = chirp_piece(n, 16000, 22000, 0, n)
    lo = chirp_piece(n, 16000, 22000, 0, n // 2); hi = chirp_piece(n, 16000, 22000, n // 2, n)
    e = np.abs(mf(x[:, 0], full)); eL = np.abs(mf(x[:, 0], lo)); eH = np.abs(mf(x[:, 0], hi))
    k = int(np.argmax(e[:P])); clicks = []
    while k + 400 < len(e):
        a0, b0 = max(0, k - 20), k + 21; kk = a0 + int(np.argmax(e[a0:b0])); clicks.append(kk); k = kk + P
    W = [w for f in fr for w in f.get('rcd', []) if w[5] == 1]
    frs = np.array([f['fr'] for f in fr]); s2m = C / (2 * SR)
    for c in clicks:
        j = np.searchsorted(frs, start + c)
        if j >= len(fr): continue
        f = fr[j]
        for ech in f['e']:
            if not ech[10]: continue
            ws = [w for w in W if abs(ech[0] - w[1]) < 0.05 and abs(ad(f['h'], w[2])) < 70]
            if not ws: continue
            w = min(ws, key=lambda w: abs(ad(f['h'], w[2])))
            b = c + int(round(ech[0] / s2m)); h = int(0.03 / s2m)
            if b + h >= len(e): continue
            LL = 20 * np.log10(eL[b - h:b + h].max() / eL[c]); LH = 20 * np.log10(eH[b - h:b + h].max() / eH[c])
            rows.append((logf[-30:-16], ad(f['h'], w[2]), ech[0], LL, LH, LH - LL))
R = np.array([r[1:] for r in rows], float)
print('echo-clicks from found walls:', len(R), 'sessions:', len(set(r[0] for r in rows)))
print('|angle off the wall normal|   n    high-low ratio median (p25..p75)   low band level   high band level')
for a, b in ((0, 5), (5, 10), (10, 20), (20, 30), (30, 45), (45, 70)):
    m = (np.abs(R[:, 0]) >= a) & (np.abs(R[:, 0]) < b)
    if m.sum() < 10: continue
    q = np.percentile(R[m, 4], [25, 50, 75])
    print(f'   {a:2d}-{b:2d} deg  {m.sum():5d}    {q[1]:6.1f} dB  ({q[0]:.1f} .. {q[2]:.1f})        {np.median(R[m,2]):6.1f}          {np.median(R[m,3]):6.1f}')
# signed: left vs right
for a, b in ((-45, -15), (-15, 15), (15, 45)):
    m = (R[:, 0] >= a) & (R[:, 0] < b)
    if m.sum() > 10: print(f'   signed {a:+d}..{b:+d}: ratio median {np.median(R[m,4]):.1f} dB, n {m.sum()}')
# per session check
for s in sorted(set(r[0] for r in rows)):
    S = np.array([r[1:] for r in rows if r[0] == s], float)
    a = S[np.abs(S[:, 0]) < 10, 4]; b2 = S[np.abs(S[:, 0]) >= 20, 4]
    if len(a) > 5 and len(b2) > 5: print(f'   {s}: on-axis (<10) {np.median(a):.1f} dB (n {len(a)}), off-axis (>=20) {np.median(b2):.1f} dB (n {len(b2)})')
np.save('bandangle_rows.npy', R)
