import json, numpy as np, glob, sys, importlib.util
spec=importlib.util.spec_from_file_location('rf','roomfit.py'); rf=importlib.util.module_from_spec(spec); sys.argv=['x','none']; spec.loader.exec_module(rf)
sess=['120930-256','121133-233','121421-809','123840-246','125027-701','125121-158','125252-920','140408-771','140553-471','141954-224','154811-707']
rows=[]
for s in sess:
    d=json.load(open(f'logs/sweep-20261118-{s}-sonar_log.json')); fr=d['frames']
    hs=[x['h'] for x in fr]
    if max(hs)-min(hs)<300: continue
    h=[];r=[];ya=[]
    for x in fr:
        for e in x['e']:
            if e[10] and e[0]>0.35: h.append(x['h']); r.append(e[0]-(e[12]/100 if len(e)>12 and e[12] is not None else 0)); ya.append(x['yaw']+180)
    h,r,ya=np.array(h),np.array(r),np.array(ya)
    p,score,votes=rf.fit_vote(h,r)
    clutter=int(len(r)*0.08/4)
    # same fit in the absolute (sensor) heading frame, to compare box orientation across sessions
    pa,_,va=rf.fit_vote(((ya+180)%360)-180,r)
    rows.append((s,d['settings']['ping'],p,votes,clutter,pa))
    print(f"{s} {d['settings']['ping']:12s}: walls (sorted) {np.round(np.sort(p[1:]),2)} votes {sorted(votes,reverse=True)} (clutter ~{clutter}) | absolute-frame box rot {pa[0]:+.0f}, walls by direction {np.round(pa[1:],2)}")
