# Are the echoes the mirror (image-source) model predicts actually in the recordings?
# Box from the whole same-spot sweep (walls j at normal rot+90j, distance D_j from the turning spot; phone ARM ahead).
#  corner (vertical edge where walls j, j+1 meet): a two-wall retroreflector -> echo at the horizontal distance from the
#     phone to the corner point, heard whenever the corner is within +-CB deg of where the phone points
#  wall-body-wall: wall echo bounces off you/the phone and goes round again -> 2 x the wall echo distance, facing the wall
#  front-back: phone -> wall j -> opposite wall -> wall j -> phone ... second-order image: one-way distance D_j + D_opp
#     (= room width + the arm term), facing wall j or its opposite
# For each kind: share of readings (when the condition holds) with an echo within +-TOL of the prediction, vs the same
# count at the prediction shifted by +-15..40 cm (chance level from everything else that is heard).
import json, math, sys, numpy as np, importlib.util
sys.argv = ['x', 'none']
spec = importlib.util.spec_from_file_location('rf', 'roomfit.py'); rf = importlib.util.module_from_spec(spec); spec.loader.exec_module(rf)
ARM, TOL, CB = 0.25, 0.04, 40
def ad(a, b): return (a - b + 540) % 360 - 180
SESS = ['161659-916', '161753-114', '161829-437', '161910-971', '140553-471', '140408-771', '162000-283', '141954-224', '163656-046', '120930-256', '121421-809']
SHIFTS = [-0.40, -0.30, -0.20, -0.15, 0.15, 0.20, 0.30, 0.40]
tot = {}
for s in SESS:
    try: d = json.load(open(f'logs/sweep-20261118-{s}-sonar_log.json'))
    except Exception: continue
    fr = d['frames']; hs = [x['h'] for x in fr]
    if max(hs) - min(hs) < 300: continue
    h = []; r = []
    for x in fr:
        for e in x['e']:
            if e[10] and e[0] > 0.35: h.append(x['h']); r.append(e[0] - (e[12] or 0) / 100)
    p, sc, votes = rf.fit_vote(np.array(h), np.array(r)); rot, D = p[0], p[1:5]; cl = int(len(r) * 0.08 / 4)
    strong = [v > 2 * cl for v in votes]
    N = [np.array([math.sin(math.radians(rot + 90 * j)), math.cos(math.radians(rot + 90 * j))]) for j in range(4)]
    stats = {}
    def add(kind, hit, base):
        a = stats.setdefault(kind, [0, 0, 0.0]); a[0] += 1; a[1] += hit; a[2] += base
    for x in fr:
        th = x['h']; u = np.array([math.sin(math.radians(th)), math.cos(math.radians(th))]); ph = ARM * u
        R = np.array([e[0] for e in x['e'] if e[0] > 0.35])
        def near(v): return bool(len(R)) and bool(np.any(np.abs(R - v) < TOL))
        firsts = [D[j] - ARM * math.cos(math.radians(ad(th, rot + 90 * j))) for j in range(4) if abs(ad(th, rot + 90 * j)) < 35]
        def test(kind, v):
            if v > 4.9 or any(abs(v - f) < 2 * TOL for f in firsts): return     # would be confused with a wall echo
            add(kind, near(v), np.mean([near(v + sh) for sh in SHIFTS]))
        for j in range(4):
            k = (j + 1) % 4
            if not (strong[j] and strong[k]): continue
            c = D[j] * N[j] + D[k] * N[k]; v = c - ph; dist = np.linalg.norm(v)
            ang = math.degrees(math.atan2(v[0], v[1]))
            if abs(ad(ang, th)) < CB: test('corner', dist)
        for j in range(4):
            off = ad(th, rot + 90 * j)
            if abs(off) >= 25 or not strong[j]: continue
            r1 = D[j] - ARM * math.cos(math.radians(off))
            test('2x wall (via you)', 2 * r1)
            o = (j + 2) % 4
            if strong[o]: test('front-back (room width)', D[j] + D[o] - ARM * math.cos(math.radians(off)))
    w1, w2 = D[0] + D[2], D[1] + D[3]
    print(f"{s} {d['settings']['ping'][:10]:10s} box {min(w1,w2):.2f} x {max(w1,w2):.2f} walls {''.join('*' if q else '.' for q in strong)} | " +
          ' | '.join(f'{k}: {100*v[1]/v[0]:.0f}% vs chance {100*v[2]/v[0]:.0f}% (n {v[0]})' for k, v in stats.items()))
    for k, v in stats.items():
        a = tot.setdefault(k, [0, 0, 0.0]); a[0] += v[0]; a[1] += v[1]; a[2] += v[2]
print('ALL: ' + ' | '.join(f'{k}: {100*v[1]/v[0]:.1f}% of readings vs chance {100*v[2]/v[0]:.1f}% -> x{v[1]/max(v[2],1e-9):.2f} (n {v[0]})' for k, v in tot.items()))
