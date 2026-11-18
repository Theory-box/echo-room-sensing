# Hum tracking on real recordings vs the motion sensor (forward), plus stillness wobble
import numpy as np, json, sys
from scipy.io import wavfile
from scipy.signal import butter, filtfilt
import importlib.util
spec = importlib.util.spec_from_file_location('hum2', 'hum2.py'); H = importlib.util.module_from_spec(spec); spec.loader.exec_module(H)
SR = 48000
def evaluate(base, hum, lowpass=None):
    d = json.load(open(base + '-sonar_log.json')); fr = d['frames']
    sr, x = wavfile.read(base + '-raw_audio.wav'); x = x.astype(np.float64)
    end, nraw = int(d['raw'].split('|')[1]), int(d['raw'].split('|')[2]); start = end - nraw
    ok = [f for f in fr if f.get('tc')]
    k, b0 = np.polyfit([f['fr'] for f in ok], [f['tc'] for f in ok], 1)
    tb, comb = hum.track(x[:, 0], lowpass=lowpass)
    tms = k * (start + tb * SR) + b0
    yawt = np.array([f['t'] for f in fr], float); psi = np.unwrap(np.radians(np.array([f['yaw'] for f in fr]) + 180))
    A = np.array([a for f in fr for a in f.get('ac', [])], float); A = A[np.argsort(A[:, 0])]
    pa = np.interp(A[:, 0], yawt, psi); af = A[:, 1] * np.sin(pa) + A[:, 2] * np.cos(pa)
    fs = SR / hum.blk; bb, aa = butter(2, [0.15 / (fs / 2), 2.0 / (fs / 2)], 'band')
    g = filtfilt(bb, aa, np.interp(tms, A[:, 0], af) - np.mean(af)); n = len(g)
    F = np.fft.rfftfreq(n, 1 / fs); S = np.fft.rfft(g); w = 2 * np.pi * F; S[1:] /= -(w[1:] ** 2); S[0] = 0
    xf = filtfilt(bb, aa, np.fft.irfft(S, n)); cb = filtfilt(bb, aa, comb - comb.mean())
    best = None
    for L in range(-int(0.6 * fs), int(0.6 * fs) + 1, 2):
        a, b = (cb[L:], xf[:n - L]) if L >= 0 else (cb[:L], xf[-L:])
        c = np.corrcoef(a, b)[0, 1]
        if best is None or abs(c) > abs(best[0]): best = (c, L / fs * 1000, np.dot(a, b) / np.dot(b, b))
    tsec = (tms - fr[0]['t']) / 1000
    gy = np.interp(tms, yawt, np.array([f.get('gy', 0) for f in fr]))
    still = (gy < 0.05)
    wob = []
    for s0 in np.arange(tsec[0], tsec[-1] - 2, 1.0):
        m = (tsec >= s0) & (tsec < s0 + 2) & still
        if m.sum() > fs * 1.5: wob.append(1000 * (comb[m] - comb[m].mean()).std())
    print(f'{base[-25:]}: {tsec[-1]-tsec[0]:.0f} s raw | hum vs sensor forward: corr {best[0]:+.2f} (hum {"later" if best[1] > 0 else "earlier"} {abs(best[1]):.0f} ms), scale {best[2]:+.2f} | sensor fwd rms {100*xf.std():.1f} cm | still 2-s windows: hum wobble median {np.median(wob) if wob else float("nan"):.2f} mm (n {len(wob)})')
for base, hum, lp in (('logs/sweep-20261118-133442-913', H.HUM16, None), ('logs/sweep-20261118-134808-795', H.HUM16, None), ('logs/sweep-20261118-134626-364', H.HYB8, 18250)):
    evaluate(base, hum, lp)
