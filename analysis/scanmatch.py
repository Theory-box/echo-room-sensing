# Phone movement by lining up whole echo profiles (1-D scan matching against a keyframe)
import json, numpy as np, importlib.util
from scipy.signal import butter, filtfilt
spec=importlib.util.spec_from_file_location('em','echomotion.py'); em=importlib.util.module_from_spec(spec); spec.loader.exec_module(em)
def scan_motion(fr, r0=0.3, r1=3.0, maxs=10, cmin=0.5, sub=4):
    T0=fr[0]['t']; key=None; base=0.0; out=[]
    for x in fr:
        p=np.array(x['p'],float); a=10**(p/20); a[p<=-99]=0
        i0,i1=int(r0/0.03),min(len(a)-maxs-1,int(r1/0.03))
        if key is None: key=a; out.append(((x['t']-T0)/1000,base)); last=0.0; continue
        # upsample both by `sub` (linear), normalised correlation over shifts +-maxs bins
        xs=np.arange(len(a)); fine=np.arange(0,len(a)-1,1/sub)
        A=np.interp(fine,xs,a); K=np.interp(fine,xs,key)
        j0,j1=i0*sub,i1*sub; best=(-2,0)
        for s in range(-maxs*sub,maxs*sub+1):
            u=A[j0:j1]; v=K[j0+s:j1+s] if s>=0 else K[j0+s:j1+s]
            if j0+s<0 or j1+s>len(K): continue
            c=np.dot(u-u.mean(),v-v.mean())/(np.linalg.norm(u-u.mean())*np.linalg.norm(v-v.mean())+1e-12)
            if c>best[0]: best=(c,s)
        c,s=best; shift=s/sub*0.03     # current echo at r matches key at r+shift -> phone moved closer by shift
        if c<cmin or abs(s)>=maxs*sub-1:
            base+=last; key=a; shift=0.0     # re-anchor on the current profile
        last=shift; out.append(((x['t']-T0)/1000,base+shift))
    o=np.array(out); return o[:,0],o[:,1]
if __name__=='__main__':
    d,fr=em.load('143500-443'); t,E=scan_motion(fr)
    a=(t>1)&(t<6); b=t>t[-1]-1.5
    print(f'calibration: scan-matched movement {100*(E[b].mean()-E[a].mean()):+.1f} cm (wall echo +25.0); at rest sd {100*E[a].std():.2f} cm')
    d,fr=em.load('151756-769'); t,E=scan_motion(fr)
    def m(a0,a1): mm=(t>=a0)&(t<a1); return 100*E[mm].mean()
    print(f'hum-band table run: rest {m(1,4):+.1f}, after 43 cm move {m(16,20):+.1f}, after moving back {m(25,28):+.1f} cm (wall echo: 0 / +43 / +7)')
    for s in ('142308-495','143533-870'):
        d,fr=em.load(s); t,E=scan_motion(fr)
        fs=1/np.median(np.diff(t)); g=np.arange(t[0],t[-1],1/fs)
        Eg=em.bp(np.interp(g,t,E),fs); Ag=em.bp(em.accel_disp(fr,g),fs); c=em.lagcorr(Eg,Ag,int(0.5*fs))
        print(f'{s}: scan-matched vs sensor corr {c[0]:+.2f} at {c[1]/fs*1000:+.0f} ms, scale {c[2]:+.2f}')
