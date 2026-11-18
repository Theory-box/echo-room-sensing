import sys, collections
import numpy as np
sys.argv=['x']; exec(open('rough.py',encoding='utf-8').read().split("if __name__")[0])
def ad(a,b): return (a-b+540)%360-180
def tally2(sel,zthr,mmin):
    c=collections.Counter()
    for v in sel:
        if v is None or v['mot']<mmin: c['unsure']+=1
        elif v['z']>zthr: c['ahead']+=1
        elif v['z']<-zthr: c['behind']+=1
        else: c['unsure']+=1
    return c
P=run('logs/sweep-20261118-123740-977-sonar_log.json',120); S=run('logs/sweep-20261118-123840-246-sonar_log.json',120)
d,fr,out=P; T0=fr[0]['t']
pw=[v for i,e,v in out if abs(e[0]-0.9)<0.15 and 10000<=fr[i]['t']-T0<30000]
print('push test wall: forward motion in window cm, pct 25/50/75:', np.percentile([v['mot'] for v in pw if v],[25,50,75]).round(2))
d,fr,out=S; W=[w for x in fr for w in x.get('rcd',[]) if w[5]==1]
sa=[v for i,e,v in out if e[10] and any(abs(ad(fr[i]['h'],w[2]))<20 and abs(e[0]-w[1])<0.05 for w in W)]
so=[v for i,e,v in out if e[10] and not any(abs(ad(fr[i]['h'],w[2]))<20 and abs(e[0]-w[1])<0.05 for w in W)]
for mmin in (0,0.3,0.5,0.8):
  for z in (2.5,4):
    a=tally2(pw,z,mmin); b=tally2(sa,z,mmin); o=tally2(so,z,mmin)
    print(f'min motion {mmin} cm, z>{z}: PUSH wall ahead {a["ahead"]}/{a["behind"]} (ahead/behind) | SWEEP walls ahead {b["ahead"]}/{b["behind"]} | sweep other {o["ahead"]}/{o["behind"]}')
