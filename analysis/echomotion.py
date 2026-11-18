# Phone movement from the echoes themselves: between consecutive readings, the confirmed echoes (same track) all shift
# by about the phone's movement toward them (things ahead). The median shift = common-mode movement; summed over time.
# Then: combine with the pilots (fine, short-term), and test motion-corrected averaging of echo distances.
import json, sys, numpy as np, collections
from scipy.signal import butter, filtfilt
def load(s):
    d = json.load(open(f'logs/sweep-20261118-{s}-sonar_log.json')); return d, d['frames']
def echo_motion(fr, min_tracks=1):
    """returns t (s), cumulative movement toward the echoes (m, + = moved closer), n tracks used per step"""
    T0 = fr[0]['t']; prev = {}; cum = 0.0; out = []; nused = []
    for x in fr:
        cur = {e[9]: e[0] - (e[12] / 100 if len(e) > 12 and e[12] is not None else 0) for e in x['e'] if e[9] and e[10]}
        d = [prev[k] - cur[k] for k in cur if k in prev and abs(prev[k] - cur[k]) < 0.06]
        if len(d) >= min_tracks: cum += float(np.median(d))
        out.append(((x['t'] - T0) / 1000, cum)); nused.append(len(d)); prev = cur
    a = np.array(out); return a[:, 0], a[:, 1], np.array(nused)
def pilot_series(fr):
    T0 = fr[0]['t']; v = [((x['t'] - T0) / 1000, x.get('pm')) for x in fr]
    v = [(t, p) for t, p in v if p is not None]
    if not v: return None, None
    a = np.array(v, float); return a[:, 0], -a[:, 1] / 1000     # pm: + = paths longer -> moved away; flip to "moved closer"
def accel_disp(fr, t):
    T0 = fr[0]['t']; yt = np.array([f['t'] for f in fr], float); psi = np.unwrap(np.radians(np.array([f['yaw'] for f in fr]) + 180))
    A = np.array([a for f in fr for a in f.get('ac', [])], float); A = A[np.argsort(A[:, 0])]
    pa = np.interp(A[:, 0], yt, psi); af = A[:, 1] * np.sin(pa) + A[:, 2] * np.cos(pa)
    fs = 50; g = np.arange(A[0, 0], A[-1, 0], 1000 / fs); ag = np.interp(g, A[:, 0], af)
    bb, aa = butter(2, [0.15 / (fs / 2), 2.0 / (fs / 2)], 'band'); ag = filtfilt(bb, aa, ag - ag.mean())
    n = len(ag); F = np.fft.rfftfreq(n, 1 / fs); S = np.fft.rfft(ag); w = 2 * np.pi * F; S[1:] /= -(w[1:] ** 2); S[0] = 0
    xd = filtfilt(bb, aa, np.fft.irfft(S, n))
    return np.interp(t * 1000 + T0 - 330, g, xd)      # sensor leads the audio by ~0.33 s
def bp(x, fs, lo=0.15, hi=2.0):
    bb, aa = butter(2, [lo / (fs / 2), hi / (fs / 2)], 'band'); return filtfilt(bb, aa, x - x.mean())
def lagcorr(a, b, maxl):
    best = None
    for L in range(-maxl, maxl + 1):
        u, v = (a[L:], b[:len(b) - L]) if L >= 0 else (a[:L], b[-L:])
        c = np.corrcoef(u, v)[0, 1]
        if best is None or abs(c) > abs(best[0]): best = (c, L, np.dot(u, v) / np.dot(v, v))
    return best
if __name__ == '__main__':
    # 1) known move (phone on the table, moved ~25 cm toward the wall, resting again)
    d, fr = load('143500-443'); t, E, n = echo_motion(fr)
    a = (t > 1) & (t < 6); b = t > t[-1] - 1.5
    print(f'calibration: echo-based movement {100*(E[b].mean()-E[a].mean()):+.1f} cm (wall echo: +25.0, paper 27.9); at rest drift sd {100*E[a].std():.2f} cm; tracks used per step median {np.median(n):.0f}')
    tp, P = pilot_series(fr)
    if tp is not None:
        Pi = np.interp(t, tp, P); print(f'             pilots (live): {100*(Pi[b].mean()-Pi[a].mean()):+.1f} cm')
    # 2) hand-held pushes: compare with the motion sensor's movement (band 0.15-2 Hz)
    for s in ('142308-495', '143533-870'):
        d, fr = load(s); t, E, n = echo_motion(fr)
        fs = 1 / np.median(np.diff(t)); g = np.arange(t[0], t[-1], 1 / fs)
        Eg = bp(np.interp(g, t, E), fs); Ag = bp(accel_disp(fr, g), fs)
        c = lagcorr(Eg, Ag, int(0.5 * fs))
        line = f'{s}: echo movement vs sensor: corr {c[0]:+.2f} at {c[1]/fs*1000:+.0f} ms, scale {c[2]:+.2f}; echo movement rms {100*Eg.std():.1f} cm, sensor {100*Ag.std():.1f} cm'
        tp, P = pilot_series(fr)
        if tp is not None:
            Pg = bp(np.interp(g, tp, P), fs); cp = lagcorr(Pg, Ag, int(0.5 * fs)); ce = lagcorr(Pg, Eg, int(0.5 * fs))
            line += f' | pilots vs sensor {cp[0]:+.2f} (scale {cp[2]:+.2f}), pilots vs echoes {ce[0]:+.2f} (scale {ce[2]:+.2f})'
        print(line)
