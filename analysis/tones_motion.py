# Millimetre motion from the all-tone recording: sliding 2048-sample windows (hop 256 = 187.5/s); because the played
# signal repeats every 2048 samples, any window gives the full response, rotated by the window start (undone below).
import numpy as np, json, sys, math
from scipy.io import wavfile
from scipy.signal import butter, filtfilt
SR, C, P, K0, NT, HOP = 48000, 343.0, 2048, 683, 256, 256
TOPN = int(__import__('os').environ.get('TOPN', '20'))
def motion_track(x, guard=24, M=1024):
    starts = np.arange(0, len(x) - P, HOP)
    kk = K0 + np.arange(NT)
    B = np.zeros((len(starts), NT), complex)
    for i, s in enumerate(starts):
        Y = np.fft.fft(x[s:s + P])[kk]
        B[i] = Y * np.exp(-2j * np.pi * kk * s / P)      # undo the window-start rotation
    w = np.hanning(NT + 2)[1:-1]
    d0 = int(np.argmax(np.abs(np.fft.ifft(B.mean(0) * w, M))))
    Pr = np.fft.ifft((B - B.mean(0)) * w, M, axis=1)
    cand = [m for m in range(0, M, 2) if min((m - d0) % M, (d0 - m) % M) > guard]
    mag = np.abs(Pr[:, cand]).mean(0)
    bins = [cand[i] for i in np.argsort(-mag)[:TOPN]]      # only slots that actually hold changing echoes
    fc = (K0 + NT / 2) * SR / P
    Mo = np.array([np.unwrap(np.angle(Pr[:, m])) for m in bins])
    Mo = -(Mo - Mo[:, :1]) * C / (2 * np.pi * fc) / 2
    return (starts + P / 2) / SR, np.median(Mo, 0), Mo
def evaluate(base):
    d = json.load(open(base + '-sonar_log.json')); fr = d['frames']
    sr, x = wavfile.read(base + '-raw_audio.wav'); x = x.astype(np.float64)[:, 0]
    end, nraw = int(d['raw'].split('|')[1]), int(d['raw'].split('|')[2]); start = end - nraw
    ok = [f for f in fr if f.get('tc')]; k, b0 = np.polyfit([f['fr'] for f in ok], [f['tc'] for f in ok], 1)
    tb, comb, Mo = motion_track(x)
    tms = k * (start + tb * SR) + b0
    yt = np.array([f['t'] for f in fr], float); psi = np.unwrap(np.radians(np.array([f['yaw'] for f in fr]) + 180))
    A = np.array([a for f in fr for a in f.get('ac', [])], float); A = A[np.argsort(A[:, 0])]
    pa = np.interp(A[:, 0], yt, psi); af = A[:, 1] * np.sin(pa) + A[:, 2] * np.cos(pa)
    fs = SR / HOP; bb, aa = butter(2, [0.15 / (fs / 2), 2.0 / (fs / 2)], 'band')
    g = filtfilt(bb, aa, np.interp(tms, A[:, 0], af) - af.mean()); n = len(g)
    F = np.fft.rfftfreq(n, 1 / fs); S = np.fft.rfft(g); wv = 2 * np.pi * F; S[1:] /= -(wv[1:] ** 2); S[0] = 0
    xf = filtfilt(bb, aa, np.fft.irfft(S, n)); cb = filtfilt(bb, aa, comb - comb.mean())
    best = None
    for L in range(-int(0.7 * fs), int(0.7 * fs) + 1):
        a, b = (cb[L:], xf[:n - L]) if L >= 0 else (cb[:L], xf[-L:])
        c = np.corrcoef(a, b)[0, 1]
        if best is None or abs(c) > abs(best[0]): best = (c, L / fs * 1000, np.dot(a, b) / np.dot(b, b))
    hs = np.interp(tms, yt, np.array([f['h'] for f in fr], float))
    print(f'{base[-25:]}: {tb[-1]-tb[0]:.0f} s | tone-phase motion vs sensor forward: corr {best[0]:+.2f} (tones {"later" if best[1] > 0 else "earlier"} {abs(best[1]):.0f} ms), scale {best[2]:+.2f} | sensor fwd rms {100*xf.std():.1f} cm | heading span {hs.min():.0f}..{hs.max():.0f}')
    # stillest 2 s: lowest sensor activity
    win = int(2 * fs); act = np.array([np.std(xf[i:i + win]) for i in range(0, n - win, win // 2)])
    i0 = int(np.argmin(act)) * (win // 2); seg = comb[i0:i0 + win] - comb[i0:i0 + win].mean()
    print(f'   stillest 2 s: tone-phase wobble sd {1000*seg.std():.2f} mm (sensor {1000*act.min():.2f} mm)')
    return tb, comb
if __name__ == '__main__':
    for b in sys.argv[1:]: evaluate(b)

def motion_track_tone(x, groups=16):
    """per tone (no distance slots): remove each tone's average, unwrap its phase; tones grouped in `groups` blocks of
    consecutive tones, each group summed coherently first (wider 'slot' ~ a coarse profile), median over groups"""
    starts = np.arange(0, len(x) - P, HOP); kk = K0 + np.arange(NT)
    B = np.zeros((len(starts), NT), complex)
    for i, s in enumerate(starts):
        B[i] = np.fft.fft(x[s:s + P])[kk] * np.exp(-2j * np.pi * kk * s / P)
    D = B - B.mean(0); fc = (K0 + NT / 2) * SR / P
    g = NT // groups; out = []
    for j in range(groups):
        for m in range(g):     # each tone separately within the group
            z = D[:, j * g + m]; f = (K0 + j * g + m) * SR / P
            ph = np.unwrap(np.angle(z)); out.append(-(ph - ph[0]) * C / (2 * np.pi * f) / 2)
    Mo = np.array(out)
    return (starts + P / 2) / SR, np.median(Mo, 0), Mo

def motion_track_groups(x, gsize=16, nb=8, guard=1):
    """groups of gsize neighbouring tones -> coarse profile per group (wide slots, signal of gsize tones),
    the nb strongest changing slots per group (away from the direct sound) tracked; median over all"""
    starts = np.arange(0, len(x) - P, HOP); kk = K0 + np.arange(NT)
    B = np.zeros((len(starts), NT), complex)
    for i, s in enumerate(starts):
        B[i] = np.fft.fft(x[s:s + P])[kk] * np.exp(-2j * np.pi * kk * s / P)
    out = []; Mz = 4 * gsize
    for j in range(NT // gsize):
        G = B[:, j * gsize:(j + 1) * gsize]; w = np.hanning(gsize + 2)[1:-1]
        d0 = int(np.argmax(np.abs(np.fft.ifft(G.mean(0) * w, Mz))))
        Pr = np.fft.ifft((G - G.mean(0)) * w, Mz, axis=1)
        cand = [m for m in range(Mz) if min((m - d0) % Mz, (d0 - m) % Mz) > guard * 4]
        mag = np.abs(Pr[:, cand]).mean(0)
        f = (K0 + j * gsize + gsize / 2) * SR / P
        for i in np.argsort(-mag)[:nb]:
            ph = np.unwrap(np.angle(Pr[:, cand[i]])); out.append(-(ph - ph[0]) * C / (2 * np.pi * f) / 2)
    Mo = np.array(out)
    return (starts + P / 2) / SR, np.median(Mo, 0), Mo

def motion_track_pilots(x, step=16, off=8, guard=1):
    """pilot tones only (every `step`-th tone from `off`): a 16-tone hum inside the comb -> coarse profile, strongest
    changing slots away from the direct sound, median of their unwrapped phase"""
    starts = np.arange(0, len(x) - P, HOP); kk = K0 + off + step * np.arange(NT // step)
    B = np.zeros((len(starts), len(kk)), complex)
    for i, s in enumerate(starts):
        B[i] = np.fft.fft(x[s:s + P])[kk] * np.exp(-2j * np.pi * kk * s / P)
    n = len(kk); Mz = 64; w = np.hanning(n + 2)[1:-1]
    d0 = int(np.argmax(np.abs(np.fft.ifft(B.mean(0) * w, Mz))))
    Pr = np.fft.ifft((B - B.mean(0)) * w, Mz, axis=1)
    cand = [m for m in range(Mz) if min((m - d0) % Mz, (d0 - m) % Mz) > 6]
    fc = (kk.mean()) * SR / P
    Mo = np.array([-(np.unwrap(np.angle(Pr[:, m])) - np.angle(Pr[0, m])) * C / (2 * np.pi * fc) / 2 for m in cand])
    return (starts + P / 2) / SR, np.median(Mo, 0), Mo
