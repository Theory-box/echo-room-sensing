import json,math,sys
import numpy as np
f=sys.argv[1]
d=json.load(open(f)); fr=d['frames']; mask=float(d['settings']['mask'])
P=[np.array(x['p'],float) for x in fr]
nb=min(len(p) for p in P); P=np.array([p[:nb] for p in P])
r=(np.arange(nb)+0.5)*0.03; b0=int(math.ceil(max(mask,0.3)/0.03))
lev=np.where(P>-99, P+20*np.log10(np.maximum(r,0.3)), -120)
def peaks(L,thr):
    out=[]
    for b in range(max(b0,1),nb-1):
        if L[b]>=thr[b] and L[b]>=L[b-1] and L[b]>L[b+1]: out.append(b)
    # keep strongest 5, >=4 bins apart, within 24 dB of best
    out.sort(key=lambda b:-L[b]); kept=[]
    for b in out:
        if kept and L[b]<L[kept[0]]-24: break
        if len(kept)>=5: break
        if any(abs(b-k)<4 for k in kept): continue
        kept.append(b)
    return kept
def detect(method,off):
    D=[]
    for L in lev:
        v=L[b0:]; v=v[v>-100]
        if method=='median':
            typ=np.median(v) if len(v)>8 else -60; thr=np.full(nb,typ+off)
        else:  # OS-CFAR: 10 cells each side, 2 guard, 75th percentile of the reference cells (in dB) + off
            thr=np.full(nb,999.0)
            for b in range(b0,nb):
                ref=np.r_[L[max(b0,b-12):max(b0,b-2)], L[b+3:b+13]]; ref=ref[ref>-100]
                if len(ref)>=6: thr[b]=np.percentile(ref,75)+off
        D.append(peaks(L,thr))
    return D
def score(D):
    real=fake=0
    for i,ds in enumerate(D):
        for b in ds:
            hits=sum(1 for j in range(max(0,i-4),min(len(D),i+5)) if j!=i and any(abs(b-c)<=2 for c in D[j]))
            if hits>=3: real+=1
            else: fake+=1
    return real,fake
n=len(D:=None) if False else len(fr)
print(f, 'readings',len(fr))
for m,offs in (('median',(5,7,9,11)),('oscfar',(3,5,7,9))):
    for o in offs:
        rl,fk=score(detect(m,o)); print(f'  {m:7s} +{o:2d} dB: persistent {rl/len(fr):.2f}/reading, non-persistent {fk/len(fr):.2f}/reading, share non-persistent {100*fk/max(1,rl+fk):.0f}%')
