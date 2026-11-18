import sys, json, math
import numpy as np
from scipy.io import wavfile
from numpy.fft import rfft, irfft

wav, logf = sys.argv[1], sys.argv[2]
sr, x = wavfile.read(wav); x = x.astype(np.float64)
SR, C, P = 48000, 343.0, 3200
n = 1501; t = np.arange(n) / SR; T = n / SR
ph = 2 * np.pi * (16000 * t + 6000 * t * t / (2 * T)); w = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(n) / (n - 1))
tpl = w * np.exp(1j * ph)

def mf(sig):  # complex matched filter output y[k] = sum sig[k+i] * conj(tpl[i])
    N = 1 << int(np.ceil(np.log2(len(sig) + n)))
    S = np.fft.fft(sig, N); Tp = np.fft.fft(tpl, N)
    return np.fft.ifft(S * np.conj(Tp))[:len(sig)]
y1, y2 = mf(x[:, 0]), mf(x[:, 1])
e1 = np.abs(y1)
# clicks: direct-sound peaks spaced P
k0 = int(np.argmax(e1[:P])); clicks = []
k = k0
while k + 400 < len(e1):
    lo, hi = max(0, k - 20), min(len(e1), k + 21); kk = lo + int(np.argmax(e1[lo:hi])); clicks.append(kk); k = kk + P
clicks = np.array(clicks); tt = clicks / SR
s2m = C / (2 * SR)
i0, i1 = int(0.72 / s2m), int(1.14 / s2m)
pk, lead, cen, amp, phs, lag, direct_lag = [], [], [], [], [], [], []
for c in clicks:
    seg = e1[c + i0:c + i1]; m = int(np.argmax(seg)); top = seg[m]
    j = m + 0
    if 0 < m < len(seg) - 1:
        a, b, d = seg[m - 1], seg[m], seg[m + 1]; den = a - 2 * b + d; off = 0.5 * (a - d) / den if den < 0 else 0
    else: off = 0
    pk.append((i0 + m + off) * s2m)
    thr = top / 2  # -6 dB
    jj = m
    while jj > 0 and seg[jj - 1] > thr: jj -= 1
    f = (thr - seg[jj - 1]) / (seg[jj] - seg[jj - 1]) if jj > 0 and seg[jj] != seg[jj - 1] else 0
    lead.append((i0 + jj - 1 + f) * s2m)
    kk = m
    while kk < len(seg) - 1 and seg[kk + 1] > thr: kk += 1
    ww = seg[jj:kk + 1] ** 2; cen.append(((np.arange(jj, kk + 1) + i0) * ww).sum() / ww.sum() * s2m)
    amp.append(20 * np.log10(top / e1[c]))
    phs.append(np.angle(y1[c + i0 + m] / y1[c]))
    # two-mic lag of the wall echo: envelope cross-corr, +-26 samples, window +-12 around peak
    g = c + i0 + m; best, bl = -9, 0
    a1 = e1[g - 12:g + 13]
    for L in range(-26, 27):
        b2 = np.abs(y2[g - 12 + L:g + 13 + L]); r = np.corrcoef(a1, b2)[0, 1]
        if r > best: best, bl = r, L
    lag.append((bl, best))
    best, bl = -9, 0; a1 = e1[c - 8:c + 9]
    for L in range(-26, 27):
        b2 = np.abs(y2[c - 8 + L:c + 9 + L]); r = np.corrcoef(a1, b2)[0, 1]
        if r > best: best, bl = r, L
    direct_lag.append(bl)
pk, lead, cen = map(np.array, (pk, lead, cen))
print(f'raw: {len(x)/SR:.1f} s, clicks {len(clicks)}, wall echo level {np.median(amp):.1f} dB re direct')
# push frequency from the peak track
F = np.fft.rfftfreq(len(tt), 1 / 15); Pw = np.abs(np.fft.rfft(cen - cen.mean())); band = (F > 0.3) & (F < 2)
fk = F[band][np.argmax(Pw[band])]; wv = 2 * np.pi * fk
print(f'push frequency {fk:.2f} Hz')
def fitres(yv):
    M = np.column_stack([np.sin(wv * tt), np.cos(wv * tt), np.ones_like(tt)]); cc = np.linalg.lstsq(M, yv, rcond=None)[0]; r = yv - M @ cc
    return math.hypot(cc[0], cc[1]), r.std(), np.median(np.abs(np.diff(yv)))
for nm, yv in [('loudest point (1 click, no averaging)', pk), ('front edge -6 dB', lead), ('centre of hump', cen)]:
    A, sd, dd = fitres(yv)
    print(f'  {nm:38s}: mean {yv.mean():.3f} m, push swing {100*A:.2f} cm, leftover jitter sd {100*sd:.2f} cm, click-to-click {100*dd:.2f} cm')
# phase at the loudest point, unwrapped -> distance change (one turn = c/(2*19000) m)
lam2 = C / (2 * 19000)
u = np.unwrap(np.array(phs)) / (2 * np.pi) * lam2
A, sd, dd = fitres(u)
print(f'  {"phase at loudest point (unwrapped)":38s}: push swing {100*A:.2f} cm, leftover sd {100*sd:.2f} cm, click-to-click {100*dd:.2f} cm')
L = np.array([l[0] for l in lag]); Q = np.array([l[1] for l in lag])
print(f'two-mic lag of the wall echo (wall AHEAD -> expect about +20): median {np.median(L)}, p10/p90 {np.percentile(L,10)}/{np.percentile(L,90)}, share >= +10: {np.mean(L>=10):.2f}, share <= -10: {np.mean(L<=-10):.2f}, shape match median {np.median(Q):.2f}')
print(f'direct-sound lag: median {np.median(direct_lag)}, p10/p90 {np.percentile(direct_lag,10)}/{np.percentile(direct_lag,90)}')
np.savez(sys.argv[3], tt=tt, pk=pk, lead=lead, cen=cen, u=u, lag=L, q=Q)
