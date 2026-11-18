# Hum analysis, parameterised (hum-only: 16 tones 17000+250k, block 192; hybrid: 8 tones 16320+240k, block 200)
import numpy as np, math
SR, C = 48000, 343.0
def lcg_phases(n, seed):
    ph = []
    for _ in range(n):
        seed = (seed * 16807) % 2147483647; ph.append(2 * math.pi * seed / 2147483647)
    return np.array(ph)
class Hum:
    def __init__(self, n, f0, df, seed):
        self.n, self.f0, self.df = n, f0, df; self.fk = f0 + df * np.arange(n); self.blk = int(round(SR / df)); self.ph = lcg_phases(n, seed)
    def baseband(self, x, lowpass=None):
        if lowpass:   # keep only the hum's band (removes the clicks above it)
            from scipy.signal import firwin, filtfilt
            hcoef = firwin(801, [self.f0 - 300, lowpass], pass_zero=False, fs=SR, window=('kaiser', 10))
            x = filtfilt(hcoef, [1.0], x)
        nb = len(x) // self.blk; t = np.arange(nb * self.blk) / SR; xx = x[:nb * self.blk]
        out = np.zeros((nb, self.n), complex)
        for k in range(self.n):
            out[:, k] = (xx * np.exp(-1j * (2 * np.pi * self.fk[k] * t + self.ph[k]))).reshape(nb, self.blk).mean(1) * 2
        return out
    def profiles(self, B, nfft=64):
        w = np.hanning(self.n + 2)[1:-1]
        return np.fft.ifft((B - B.mean(0)) * w, nfft, axis=1)
    def bin_motion(self, P, m):
        ph = np.unwrap(np.angle(P[:, m])); fc = self.f0 + self.df * (self.n - 1) / 2
        return -(ph - ph[0]) * C / (2 * np.pi * fc) / 2
    def track(self, x, guard=6, lowpass=None):
        """combined movement track: median of the unwrapped path change over all distance slots away from the
        direct sound (strongest static slot +- guard). returns (block times s, path change m)"""
        B = self.baseband(x, lowpass); w = np.hanning(self.n + 2)[1:-1]
        d0 = int(np.argmax(np.abs(np.fft.ifft(B.mean(0) * w, 64))))
        P = self.profiles(B)
        bins = [m for m in range(64) if min((m - d0) % 64, (d0 - m) % 64) > guard]
        M = np.array([self.bin_motion(P, m) for m in bins])
        return (np.arange(B.shape[0]) + 0.5) * self.blk / SR, np.median(M - M[:, :1], 0)

HUM16 = Hum(16, 17000, 250, 12345)
HYB8 = Hum(8, 16320, 240, 4242)

if __name__ == '__main__':
    # synthetic hybrid: Quiet clicks 18.5-22 kHz every 3200 samples (15/s) + 8-tone hum, reflections moving with the phone
    rng = np.random.default_rng(3); T = 20; t = np.arange(T * SR) / SR
    fwd = 0.02 * np.sin(2 * np.pi * 0.5 * t) + 0.01 * np.sin(2 * np.pi * 1.3 * t + 1) + 0.002 * t
    P = 3200; n = 1501; tt = np.arange(n) / SR; Tc = n / SR
    chirp = (0.5 - 0.5 * np.cos(2 * np.pi * np.arange(n) / (n - 1))) * np.cos(2 * np.pi * (18500 * tt + 3500 * tt * tt / (2 * Tc)))
    loop = np.zeros(P); loop[:n] = 0.6 * chirp
    h = HYB8; hum = sum(np.cos(2 * np.pi * h.fk[k] * np.arange(P) / SR + h.ph[k]) for k in range(h.n)); loop += 0.3 * hum / np.abs(hum).max()
    def play(tau):   # loop delayed by tau(t) seconds (fractional, interpolated)
        idx = (t - tau) * SR; return np.interp(idx % P, np.arange(P), loop, period=P)
    import sys
    for clicks_on in (False, True):
        if not clicks_on: loop2 = loop.copy(); loop[:n] -= 0.6 * chirp
        x = np.zeros_like(t)
        for (d, g, u) in [(0.03, 1.0, 0), (0.06, 0.2, 0), (1.0, 0.01, 1), (2.2, 0.004, -1)]:
            tau = 2 * (d - u * fwd) / C if d > 0.1 else d / C * np.ones_like(t)
            x += g * play(tau)
        x += 0.0003 * rng.standard_normal(len(t))
        tb, est = h.track(x, lowpass=18250)
        tr = -np.interp(tb, t, fwd); tr -= tr[0]
        print(f'clicks {"ON " if clicks_on else "OFF"}: hum track vs truth corr {np.corrcoef(est, tr)[0,1]:+.3f}, rms err {1000*np.sqrt(np.mean((est-tr)**2)):.2f} mm over {1000*(tr.max()-tr.min()):.0f} mm')
        if not clicks_on: loop = loop2
