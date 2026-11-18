# Second-mic diversity: wall echo jitter with the bottom mic alone vs bottom + back mic combined (back mic shifted by
# its measured delay for this echo and scaled to equal strength), on the raw push recording (wall straight ahead).
import numpy as np, math
from scipy.io import wavfile
SR,C,P=48000,343.0,3200
sr,x=wavfile.read('logs/sweep-20261118-115259-105-raw_audio.wav'); x=x.astype(np.float64)
n=1501; t=np.arange(n)/SR; T=n/SR
ph=2*np.pi*(16000*t+6000*t*t/(2*T))
def mf(sig,tp):
    N=1<<int(np.ceil(np.log2(len(sig)+len(tp)))); return np.fft.ifft(np.fft.fft(sig,N)*np.conj(np.fft.fft(tp,N)))[:len(sig)]
def sub(k,K):
    a,b=int(k*n/K),int((k+1)*n/K); m=b-a; s=np.zeros(n,complex); s[a:b]=np.exp(1j*ph[a:b])*(0.5-0.5*np.cos(2*np.pi*np.arange(m)/(m-1))); return s
full=(0.5-0.5*np.cos(2*np.pi*np.arange(n)/(n-1)))*np.exp(1j*ph)
s2m=C/(2*SR); i0,i1=int(0.72/s2m),int(1.14/s2m)
def env(ch,K):
    if K==1: return np.abs(mf(x[:,ch],full))
    return np.sqrt(sum(np.abs(mf(x[:,ch],sub(k,K)))**2 for k in range(K)))
e1=env(0,1); k=int(np.argmax(e1[:P])); clicks=[]
while k+400<len(e1):
    a0=max(0,k-20); kk=a0+int(np.argmax(e1[a0:k+21])); clicks.append(kk); k=kk+P
clicks=np.array(clicks); tt=clicks/SR
def jitter(H,navg=3):
    H=np.array([H[max(0,i-navg+1):i+1].mean(0) for i in range(len(H))])
    pk=(np.argmax(H,1)+i0)*s2m
    wv=2*np.pi*0.70; M=np.column_stack([np.sin(wv*tt),np.cos(wv*tt),np.ones_like(tt)]); c=np.linalg.lstsq(M,pk,rcond=None)[0]
    return 100*(pk-M@c).std()
for K in (1,2):
    a=env(0,K); b=env(1,K)
    A=np.array([a[c+i0:c+i1]/a[c] for c in clicks]); B=np.array([b[c+i0-30:c+i1+30] for c in clicks])
    # back mic: find the delay that best matches the bottom mic's wall hump on average, scale to equal strength
    best=None
    for L in range(-30,31):
        Bs=B[:,30+L:30+L+(i1-i0)]; cc=np.corrcoef(A.mean(0),Bs.mean(0))[0,1]
        if best is None or cc>best[0]: best=(cc,L)
    Bs=B[:,30+best[1]:30+best[1]+(i1-i0)]; Bs=Bs/Bs.mean()*A.mean()
    corr_pk=np.corrcoef(np.argmax(A,1),np.argmax(Bs,1))[0,1]
    print(f'{K} band(s): back mic delay {best[1]} samples (match {best[0]:.2f}); bottom-vs-back peak positions correlate {corr_pk:+.2f} | jitter: bottom {jitter(A):.2f} cm, back {jitter(Bs):.2f} cm, combined {jitter(np.sqrt((A**2+Bs**2)/2)):.2f} cm')
