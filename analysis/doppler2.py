import numpy as np, importlib.util, sys
spec=importlib.util.spec_from_file_location('dp','doppler.py'); dp=importlib.util.module_from_spec(spec); spec.loader.exec_module(dp)
SR,C,P=48000,343.0,2048
def remove_static(x, start, tau=3.0):
    """synchronous running average of the repeating signal (aligned to absolute sample number mod P), subtracted"""
    ph=(start)%P; n0=(P-ph)%P            # first sample index at a period boundary
    y=x.copy(); S=None; al=1/(tau*SR/P)
    for p in range(n0, len(x)-P+1, P):
        seg=x[p:p+P]
        if S is None: S=seg.copy(); y[p:p+P]=0; continue
        y[p:p+P]=seg-S; S+=al*(seg-S)
    y[:n0]=0
    return y
if __name__=='__main__':
    base='logs/sweep-20261118-143500-443'
    d,fr,x,start=dp.load(base)
    r=remove_static(x,start)
    vgrid=np.arange(-0.40,0.401,0.02)
    t,v,e=dp.run(r,start,vgrid,stat_tau=1e9)
    disp=-np.cumsum(v)*dp.HOP/SR
    a=(t>1)&(t<5); b=t>t[-1]-1.5
    print(f'static removed first: Doppler-picked speed integrated {100*(disp[b].mean()-disp[a].mean()):+.1f} cm (echo says -25.0)')
    print('speed picked (cm/s) per second:', [int(round(100*np.median(v[(t>=s)&(t<s+1)]))) for s in range(int(t[-1]))])
    np.save('doppler_cal2.npy',np.vstack([t,v,e]))
