# learn the speaker->phone response at spot A from the probe recording, build tr_test.wav
import sys, numpy as np
from scipy.io import wavfile
from scipy.signal import find_peaks
from common import *
rec=sys.argv[1]; ch=int(sys.argv[2]) if len(sys.argv)>2 else 0
sr,x=wavfile.read(rec); x=band(x[:,ch].astype(float))
c=chirp(); mf=np.abs(np.fft.irfft(np.fft.rfft(x)*np.conj(np.fft.rfft(c,len(x))),len(x)))
pk,_=find_peaks(mf,distance=int(0.8*SR),height=mf.max()*0.3)
print('chirps found',len(pk),'at s',np.round(pk/SR,2))
pre=int(0.01*SR); L=int(0.45*SR); N=1<<16
C=np.fft.rfft(c,N); f=np.fft.rfftfreq(N,1/SR); m=(f>=F0)&(f<=F1); w=np.zeros(len(f)); w[m]=np.hanning(m.sum())
hs=[]
for p in pk:
    seg=x[p-pre:p-pre+N] if p-pre+N<=len(x) else np.pad(x[p-pre:],(0,N-len(x[p-pre:])))
    H=np.fft.rfft(seg)/np.where(m,C,1)*w
    hs.append(np.fft.irfft(H,N)[:L])
hs=np.array(hs)
# coherence between repeats (how steady the room/phone was)
cc=[np.corrcoef(hs[0],h)[0,1] for h in hs[1:]]; print('repeat similarity',np.round(cc,3))
h=hs.mean(0); np.save('h_A.npy',h)
e=h**2; ce=np.cumsum(e)/e.sum(); print('energy 90%% within %.0f ms of the direct sound'%(np.argmax(ce>0.9)/SR*1000))
tr=band(h[::-1]); tr/=np.abs(tr).max(); tr*=0.6
E=(tr**2).sum(); ch_=chirp(); ch_*=np.sqrt(E/(ch_**2).sum())
print('TR length %.2f s, peak %.2f; equal-energy chirp peak %.2f'%(len(tr)/SR,np.abs(tr).max(),np.abs(ch_).max()))
gap=int(1.5*SR); seq=[np.zeros(SR)]
for k in range(3): seq+= [tr,np.zeros(gap),ch_,np.zeros(gap)]
out=np.concatenate(seq); save('tr_test.wav',out); np.save('tr_sig.npy',tr); np.save('ch_sig.npy',ch_)
print('tr_test.wav %.1f s: TR, chirp, TR, chirp, TR, chirp'%(len(out)/SR))
