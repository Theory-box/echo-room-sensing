# Hum band design: dense map tones (23.4 Hz apart) above a gap, a few hum tones (375 Hz apart) below, all repeating
# every 2048 samples. Simulate a wall moving a known 25 cm at hand speeds; read the hum with short windows.
import numpy as np, math, sys
SR, C, P = 48000, 343.0, 2048
rng = np.random.default_rng(0)
def design(hum_k, map_k0, map_k1, hum_gain):
    tones = list(hum_k) + list(range(map_k0, map_k1 + 1))
    amp = np.array([hum_gain] * len(hum_k) + [1.0] * (map_k1 - map_k0 + 1))
    ph = rng.uniform(0, 2 * np.pi, len(tones))
    # peak taming (clip and refilter)
    n = np.arange(P)
    def synth(ph):
        S = np.zeros(P, complex); S[tones] = amp * P / 2 * np.exp(1j * ph); S[[P - t for t in tones]] = np.conj(S[tones])
        return np.fft.ifft(S).real
    x = synth(ph)
    for _ in range(60):
        r = np.sqrt((x ** 2).mean()); y = np.clip(x, -1.6 * r, 1.6 * r); ph = np.angle(np.fft.fft(y)[tones]); x = synth(ph)
    m = np.abs(x).max()
    return np.array(tones), amp / m, ph, x / m
def synth_room(tones, amp, ph, T, paths, noise=2e-5):
    t = np.arange(int(T * SR)) / SR; x = np.zeros_like(t)
    for g, dfun in paths:
        tau = 2 * dfun(t) / C
        for k, a, p in zip(tones, amp, ph): x += g * a * np.cos(2 * np.pi * k * SR / P * (t - tau) + p)
    return x + noise * rng.standard_normal(len(t))
def hum_track(x, hum_k, win, hop, taper=True, tau_s=3.0):
    hum_k = np.array(hum_k); n = np.arange(win); wnd = np.hanning(win) if taper else np.ones(win)
    E = np.exp(-2j * np.pi * np.outer(hum_k, n) / P) * wnd
    starts = np.arange(0, len(x) - win, hop); S = np.zeros(len(hum_k), complex); cum = 0; last = None; out = []
    fc = hum_k.mean() * SR / P
    for i, s in enumerate(starts):
        b = (E @ x[s:s + win]) * np.exp(-2j * np.pi * hum_k * s / P)
        al = max(hop / (tau_s * SR), 1 / (i + 1)); S += al * (b - S)
        z = b - S
        if i > 40 and last is not None:
            step = np.angle(np.sum(z * np.conj(last)))           # power-weighted common phase step across hum tones
            cum += -step * C / (2 * np.pi * fc) / 2
        last = z; out.append(cum)
    return (starts + win / 2) / SR, np.array(out)
def move(t0, dur, d0, dist):
    def f(t):
        u = np.clip((t - t0) / dur, 0, 1); return d0 - dist * (u - np.sin(2 * np.pi * u) / (2 * np.pi))
    return f
if __name__ == '__main__':
    configs = [
        ('4 hum tones 15.6-16.8 kHz x4, map 17.9-22', [667, 683, 699, 715], 763, 938, 4.0),
        ('6 hum tones 15.3-17.1 kHz x3, map 17.9-22', [651, 667, 683, 699, 715, 731], 779, 938, 3.0),
    ]
    for name, hk, m0, m1, g in configs:
        tones, amp, ph, x0 = design(hk, m0, m1, g)
        hp = (amp[:len(hk)] ** 2).sum() / (amp ** 2).sum()
        # map tone level vs the plain 256-tone design (map amplitude after normalisation)
        print(f'== {name}: hum share of power {100*hp:.0f}%, crest {1/np.sqrt((x0**2).mean()):.2f}, map tone amplitude {amp[-50]:.4f}')
        for dur in (8.0, 2.0, 1.0):
            x = synth_room(tones, amp, ph, 12, [(1.0, lambda t: 0.02 + 0 * t), (0.05, lambda t: 0.84 + 0 * t), (0.012, move(4, dur, 1.0, 0.25))])
            for win in (256, 512):
                tt, cum = hum_track(x, hk, win, 256)
                a0 = cum[(tt > 2) & (tt < 3.5)].mean(); b0 = cum[tt > tt[-1] - 1.5].mean()
                print(f'   25 cm in {dur:.0f} s (peak {50/dur:.0f} cm/s), {win}-sample window: hum reads {100*(b0-a0):+6.1f} cm')
