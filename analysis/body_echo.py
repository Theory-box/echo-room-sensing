# Is there an echo from the user's body (behind the phone, ~25-45 cm) in the raw recordings? Quiet (long) chirp:
# 16-22 kHz, 1501 samples, one click per 3200 samples. Matched filter on both mics, envelope re the direct-sound peak,
# per 1 cm distance step out to 1 m, median over clicks, plus how much each step varies click to click. A body echo
# would be a bump above the smooth decay of the phone's own ringing, steady (it moves with the phone).
import sys, json, numpy as np
from scipy.io import wavfile
SR, C, P = 48000, 343.0, 3200
n = 1501; t = np.arange(n) / SR; T = n / SR
tpl = (0.5 - 0.5 * np.cos(2 * np.pi * np.arange(n) / (n - 1))) * np.exp(1j * 2 * np.pi * (16000 * t + 6000 * t * t / (2 * T)))
def mf(sig):
    N = 1 << int(np.ceil(np.log2(len(sig) + n))); return np.fft.ifft(np.fft.fft(sig, N) * np.conj(np.fft.fft(tpl, N)))[:len(sig)]
s2m = C / (2 * SR)
for s in sys.argv[1:]:
    sr, x = wavfile.read(f'logs/sweep-20261118-{s}-raw_audio.wav'); x = x.astype(np.float64)
    if x.ndim == 1: x = x[:, None]
    out = []
    for ch in range(min(2, x.shape[1])):
        e = np.abs(mf(x[:, ch]))
        k = int(np.argmax(e[:P])); clicks = []
        while k + P < len(e):
            lo = max(0, k - 20); kk = lo + int(np.argmax(e[lo:k + 21])); clicks.append(kk); k = kk + P
        nb = int(1.0 / s2m); prof = np.array([20 * np.log10(e[c:c + nb] / e[c] + 1e-9) for c in clicks if c + nb < len(e)])
        med = np.median(prof, 0); var = np.std(prof, 0)
        cm = np.arange(nb) * s2m * 100
        # smooth decay model: fit to 5-15 cm and 55-70 cm, look at residual bumps 15-55 cm
        sel = lambda a, b: (cm >= a) & (cm < b)
        bumps = []
        for a in range(10, 60, 3):
            m = sel(a, a + 3); bumps.append((a, med[m].max()))
        out.append((ch, len(prof), bumps, [(a, float(np.median(var[sel(a, a + 3)]))) for a in range(10, 60, 9)]))
    for ch, nc, bumps, vv in out:
        print(f"{s} mic{ch+1} ({nc} clicks): level dB re direct by distance (cm): " + ' '.join(f'{a}:{v:.0f}' for a, v in bumps) + ' | click-to-click sd: ' + ' '.join(f'{a}:{v:.1f}' for a, v in vv))
