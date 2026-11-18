# How much of each echo's 1-s distance wobble is shared (phone sway: same shift for all echoes) vs its own jitter?
# Shared part estimated WITHOUT the echo itself (leave-one-out median of the other tracks' shifts) -> no self-fitting.
import json, numpy as np, collections, glob, os
def analyse(path):
    d=json.load(open(path)); fr=d['frames']
    rows=collections.defaultdict(list)   # tid -> [(i, r)]
    for i,x in enumerate(fr):
        for e in x['e']:
            if e[9] and e[10]: rows[e[9]].append((i, e[0]-(e[12]/100 if len(e)>12 and e[12] is not None else 0)))
    # per reading, the shift of each track vs the previous reading
    shift=collections.defaultdict(dict)
    for tid,v in rows.items():
        for (i0,r0),(i1,r1) in zip(v,v[1:]):
            if i1==i0+1 and abs(r1-r0)<0.06: shift[i1][tid]=r1-r0
    raw_sd=[]; cor_sd=[]
    for tid,v in rows.items():
        for j in range(0,len(v)-15,15):
            seg=v[j:j+15]
            if seg[-1][0]-seg[0][0]!=14: continue
            r=np.array([s[1] for s in seg]); corr=[0.0]
            for (i,_) in seg[1:]:
                others=[s for k,s in shift[i].items() if k!=tid]
                corr.append(corr[-1]+(np.median(others) if len(others)>=1 else 0.0))
            raw_sd.append(r.std()); cor_sd.append((r-np.array(corr)).std())
    return np.array(raw_sd), np.array(cor_sd), d['settings'].get('ping')
for f in ['143533-870','142308-495','141954-224','140408-771','140553-471','125027-701','121421-809']:
    p=f'logs/sweep-20261118-{f}-sonar_log.json'
    if not os.path.exists(p): continue
    a,b,ping=analyse(p)
    if len(a)<5: continue
    print(f'{f} {ping:12s}: 1-s wobble median {100*np.median(a):.2f} cm -> after removing the shared sway {100*np.median(b):.2f} cm  (n {len(a)} track-seconds)')
