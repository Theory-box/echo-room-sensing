import numpy as np
exec(open('mic3.py').read().split("results = {}")[0])
def jit(A, m0):   # strongest echo in 0.45-1.5 m per click (3-click average), residual vs a 0.6 s running mean
    lo, hi = int(0.45 / s2m), int(1.5 / s2m)
    H = np.array([A[c + lo:c + hi] for c in clicks[m0]]); H = np.array([H[max(0, i - 2):i + 1].mean(0) for i in range(len(H))])
    pk = (np.argmax(H, 1) + lo) * s2m
    sm = np.convolve(pk, np.ones(9) / 9, mode='same'); r = (pk - sm)[4:-4]
    return 100 * np.median(np.abs(np.diff(pk))), 100 * r.std(), pk
m0 = (tsec >= 7.5) & (tsec < 16)
for name in ('low 2-8 kHz', 'quiet 16-22 kHz'):
    tp = bands[name]; E = [np.abs(mf(x[:, c], tp)) for c in range(3)]
    s1, r1, p1 = jit(E[0], m0)
    out = f'{name}: mic1 alone step {s1:.2f} cm, residual {r1:.2f} cm'
    for L2 in (22,):
        e2 = np.roll(E[1], -L2); e3 = np.roll(E[2], -L2)
        w2 = (E[0][clicks[m0][0]] / E[1][clicks[m0][0]])   # rough scale to mic1
        g = np.median(E[0]) / np.median(E[1]); g3 = np.median(E[0]) / np.median(E[2])
        comb = np.sqrt(E[0] ** 2 + (g * e2) ** 2) ; comb3 = np.sqrt(E[0] ** 2 + (g * e2) ** 2 + (g3 * e3) ** 2)
        s2, r2, p2 = jit(comb, m0); s3, r3, _ = jit(comb3, m0)
        out += f' | +mic2 (shifted {L2}) step {s2:.2f}, residual {r2:.2f} | +mic2+mic3 step {s3:.2f}, residual {r3:.2f}'
    print(out)
