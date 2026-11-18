# 3-mic Full-sweep recording: per click, per pitch band, matched-filter envelopes for each mic; for the strongest echoes,
# the delay between mics (envelope cross-correlation, sub-sample) and how consistent it is.
import json, numpy as np, math, sys
from scipy.io import wavfile
SR, C, P = 48000, 343.0, 3200
base = 'logs/sweep-20261118-154811-707'
d = json.load(open(base + '-sonar_log.json')); fr = d['frames']
sr, x = wavfile.read(base + '-raw_audio.wav'); x = x.astype(np.float64)
end, nraw = int(d['raw'].split('|')[1]), int(d['raw'].split('|')[2]); start = end - nraw
ok = [f for f in fr if f.get('tc')]; kk, bb = np.polyfit([f['fr'] for f in ok], [f['tc'] for f in ok], 1); T0 = fr[0]['t']
n = 1501; t = np.arange(n) / SR; T = n / SR
ph = 2 * np.pi * (2000 * t + 20000 * t * t / (2 * T))
def piece(f0, f1):   # the part of the sweep between f0 and f1, Hann-tapered
    a = int(round((f0 - 2000) / 20000 * n)); b = int(round((f1 - 2000) / 20000 * n)); m = b - a
    s = np.zeros(n, complex); s[a:b] = np.exp(1j * ph[a:b]) * (0.5 - 0.5 * np.cos(2 * np.pi * np.arange(m) / (m - 1))); return s
def mf(sig, tp):
    N = 1 << int(np.ceil(np.log2(len(sig) + len(tp)))); return np.fft.ifft(np.fft.fft(sig, N) * np.conj(np.fft.fft(tp, N)))[:len(sig)]
bands = {'low 2-8 kHz': piece(2000, 8000), 'mid 8-14 kHz': piece(8000, 14000), 'quiet 16-22 kHz': piece(16000, 22000)}
full = piece(2000, 22000)
e_full = np.abs(mf(x[:, 0], full))
k = int(np.argmax(e_full[:P])); clicks = []
while k + 1500 < len(e_full):
    a0 = max(0, k - 20); k2 = a0 + int(np.argmax(e_full[a0:k + 21])); clicks.append(k2); k = k2 + P
clicks = np.array(clicks)
tsec = (kk * (start + clicks) + bb - T0) / 1000
yt = np.array([f['t'] for f in fr]); H = np.array([f['h'] for f in fr], float)
head = np.interp(T0 + tsec * 1000, yt, H)
s2m = C / (2 * SR)
def env_lag(a, b, c, half=40, maxl=35):
    best = (-2, 0); sc = []
    for L in range(-maxl, maxl + 1):
        u = a[c - half:c + half + 1]; v = b[c - half + L:c + half + 1 + L]
        r = np.corrcoef(u, v)[0, 1]; sc.append(r)
        if r > best[0]: best = (r, L)
    i = best[1] + maxl
    if 0 < i < len(sc) - 1:
        y0, y1, y2 = sc[i - 1], sc[i], sc[i + 1]; den = y0 - 2 * y1 + y2
        if den < 0: return best[1] + 0.5 * (y0 - y2) / den, best[0]
    return best[1], best[0]
results = {}
for name, tp in bands.items():
    E = [np.abs(mf(x[:, c], tp)) for c in range(3)]
    rows = []
    for ci, c in enumerate(clicks):
        if c + int(2.6 / s2m) + 60 >= len(x): continue
        lo, hi = c + int(0.45 / s2m), c + int(2.5 / s2m)
        seg = E[0][lo:hi]; m = lo + int(np.argmax(seg))
        lvl = 20 * np.log10(E[0][m] / E[0][c])
        l12, q12 = env_lag(E[0], E[1], m); l23, q23 = env_lag(E[1], E[2], m)
        lv2 = 20 * np.log10(E[1][m - 3:m + 4].max() / E[0][m]); lv3 = 20 * np.log10(E[2][m - 3:m + 4].max() / E[0][m])
        rows.append((tsec[ci], head[ci], (m - c) * s2m, lvl, l12, q12, l23, q23, lv2, lv3))
    R = np.array(rows); results[name] = R
    dl12 = env_lag(E[0], E[1], clicks[5], half=12)[0]; dl23 = env_lag(E[1], E[2], clicks[5], half=12)[0]
    good = R[:, 5] > 0.8
    print(f'== {name}: clicks {len(R)} | direct sound lag mic1->mic2 {dl12:+.1f}, mic2->mic3 {dl23:+.1f} samples')
    for lab, m in (('toward-wall part (7-16 s, facing it)', (R[:, 0] < 16)), ('turning (16-45 s)', (R[:, 0] >= 16) & (R[:, 0] < 45))):
        mm = m & good
        if mm.sum() < 5: print(f'   {lab}: too few well-matched echoes ({mm.sum()})'); continue
        q = np.percentile(R[mm, 4], [10, 25, 50, 75, 90])
        print(f'   {lab}: echoes with shape match > 0.8: {mm.sum()}/{m.sum()} | mic1->mic2 echo lag p10/25/50/75/90 = {np.round(q,1)} | mic2->mic3 median {np.median(R[mm,6]):+.1f} (spread p25-p75 {np.percentile(R[mm,6],75)-np.percentile(R[mm,6],25):.1f}) | level mic2 {np.median(R[mm,8]):+.1f} dB, mic3 {np.median(R[mm,9]):+.1f} dB re mic1')
np.save('mic3_rows.npy', {k: v for k, v in results.items()}, allow_pickle=True)
