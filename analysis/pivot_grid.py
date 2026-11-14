import subprocess, json, sys, os, itertools
PY = sys.argv[1:]
truth_phi, truth = 20, {20: 2.8, 110: 2.5, 200: 1.6, 290: 1.1}
def ok(r):
    p = r["phi0"]; err = min(abs(((p - truth_phi + 45) % 90) - 45), 99)
    if err > 6: return False, err
    for b, d in r["walls"]:
        tb = min(truth, key=lambda t: abs(((b - t + 180) % 360) - 180))
        if abs(((b - tb + 180) % 360) - 180) > 8 or abs(d - truth[tb]) > 0.06: return False, err
    return True, err
res = {}
for jit, seed in itertools.product([0.005, 0.015, 0.03], [21, 22, 23, 24]):
    s = f"sim/g{jit}_{seed}"
    subprocess.run(PY + ["ers/analysis/simulate.py", s, "--seed", str(seed), "--clutter", "8", "--yaw-jitter", "3",
                         "--pos-jitter", str(jit), "--earpiece", "0.32,0.63", "--chassis"], capture_output=True)
    for name, extra in (("sweep", []), ("R", ["--source", "R", "--anchor", "16.5"]), ("R12", None)):
        if extra is None: continue
        out = subprocess.run(PY + ["ers/analysis/fit_walls.py", s, "out/g", *extra], capture_output=True, text=True).stdout.strip().splitlines()[-1]
        r = json.loads(out); good, err = ok(r)
        res.setdefault((name, jit), []).append((good, round(err)))
for (name, jit), v in sorted(res.items()):
    print(f"{name:6s} pivot drift {jit*100:4.1f} cm: {sum(g for g,_ in v)}/{len(v)} correct  (orientation errors {[e for _,e in v]})")
