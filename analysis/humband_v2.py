# Structural fix: map cycle 1920 samples (25 Hz grid) so a 250 Hz-spaced hum (proven design) fits exactly.
# Hum tones on multiples of 250 Hz; read with Hann windows of 384 samples (two 250-Hz cycles: neighbouring hum tones sit
# exactly on the window's zeros; map tones are >= 6 bins away where the Hann side lobes are tiny), hop 192.
import numpy as np, math, sys
SR, C = 48000, 343.0
P = 1920; DF = SR / P          # 25 Hz grid
rng = np.random.default_rng(0)
def design(hum_f, map_f0, map_f1, hum_gain, taper_iters=60):
    hk = [int(round(f / DF)) for f in hum_f]; mk = list(range(int(round(map_f0 / DF)), int(round(map_f1 / DF)) + 1))
    tones = hk + mk; amp = np.array([hum_gain] * len(hk) + [1.0] * len(mk))
    E = 16; ne = len(mk)
    for i in range(ne):
        e = min(i, ne - 1 - i); amp[len(hk) + i] *= 1 if e >= E else 0.2 + 0.8 * (0.5 - 0.5 * math.cos(math.pi * e / E))
    ph = rng.uniform(0, 2 * np.pi, len(tones))
    def synth(ph):
        S = np.zeros(P, complex); S[tones] = amp * P / 2 * np.exp(1j * ph); S[[P - t for t in tones]] = np.conj(S[tones]); return np.fft.ifft(S).real
    x = synth(ph)
    for _ in range(taper_iters):
        r = np.sqrt((x ** 2).mean()); y = np.clip(x, -1.6 * r, 1.6 * r); ph = np.angle(np.fft.fft(y)[tones]); x = synth(ph)
    m = np.abs(x).max()
    return np.array(hk), np.array(mk), np.array(tones), amp / m, ph
def room(tones, amp, ph, T, paths, noise=2e-5):
    t = np.arange(int(T * SR)) / SR; x = np.zeros_like(t)
    for g, dfun in paths:
        tau = 2 * dfun(t) / C
        for k, a, p in zip(tones, amp, ph): x += g * a * np.cos(2 * np.pi * k * DF * (t - tau) + p)
    return x + noise * rng.standard_normal(len(t))
def hum_track(x, hk, win=384, hop=192, M=64, guard=6):
    n = np.arange(win); wnd = np.hanning(win)
    E = np.exp(-2j * np.pi * np.outer(hk * DF, n) / SR) * wnd
    starts = np.arange(0, len(x) - win, hop)
    B = np.array([(E @ x[s:s + win]) * np.exp(-2j * np.pi * hk * DF * s / SR) for s in starts])
    w = np.hanning(len(hk) + 2)[1:-1]; S = B.mean(0)
    d0 = int(np.argmax(np.abs(np.fft.ifft(S * w, M))))
    Pr = np.fft.ifft((B - S) * w, M, axis=1)
    cand = [m for m in range(M) if min((m - d0) % M, (d0 - m) % M) > guard]
    fc = hk.mean() * DF
    Mo = np.array([-(np.unwrap(np.angle(Pr[:, m])) - np.angle(Pr[0, m])) * C / (2 * np.pi * fc) / 2 for m in cand])
    return (starts + win / 2) / SR, np.median(Mo, 0)
def move(t0, dur, d0, dist):
    def f(t):
        u = np.clip((t - t0) / dur, 0, 1); return d0 - dist * (u - np.sin(2 * np.pi * u) / (2 * np.pi))
    return f
if __name__ == '__main__':
    hum_f = [15250 + 250 * i for i in range(8)]          # 15.25-17.0 kHz, 8 tones
    for gain in (3.0,):
        for with_map in (False, True):
            if with_map: hk, mk, tones, amp, ph = design(hum_f, 17750, 22000, gain)
            else:
                hk = np.array([int(round(f / DF)) for f in hum_f]); tones = hk; amp = np.ones(len(hk)) / len(hk) * 0.5; ph = rng.uniform(0, 2 * np.pi, len(hk))
            share = (amp[:len(hk)] ** 2).sum() / (amp ** 2).sum()
            print(f'== {"hum + map 17.75-22 kHz" if with_map else "hum only"} (hum share of power {100*share:.0f}%' + (f', map tone amp {amp[-60]:.4f} vs plain tones 0.0587)' if with_map else ')'))
            for dur in (8.0, 4.0, 2.0, 1.0):
                x = room(tones, amp, ph, 12, [(1.0, lambda t: 0.02 + 0 * t), (0.05, lambda t: 0.84 + 0 * t), (0.012, move(4, dur, 1.0, 0.25))])
                tt, cum = hum_track(x, hk)
                a0 = cum[(tt > 2) & (tt < 3.5)].mean(); b0 = cum[tt > tt[-1] - 1.5].mean()
                print(f'   25 cm in {dur:.0f} s (peak {50/dur:.0f} cm/s): hum reads {100*(b0-a0):+6.1f} cm')
