import json,numpy as np,sys
def bounce_check(F,rot,D,ax):
    # accumulate raw profiles while facing either wall of this axis; look for an echo at D[a]+D[b]
    n0=(rot+90*ax)%360; acc=None; n=0
    for f in F:
        if not f.get('p'): continue
        dh=min(abs(((f['h']-n0+180)%360)-180),abs(((f['h']-n0-180+180)%360)-180))
        if dh<25:
            p=10**(np.array(f['p'][:166]+[-99]*(166-len(f['p'][:166])))/10); acc=p if acc is None else acc+p; n+=1
    if n<30: return None,n,None
    mp=10*np.log10(acc/n); L=D[ax]+D[ax+2]; i=int(L/0.03)
    if i+20>=len(mp): return 0,n,None
    w=mp[max(0,i-3):i+4]; pk=w.max(); ref=np.median(mp[max(0,i-20):i+21])
    j=max(0,i-3)+int(np.argmax(w))
    return (1 if pk-ref>=3 else 0), n, (round(j*0.03+0.015,2), round(pk-ref,1))
def score(S,ts):
    FF=json.load(open(S+'/sonar_log.json'))['frames']
    F=[f for f in FF if ts is None or f.get('ts')==ts]
    fits=[f['rb'] for f in F if 'rb' in f]; lk=[f for f in F if 'slk' in f]
    if not lk: return 'no lock'
    rb=fits[-1]; rot=rb[0]; D=rb[1:5]; votes=rb[5:9]; clutter=rb[9]
    sup=[v>=max(15,3*clutter) for v in votes]
    last=[r[1:5] for r in fits[-6:]]
    stab=[max(abs(r[w]-D[w]) for r in last)<=0.05 for w in range(4)]
    b=[bounce_check(F,rot,D,a) for a in (0,1)]
    bs=[x[0] for x in b]; bv=[0.5 if x is None else x for x in bs]
    pct=round(100*(0.4*np.mean(sup)+0.3*np.mean(stab)+0.3*np.mean(bv)))
    return dict(pct=pct,walls=D,support=sup,steady=stab,bounce=[(x[0],x[1],x[2]) for x in b])
for nm,S,ts in (('Test 1 (bad back wall)','sweep-20261119-145617-963',1),('Test 2 (matched room)','sweep-20261119-152557-632',1),('box A','sweep-20261119-153555-527',None),('box B','sweep-20261119-153714-947',None),('roll (ringing)','sweep-20261119-154604-377',None)):
    print(nm, score(S,ts))
