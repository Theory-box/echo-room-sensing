import numpy as np, json, math, sys, importlib.util
from scipy.io import wavfile
from scipy.signal import butter, filtfilt
spec = importlib.util.spec_from_file_location('hum', 'hum.py'); hum = importlib.util.module_from_spec(spec); sys.argv = ['x', 'none']; spec.loader.exec_module(hum)
SR, C, BLK = 48000, 343.0, 192
base = 'logs/sweep-20261118-133442-913'
d = json.load(open(base + '-sonar_log.json')); fr = d['frames']
sr, x = wavfile.read(base + '-raw_audio.wav'); x = x.astype(np.float64)
end, nraw = int(d['raw'].split('|')[1]), int(d['raw'].split('|')[2]); start = end - nraw
# recording sample -> page-clock ms (from the capture clock logged each reading)
FR = np.array([f['fr'] for f in fr if f.get('tc')], float); TC = np.array([f['tc'] for f in fr if f.get('tc')], float)
k, b0 = np.polyfit(FR, TC, 1); print(f'clock fit: {1000*k*SR/1000:.4f} ms per ms (should be ~1), residual sd {np.std(TC-(k*FR+b0)):.1f} ms')
B = hum.baseband(x[:, 0], hum.hum_phases())          # 250 blocks/s
nb = B.shape[0]; tb_ms = k * (start + (np.arange(nb) + 0.5) * BLK) + b0
T0 = fr[0]['t']; tsec = (tb_ms - T0) / 1000
print(f'blocks {nb} ({nb/250:.1f} s); tone amplitudes median {np.median(np.abs(B)):.4f}')
# how much does each tone's complex value move? (static direct sound vs changing room part)
S = B.mean(0); dyn = np.abs(B - S); print('per tone: changing part / static part (dB):', np.round(20*np.log10(np.median(dyn,0)/np.abs(S)),1))
# delay profile of the static part (direct sound position) and of the changing part
w = np.hanning(hum.N + 2)[1:-1]
Ps = np.abs(np.fft.ifft(S * w, 64)); amb = C / (2 * hum.DF)
print('static profile peak bin', int(np.argmax(Ps)), ' (bins are', round(amb/64*100,2), 'cm each, repeat every', round(amb,3), 'm)')
P = hum.profiles(B); mag = np.abs(P).mean(0)
order = np.argsort(-mag)[:8]; print('changing part: strongest bins', [(int(m), round(float(mag[m]),5)) for m in order])
# motion sensor forward displacement (band 0.15-2 Hz) on the block grid
psi = np.radians(np.array([f['yaw'] for f in fr]) + 180); ty = np.array([f['t'] for f in fr], float)
A = np.array([a for f in fr for a in f.get('ac', [])], float); A = A[np.argsort(A[:, 0])]
psiA = np.interp(A[:, 0], ty, np.unwrap(psi)); af = A[:, 1] * np.sin(psiA) + A[:, 2] * np.cos(psiA); ar = A[:, 1] * np.cos(psiA) - A[:, 2] * np.sin(psiA)
fs = 250; bb, aa = butter(2, [0.15 / (fs / 2), 2.0 / (fs / 2)], 'band')
def disp_from_acc(a):
    g = np.interp(tb_ms, A[:, 0], a); g = filtfilt(bb, aa, g - g.mean())
    n = len(g); F = np.fft.rfftfreq(n, 1 / fs); Sg = np.fft.rfft(g); wv = 2 * np.pi * F; Sg[1:] /= -(wv[1:] ** 2); Sg[0] = 0
    return filtfilt(bb, aa, np.fft.irfft(Sg, n))
xf, xr = disp_from_acc(af), disp_from_acc(ar)
print(f'motion sensor: forward movement rms {100*xf.std():.2f} cm, sideways {100*xr.std():.2f} cm')
heads = np.array([f['h'] for f in fr]); print('heading range during recording', heads.min(), heads.max())
def best_lag(u, v, maxl=100):
    best = None
    for L in range(-maxl, maxl + 1, 2):
        a, b2 = (u[L:], v[:len(v) - L]) if L >= 0 else (u[:L], v[-L:])
        c = np.corrcoef(a, b2)[0, 1]
        if best is None or abs(c) > abs(best[0]): best = (c, L)
    return best
print('per strongest bin: hum-tracked path change (band-passed like the sensor) vs motion sensor forward movement')
for m in order[:6]:
    mot = hum.bin_motion(P, int(m)); mb = filtfilt(bb, aa, mot - mot.mean())
    c0 = np.corrcoef(mb, xf)[0, 1]; c, L = best_lag(mb, xf)
    sc = np.dot(mb, xf) / np.dot(xf, xf)
    print(f'  bin {int(m):2d}: path change rms {1000*mb.std():6.2f} mm | corr with forward motion {c0:+.2f} (best {c:+.2f} at {L*4:+d} ms) | scale {sc:+.2f} | corr with sideways {np.corrcoef(mb, xr)[0,1]:+.2f}')
np.savez('hum_real_out.npz', P=P, tsec=tsec, xf=xf, xr=xr)
