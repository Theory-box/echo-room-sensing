# Hum ("hologram") analysis: 16 steady tones; per tone, the received complex value (baseband) = constant direct sound
# + room reflections that rotate as the phone moves. Remove the constant part, unwrap the phase -> path change.
# Also: inverse FFT across the tones = a coarse distance profile (4.3 cm steps, repeats every 0.69 m) whose phase is
# tracked continuously at 250 Hz.
import numpy as np, math, sys, json
SR, C = 48000, 343.0
N, F0, DF, BLK = 16, 17000, 250, 192
FK = F0 + DF * np.arange(N)

def hum_phases():
    seed = 12345; ph = []
    for _ in range(N):
        seed = (seed * 16807) % 2147483647; ph.append(2 * math.pi * seed / 2147483647)
    return np.array(ph)

def baseband(x, phases):
    """x: mic samples. returns (blocks, N) complex: per 192-sample block, each tone's amplitude/phase re what was played"""
    nb = len(x) // BLK; t = np.arange(nb * BLK) / SR; xx = x[:nb * BLK]
    out = np.zeros((nb, N), complex)
    for k in range(N):
        out[:, k] = (xx * np.exp(-1j * (2 * np.pi * FK[k] * t + phases[k]))).reshape(nb, BLK).mean(1) * 2
    return out          # 250 blocks per second

def circle_centre(z):
    """least-squares circle through complex points (Kasa): the static vector is the centre the moving part circles"""
    x, y = z.real, z.imag
    A = np.column_stack([x, y, np.ones_like(x)]); b = x * x + y * y
    c = np.linalg.lstsq(A, b, rcond=None)[0]
    return complex(c[0] / 2, c[1] / 2)

def displacement(B, win=None):
    """per tone: remove the static part (circle centre over the whole stretch), unwrap the phase, -> one-way path
    change in metres (+ = path got longer). Returns (blocks, N)"""
    D = np.zeros(B.shape)
    for k in range(N):
        z = B[:, k] - circle_centre(B[:, k])
        ph = np.unwrap(np.angle(z))
        D[:, k] = -(ph - ph[0]) * C / (2 * np.pi * FK[k]) / 2
    return D

if __name__ == '__main__' and sys.argv[1] == 'sim':
    # synthetic: direct sound + phone body (constant) + wall ahead 1.0 m + wall behind 2.2 m + clutter; phone moves
    rng = np.random.default_rng(1); ph = hum_phases(); T = 20; t = np.arange(T * SR) / SR
    fwd = 0.02 * np.sin(2 * np.pi * 0.5 * t) + 0.01 * np.sin(2 * np.pi * 1.3 * t + 1) + 0.002 * t   # phone forward motion (m)
    refl = [(0.0, 1.0, 0.0002, 0)]   # (distance, gain, extra, direction) direct sound: delay ~0
    paths = [(0.03, 1.0, +0), (0.06, 0.2, 0), (1.0, float(sys.argv[2]) if len(sys.argv) > 2 else 0.01, +1), (2.2, 0.004, -1), (1.7, 0.002, 0.3)]
    x = np.zeros_like(t)
    for (d, g, u) in paths:
        tau = 2 * (d - u * fwd) / C if d > 0.1 else d / C * np.ones_like(t)
        for k in range(N): x += g * np.cos(2 * np.pi * FK[k] * (t - tau) + ph[k])
    x += 0.0005 * rng.standard_normal(len(t))
    B = baseband(x, ph); Dm = displacement(B)
    tb = (np.arange(B.shape[0]) + 0.5) * BLK / SR; truth = -np.interp(tb, t, fwd); truth -= truth[0]   # wall ahead: path shrinks
    est = np.median(Dm, 1)
    print(f'per-tone agreement (sd across tones) median {1000*np.median(Dm.std(1)):.2f} mm')
    print(f'estimate vs truth (wall ahead path change): rms error {1000*np.sqrt(np.mean((est-truth)**2)):.2f} mm, truth range {1000*(truth.max()-truth.min()):.1f} mm, corr {np.corrcoef(est,truth)[0,1]:.3f}')

def profiles(B, static=None):
    """remove the static part (mean over the stretch), Hann-weight the tones, inverse FFT across tones ->
    (blocks, 64) complex delay profile, 0.69 m repeat distance, ~4.3 cm resolution (zero-padded to 64 bins)"""
    S = B.mean(0) if static is None else static
    w = np.hanning(N + 2)[1:-1]
    P = np.fft.ifft((B - S) * w, 64, axis=1)
    return P   # bin m <-> one-way distance m/64 * C/(2*DF) (mod 0.686 m)

def bin_motion(P, m):
    ph = np.unwrap(np.angle(P[:, m])); fc = F0 + DF * (N - 1) / 2
    return -(ph - ph[0]) * C / (2 * np.pi * fc) / 2

if __name__ == '__main__' and sys.argv[1] == 'sim2':
    rng = np.random.default_rng(1); ph = hum_phases(); T = 20; t = np.arange(T * SR) / SR
    fwd = 0.02 * np.sin(2 * np.pi * 0.5 * t) + 0.01 * np.sin(2 * np.pi * 1.3 * t + 1) + 0.002 * t
    paths = [(0.03, 1.0, 0), (0.06, 0.2, 0), (1.0, 0.003, +1), (2.2, 0.004, -1), (1.7, 0.002, 0.3)]
    x = np.zeros_like(t)
    for (d, g, u) in paths:
        tau = 2 * (d - u * fwd) / C if d > 0.1 else d / C * np.ones_like(t)
        for k in range(N): x += g * np.cos(2 * np.pi * FK[k] * (t - tau) + ph[k])
    x += 0.0005 * rng.standard_normal(len(t))
    B = baseband(x, ph); P = profiles(B); tb = (np.arange(B.shape[0]) + 0.5) * BLK / SR
    amb = C / (2 * DF); mag = np.abs(P).mean(0)
    print('profile peaks (bin: distance mod 0.686 m, strength):', [(m, round(m / 64 * amb, 3), round(float(mag[m]), 5)) for m in np.argsort(-mag)[:5]])
    fw = np.interp(tb, t, fwd); fw -= fw[0]
    for (d, g, u) in paths[2:]:
        m = int(round((d % amb) / amb * 64)) % 64
        mot = bin_motion(P, m); truth = -u * fw
        print(f'  reflector {d} m (dir {u:+}): bin {m}, tracked path change vs truth: corr {np.corrcoef(mot, truth)[0,1]:+.3f}, rms err {1000*np.sqrt(np.mean((mot-truth)**2)):.2f} mm (range {1000*(truth.max()-truth.min()):.1f} mm)')
