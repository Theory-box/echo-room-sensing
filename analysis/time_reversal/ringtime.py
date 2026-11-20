# Ring time (RT60) from repeated chirps: deconvolve each, average energy, Schroeder backward integration per band
import sys, numpy as np
from scipy.io import wavfile
from scipy.signal import find_peaks
from common import *
rec=sys.argv[1]; ch=int(sys.argv[2]) if len(sys.argv)>2 else 0
sr,x=wavfile.read(rec); x=x[:,ch].astype(float)
xb=band(x,F0,F1); c=chirp()
mf=np.abs(np.fft.irfft(np.fft.rfft(xb)*np.conj(np.fft.rfft(c,len(xb))),len(xb)))
pk,_=find_peaks(mf,distance=int(0.8*SR),height=mf.max()*0.3)
L=int(0.9*SR); N=1<<16; pre=int(0.005*SR)
C=np.fft.rfft(c,N); f=np.fft.rfftfreq(N,1/SR)
def h_band(seg,lo,hi):
    m=(f>=lo)&(f<=hi); w=np.zeros(len(f)); w[m]=np.hanning(m.sum())
    H=np.fft.rfft(seg,N)/np.where(m,C,1)*w; return np.fft.irfft(H,N)[:L]
bands=[(2000,3000),(3000,4500),(4500,7000)]
print(f'chirps used: {len(pk)}')

def rt_from(E):
    t=np.arange(L)/SR; w=int(0.01*SR)
    sm=np.convolve(E,np.ones(w)/w,'same'); noise=np.median(sm[int(0.7*SR):int(0.88*SR)])
    sdb=10*np.log10(sm+1e-30); ndb=10*np.log10(noise)
    i0=int(np.argmax(sm[:int(0.02*SR)]))
    after=np.nonzero(sdb[i0:]<ndb+5)[0]; ic=i0+(after[0] if len(after) else L-i0-1)
    Ec=np.maximum(E[i0:ic]-noise,0); sch=np.cumsum(Ec[::-1])[::-1]; sd=10*np.log10(sch/sch[0]+1e-30); tt=t[i0:ic]-t[i0]
    def fit(a,b):
        m=(sd<=a)&(sd>=b)
        return -60/np.polyfit(tt[m],sd[m],1)[0] if m.sum()>20 and sd.min()<b+1 else None
    return fit(-5,-25), fit(-5,-15), fit(0,-10), (sdb[i0]-ndb), tt[-1]
fmt=lambda v: f'{v:.2f}' if v else ' n/a'
for lo,hi in bands:
    hs=[]
    for p in pk:
        seg=x[p-pre:p-pre+N]
        if len(seg)==N: hs.append(h_band(seg,lo,hi))
    hs=np.array(hs)
    T20,T10,EDT,dr,tc=rt_from((hs**2).mean(0))
    parts=[rt_from((hs[g::3]**2).mean(0)) for g in range(3)]
    print(f'{lo/1000:.1f}-{hi/1000:.1f} kHz: RT60 T20 {fmt(T20)} s | T10 {fmt(T10)} s | early {fmt(EDT)} s | decay range {dr:.0f} dB over {tc*1000:.0f} ms | T10 by thirds',[fmt(q[1]) for q in parts])
