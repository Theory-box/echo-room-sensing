# Range-Doppler coupling test: per confirmed track, residual distance (raw minus a smooth fit over +-0.4 s) vs the
# echo's own radial speed (slope of that smooth fit). A sweep-like signal predicts residual = -v * fc*T/B.
import json, numpy as np, collections, glob
def run(path):
    d=json.load(open(path)); fr=d['frames']; ping=d['settings']['ping']; rate=int(d['settings'].get('rate',15))
    rows=collections.defaultdict(list)
    for x in fr:
        for e in x['e']:
            if e[9] and e[10]: rows[e[9]].append((x['tc'] if 'tc' in x else x['t'], e[0]-(e[12]/100 if len(e)>12 and e[12] is not None else 0)))
    R=[];V=[]
    for v in rows.values():
        if len(v)<9: continue
        t=np.array([q[0] for q in v])/1000; r=np.array([q[1] for q in v])
        for i in range(4,len(v)-4):
            m=np.abs(t-t[i])<=0.4
            if m.sum()<6: continue
            c=np.polyfit(t[m]-t[i],r[m],2); R.append(r[i]-c[2]); V.append(-c[1])   # speed: + = getting closer
    return np.array(R),np.array(V),ping,rate
res=collections.defaultdict(lambda:[[],[]])
for p in sorted(glob.glob('logs/sweep-20261118-1[2-4]*-sonar_log.json')):
    try: R,V,ping,rate=run(p)
    except Exception as ex: continue
    if len(R): res[(ping,rate if ping=='quietlong' else 0)][0].append(R); res[(ping,rate if ping=='quietlong' else 0)][1].append(V)
for k,(Rs,Vs) in res.items():
    R=np.concatenate(Rs); V=np.concatenate(Vs); m=np.abs(V)<0.5
    slope=np.polyfit(V[m],R[m],1)[0]; c=np.corrcoef(V[m],R[m])[0,1]
    pred={'quiettones':-19000*0.0427/6000,'quietpilots':None,('quietlong'):-19000*(1501/48000)/6000}.get(k[0])
    print(f'{k[0]:12s}: n {m.sum():5d} | residual vs own speed: slope {slope*100:+.2f} cm per m/s... i.e. {slope*10:+.2f} cm per 10 cm/s, corr {c:+.2f} | sweep theory {"" if pred is None else f"{pred*10:+.2f} cm per 10 cm/s"} | residual sd {100*R[m].std():.2f} cm, speed sd {100*V[m].std():.1f} cm/s')
