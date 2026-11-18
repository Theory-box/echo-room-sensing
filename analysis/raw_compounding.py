import numpy as np, math
from scipy.io import wavfile
SR,C,P=48000,343.0,3200
sr,x=wavfile.read('logs/sweep-20261118-115259-105-raw_audio.wav'); x=x.astype(np.float64)
n=1501; t=np.arange(n)/SR; T=n/SR
ph=2*np.pi*(16000*t+6000*t*t/(2*T)); w=0.5-0.5*np.cos(2*np.pi*np.arange(n)/(n-1)); full=w*np.exp(1j*ph)
def mf(sig,tp):
    N=1<<int(np.ceil(np.log2(len(sig)+len(tp)))); return np.fft.ifft(np.fft.fft(sig,N)*np.conj(np.fft.fft(tp,N)))[:len(sig)]
def subtpl(k,K):   # k-th of K time pieces of the sweep (= pitch bands), each Hann tapered
    a,b=int(k*n/K),int((k+1)*n/K); m=b-a; s=np.zeros(n,complex); s[a:b]=np.exp(1j*ph[a:b])*(0.5-0.5*np.cos(2*np.pi*np.arange(m)/(m-1))); return s
e_full=np.abs(mf(x[:,0],full))
k0=int(np.argmax(e_full[:P])); clicks=[]; k=k0
while k+400<len(e_full):
    lo,hi=max(0,k-20),k+21; kk=lo+int(np.argmax(e_full[lo:hi])); clicks.append(kk); k=kk+P
clicks=np.array(clicks); tt=clicks/SR; s2m=C/(2*SR); i0,i1=int(0.72/s2m),int(1.14/s2m)
def measure(env, navg=1, name=''):
    H=np.array([env[c+i0:c+i1]/env[c] for c in clicks])
    if navg>1: H=np.array([H[max(0,i-navg+1):i+1].mean(0) for i in range(len(H))])
    pk=[];cen=[]
    for h in H:
        m=int(np.argmax(h)); top=h[m]
        off=0
        if 0<m<len(h)-1:
            a,b,d=h[m-1],h[m],h[m+1]; den=a-2*b+d; off=0.5*(a-d)/den if den<0 else 0
        pk.append((i0+m+off)*s2m)
        thr=top/2; j=m
        while j>0 and h[j-1]>thr: j-=1
        q=m
        while q<len(h)-1 and h[q+1]>thr: q+=1
        ww=h[j:q+1]**2; cen.append(((np.arange(j,q+1)+i0)*ww).sum()/ww.sum()*s2m)
    out=[]
    for nm,y in (('loudest',np.array(pk)),('centre',np.array(cen))):
        F=np.fft.rfftfreq(len(tt),1/15); wv=2*np.pi*0.70
        M=np.column_stack([np.sin(wv*tt),np.cos(wv*tt),np.ones_like(tt)]); c=np.linalg.lstsq(M,y,rcond=None)[0]; r=y-M@c
        out.append(f'{nm}: swing {100*math.hypot(c[0],c[1]):.2f} cm, leftover sd {100*r.std():.2f} cm, step {100*np.median(np.abs(np.diff(y))):.2f} cm')
    print(f'{name:40s} '+' | '.join(out))
measure(e_full,1,'full band, 1 click (baseline)')
measure(e_full,3,'full band, 3 clicks (as app)')
for K in (2,3,4):
    env=np.zeros(len(x))
    for k in range(K): env+=np.abs(mf(x[:,0],subtpl(k,K)))**2
    env=np.sqrt(env)
    measure(env,1,f'{K} pitch bands compounded, 1 click')
    measure(env,3,f'{K} pitch bands compounded, 3 clicks')
