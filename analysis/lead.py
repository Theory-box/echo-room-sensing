# Is the pilots sessions' low wobble real? Compare 1-s wobble per mode, matched by echo level and distance, and by
# how much the phone was turning.
import json, numpy as np, collections, glob, os
def segs(path):
    d=json.load(open(path)); fr=d['frames']; rows=collections.defaultdict(list)
    for i,x in enumerate(fr):
        for e in x['e']:
            if e[9] and e[10]: rows[e[9]].append((i,e[0],e[1],x['gy']))
    out=[]
    for v in rows.values():
        for j in range(0,len(v)-15,15):
            s=v[j:j+15]
            if s[-1][0]-s[0][0]!=14: continue
            r=np.array([q[1] for q in s]); out.append((r.std()*100, np.mean([q[2] for q in s]), r.mean(), np.mean([q[3] for q in s])))
    return np.array(out), d['settings']['ping']
S=collections.defaultdict(list)
for p in sorted(glob.glob('logs/sweep-20261118-1[2-4]*-sonar_log.json')):
    try: a,ping=segs(p)
    except Exception: continue
    if len(a): S[ping].append(a)
for ping,L in S.items():
    A=np.vstack(L)
    print(f'{ping:12s}: track-seconds {len(A):4d} | wobble median {np.median(A[:,0]):.2f} cm | level median {np.median(A[:,1]):.1f} dB | distance median {np.median(A[:,2]):.2f} m | turning median {np.median(A[:,3]):.2f} rad/s')
    for lo,hi in ((-50,-42),(-42,-30)):
        m=(A[:,1]>=lo)&(A[:,1]<hi)
        for g0,g1 in ((0,0.1),(0.1,1)):
            mm=m&(A[:,3]>=g0)&(A[:,3]<g1)
            if mm.sum()>=5: print(f'     level {lo}..{hi} dB, turning {g0}-{g1}: wobble {np.median(A[mm,0]):.2f} cm (n {mm.sum()})')
