import subprocess, json, sys, itertools
PY = sys.argv[1:]
truth_phi, truth = 20, {20: 2.8, 110: 2.5, 200: 1.6, 290: 1.1}
def ok(r):
    p = r["phi0"]; err = abs(((p - truth_phi + 45) % 90) - 45)
    werr = 0
    for b, d in r["walls"]:
        tb = min(truth, key=lambda t: abs(((b - t + 180) % 360) - 180))
        if abs(((b - tb + 180) % 360) - 180) > 8: return False, err, 9.99
        werr = max(werr, abs(d - truth[tb]))
    return (err <= 6 and werr <= 0.06), err, werr
cases = {"A centred": "0,0", "B centred, 1 cm off": "0.008,0.006", "C 18 cm off-centre": "0,0.18", "D off-centre diagonal": "0.12,-0.10"}
for name, pv in cases.items():
    rows = []
    for seed in (31, 32, 33):
        s = f"sim/lz{seed}_{pv.replace(',', '_')}"
        subprocess.run(PY + ["ers/analysis/simulate.py", s, "--seed", str(seed), "--clutter", "8", "--yaw-jitter", "3",
                             "--pos-jitter", "0.003", "--pivot", pv], capture_output=True)
        out = subprocess.run(PY + ["ers/analysis/fit_walls.py", s, "out/lz", "--pivot", "auto"], capture_output=True, text=True).stdout.strip().splitlines()[-1]
        r = json.loads(out); good, e, w = ok(r)
        rows.append(f"{'OK ' if good else 'BAD'} orient err {e:.0f} deg, worst wall {w*100:.0f} cm, pivot found {r['pivot']}")
    print(f"== {name} (true pivot {pv})"); [print("   ", x) for x in rows]
