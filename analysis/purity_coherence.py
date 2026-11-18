# Purity filter test: per distance, how steady is the echo's phase from click to click?
# z_k = y_k * conj(y_{k-1}) at the echo's sample; coherence C = |sum z_k| / sum |z_k| over the clicks around it.
# A mirror-like surface: the phase step is the same every click (even while moving) -> C near 1. Clutter: random -> low.
import json, glob, collections, sys
import numpy as np
from scipy.io import wavfile
SR, C0 = 48000, 343.0
def ad(a, b): return (a - b + 540) % 360 - 180
def mf(sig, tp):
    N = 1 << int(np.ceil(np.log2(len(sig) + len(tp))))
    return np.fft.ifft(np.fft.fft(sig, N) * np.conj(np.fft.fft(tp, N)))[:len(sig)]
rows = []
for logf in sorted(glob.glob('logs/sweep-20261118-1*-sonar_log.json')):
    try: d = json.load(open(logf))
    except Exception: continue
    if not d.get('raw') or '|' not in str(d['raw']) or d['settings'].get('ping') != 'quietlong': continue
    fr = d['frames']
    if not fr or 'fr' not in fr[0]: continue
    sr, x = wavfile.read(logf.replace('-sonar_log.json', '-raw_audio.wav')); x = x.astype(np.float64)
    end, nraw = int(d['raw'].split('|')[1]), int(d['raw'].split('|')[2]); start = end - nraw
    rate = int(d['settings']['rate']); P = round(SR / rate); rng = float(d['settings'].get('range', 5))
    n = round(max(0.01 * SR, min(0.5 * P, P - round(2 * rng / C0 * SR) - 300)))
    t = np.arange(n) / SR; T = n / SR
    tpl = (0.5 - 0.5 * np.cos(2 * np.pi * np.arange(n) / (n - 1))) * np.exp(1j * 2 * np.pi * (16000 * t + 6000 * t * t / (2 * T)))
    y = mf(x[:, 0], tpl); e = np.abs(y)
    k = int(np.argmax(e[:P])); clicks = []
    while k + 400 < len(e):
        a0 = max(0, k - 20); kk = a0 + int(np.argmax(e[a0:k + 21])); clicks.append(kk); k = kk + P
    clicks = np.array(clicks)
    W = [w for f in fr for w in f.get('rcd', []) if w[5] == 1]
    frs = np.array([f['fr'] for f in fr]); s2m = C0 / (2 * SR); NW = 4   # +-4 clicks
    for ci in range(NW, len(clicks) - NW):
        c = clicks[ci]; j = np.searchsorted(frs, start + c)
        if j >= len(fr): continue
        f = fr[j]
        for q in f['e']:
            off = int(round(q[0] / s2m)); seg = range(ci - NW, ci + NW + 1)
            if clicks[seg[-1]] + off + 3 >= len(y): continue
            # per click take the strongest sample within +-3 samples of the echo (follows small moves), its complex value
            vals = []
            for m in seg:
                b = clicks[m] + off; i = b - 3 + int(np.argmax(e[b - 3:b + 4]))
                vals.append(y[i] / y[clicks[m]])          # re the direct sound (removes the click's own phase)
            vals = np.array(vals); z = vals[1:] * np.conj(vals[:-1])
            coh = np.abs(z.sum()) / (np.abs(z).sum() + 1e-30)
            wall = any(abs(ad(f['h'], w[2])) < 20 and abs(q[0] - w[1]) < 0.05 for w in W)
            rows.append((coh, q[10], wall, q[1], q[0], f['gy']))
R = np.array(rows, float)
print('echo-clicks', len(R))
def show(name, m):
    v = np.sort(R[m, 0]); print(f'  {name:34s} n {m.sum():6d}  coherence median {np.median(v):.2f}  p25 {np.percentile(v,25):.2f}  p75 {np.percentile(v,75):.2f}')
show('confirmed (tracking kept it)', R[:, 1] == 1)
show('unconfirmed (likely fake)', R[:, 1] == 0)
show('from a found wall', R[:, 2] == 1)
show('confirmed, not from a found wall', (R[:, 1] == 1) & (R[:, 2] == 0))
print('if we dropped echoes below a coherence cut:')
for cut in (0.3, 0.5, 0.7, 0.8, 0.9):
    keepc = (R[(R[:, 1] == 1), 0] >= cut).mean(); dropu = (R[(R[:, 1] == 0), 0] < cut).mean(); keepw = (R[(R[:, 2] == 1), 0] >= cut).mean()
    print(f'  cut {cut}: keeps {100*keepc:.0f}% of confirmed, {100*keepw:.0f}% of wall echoes; removes {100*dropu:.0f}% of unconfirmed')
# does coherence add anything beyond loudness? compare within level bands
for lo, hi in ((-60, -48), (-48, -42), (-42, -30)):
    m = (R[:, 3] >= lo) & (R[:, 3] < hi)
    if m.sum() > 50:
        a = R[m & (R[:, 1] == 1), 0]; b = R[m & (R[:, 1] == 0), 0]
        print(f'  level {lo}..{hi} dB: confirmed median {np.median(a):.2f} (n {len(a)}), unconfirmed {np.median(b):.2f} (n {len(b)})')
print('only nearly still moments (gyro < 0.08 rad/s):')
st = R[:, 5] < 0.08
for name, m in (('confirmed', R[:, 1] == 1), ('unconfirmed', R[:, 1] == 0), ('wall', R[:, 2] == 1)):
    v = R[st & m, 0]
    if len(v): print(f'  {name:12s} n {len(v):5d} coherence median {np.median(v):.2f} p25 {np.percentile(v,25):.2f} p75 {np.percentile(v,75):.2f}')
