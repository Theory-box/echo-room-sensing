# measure arrivals of TR and equal-energy chirp in a recording of tr_test.wav playback
import sys, numpy as np
from scipy.io import wavfile
from common import *
rec=sys.argv[1]; ch=int(sys.argv[2]) if len(sys.argv)>2 else 0
sr,x=wavfile.read(rec); x=band(x[:,ch].astype(float))
tr=np.load('tr_sig.npy'); c=np.load('ch_sig.npy')
# locate playback start: matched filter with the chirp events (spaced known)
mf=np.abs(np.fft.irfft(np.fft.rfft(x)*np.conj(np.fft.rfft(c,len(x))),len(x)))
gap=int(1.5*SR); P=len(tr)+gap+len(c)+gap
# chirp k starts at t0 + SR + k*P + len(tr)+gap ; find t0 maximizing sum of mf at the 3 chirp spots
best=None
for t0 in range(0,len(x)-3*P-SR,48):
    s=sum(mf[t0+SR+k*P+len(tr)+gap] for k in range(3))
    if best is None or s>best[0]: best=(s,t0)
t0=best[1]
# refine
seg=lambda a,b: x[a:b]
res=[]
for k in range(3):
    a=t0+SR+k*P; tw=x[a-int(0.05*SR):a+len(tr)+int(0.6*SR)]
    b=a+len(tr)+gap; cw=x[b-int(0.05*SR):b+len(c)+int(0.6*SR)]
    for nm,w in (('TR',tw),('chirp',cw)):
        pk=np.abs(w).max(); rms=np.sqrt((w**2).mean()); i=np.argmax(np.abs(w))
        e=w**2; near=e[max(0,i-48):i+48].sum()/e.sum()
        res.append((nm,pk,pk/rms,near))
for nm in ('TR','chirp'):
    r=[q for q in res if q[0]==nm]
    print(f'{nm:5s} peak {20*np.log10(np.mean([q[1] for q in r])):6.1f} dB   peak/rms {np.mean([q[2] for q in r]):5.1f}   energy within 1 ms of peak {100*np.mean([q[3] for q in r]):4.1f}%')
