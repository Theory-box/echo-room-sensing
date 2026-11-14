import sys, os, json, numpy as np
sys.path.insert(0, sys.argv[1])
from fit_walls import chirp_irs, UP
from sweep_map import log_sweep
from scipy.io import wavfile
sess = sys.argv[2]
man = json.load(open(os.path.join(sess, "session.json"), encoding="utf-8"))
sr = man["plan"]["sr"]; sw = man["plan"]["sweep"]; sweep = log_sweep(sr, sw["f1"], sw["f2"], sw["T"])
fs = sr * UP; rows = []
for c in man["captures"]:
    _, x = wavfile.read(os.path.join(sess, c["file"].split("/")[-1])); x = x.astype(float)
    R, dR = chirp_irs(x, sweep, sr, man["plan"], "R"); L, dL = chirp_irs(x, sweep, sr, man["plan"], "L")
    # common time origin: both IRs share the sweep-based timeline, index = pre (2 ms) + delay
    r = {}
    for m in range(2):
        eR, eL = np.abs(R[m]), np.abs(L[m])
        pR, pL = int(np.argmax(eR[: int(0.006 * fs)])), int(np.argmax(eL[: int(0.006 * fs)]))
        w0, w1 = int(0.002 * fs) + int(0.003 * fs), int(0.002 * fs) + int(0.025 * fs)  # echoes 3-25 ms after t0
        r[m] = dict(direct_dB=20 * np.log10(eL[pL] / eR[pR]), arrival_diff_samples=(pL - pR) / UP,
                    echo_ratio=float(np.sum(eL[w0:w1] ** 2) / np.sum(eR[w0:w1] ** 2)),
                    echo_corr=float(np.corrcoef(eL[w0:w1], eR[w0:w1])[0, 1]),
                    R_direct_idx=pR / UP, L_direct_idx=pL / UP)
    rows.append(r)
for m, name in ((0, "bottom mic"), (1, "back mic")):
    g = lambda k: np.array([row[m][k] for row in rows])
    print(f"{name}: L-vs-R direct {np.median(g('direct_dB')):.1f} dB, L arrives {np.median(g('arrival_diff_samples')):+.1f} samples vs R, "
          f"echo energy L/R {np.median(g('echo_ratio')):.2f} (range {g('echo_ratio').min():.2f}-{g('echo_ratio').max():.2f}), "
          f"echo envelope corr {np.median(g('echo_corr')):.2f}")
print("R direct idx bottom/back (samples, per stop):", [ (round(r[0]['R_direct_idx'],1), round(r[1]['R_direct_idx'],1)) for r in rows])
