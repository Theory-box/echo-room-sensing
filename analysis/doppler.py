# Doppler correction for the all-tone signal: per 2048-sample window, evaluate the tones at frequencies shifted by
# candidate speeds (zero-padded FFT, 2.93 Hz bins), build the distance profile for each speed, and pick the speed that
# makes the echoes beyond the direct sound strongest. Integrate that speed -> phone movement. Truth: known 25 cm move.
import numpy as np, json, math, sys
from scipy.io import wavfile
SR, C, P, K0, NT, HOP, ZP = 48000, 343.0, 2048, 683, 256, 256, 8
kk = K0 + np.arange(NT); fk = kk * SR / P
w = np.hanning(NT + 2)[1:-1]
def amps(pilots=True):
    a = np.ones(NT)
    for k in range(NT):
        e = min(k, NT - 1 - k); a[k] = 1 if e >= 16 else 0.2 + 0.8 * (0.5 - 0.5 * math.cos(math.pi * e / 16))
        if pilots and k % 16 == 8: a[k] *= 2
    return a
def load(base):
    d = json.load(open(base + '-sonar_log.json')); fr = d['frames']
    sr, x = wavfile.read(base + '-raw_audio.wav'); x = x.astype(np.float64)[:, 0]
    end, nraw = int(d['raw'].split('|')[1]), int(d['raw'].split('|')[2])
    return d, fr, x, end - nraw
def run(x, start, vgrid, rmin=0.35, rmax=2.5, stat_tau=3.0, vsel=None):
    """vsel: optional function(window index) -> list of candidate speeds (for the sensor-assisted variant)"""
    starts = np.arange(0, len(x) - P, HOP); out_v = []; out_e = []
    a = amps(); s2m = C / (2 * SR)
    # static part per tone (running mean at speed 0) to remove the direct sound / still room before the speed search
    S = np.zeros(NT, complex)
    win = np.hanning(P)   # taper so off-bin evaluation leaks less
    for i, s in enumerate(starts):
        seg = x[s:s + P] * win
        F = np.fft.fft(seg, P * ZP)
        y0 = F[kk * ZP] * np.exp(-2j * np.pi * kk * ((start + s) % P) / P)
        al = max(HOP / (stat_tau * SR), 1 / (i + 1)); S += al * (y0 - S)
        best = (-1, 0.0)
        cands = vgrid if vsel is None else vsel(i)
        for v in cands:
            idx = np.round((fk * (1 + 2 * v / C)) * P * ZP / SR).astype(int)
            y = F[idx] * np.exp(-2j * np.pi * kk * ((start + s) % P) / P)
            if v == 0: y = y - S                                   # (static only sits at speed 0)
            else: y = y - S * 0                                    # moving part: static leaks little off-bin
            prof = np.fft.ifft(y / a * w, 1024)
            mag = np.abs(prof)
            d0 = int(np.argmax(np.abs(np.fft.ifft(S / a * w, 1024))))
            i0 = int(rmin / s2m / 2); i1 = int(rmax / s2m / 2)
            e = (mag[(d0 + i0) % 1024:(d0 + i1) % 1024] ** 2).sum() if d0 + i1 < 1024 else (np.r_[mag[d0 + i0:], mag[:(d0 + i1) % 1024]] ** 2).sum()
            if e > best[0]: best = (e, v)
        out_v.append(best[1]); out_e.append(best[0])
    return (starts + P / 2) / SR, np.array(out_v), np.array(out_e)
if __name__ == '__main__':
    base = 'logs/sweep-20261118-143500-443'
    d, fr, x, start = load(base)
    vgrid = np.arange(-0.40, 0.401, 0.02)
    t, v, e = run(x, start, vgrid)
    # positive v = getting closer (frequencies raised) -> distance change = -integral v
    disp = -np.cumsum(v) * HOP / SR
    a = (t > 1) & (t < 5); b = t > t[-1] - 1.5
    print(f'Doppler-picked speed integrated: {100*(disp[b].mean()-disp[a].mean()):+.1f} cm (echo says -25.0)')
    print('speed picked (cm/s) per second:', [int(round(100 * np.median(v[(t >= s) & (t < s + 1)]))) for s in range(int(t[-1]))])
    np.save('doppler_cal.npy', np.vstack([t, v, e]))
