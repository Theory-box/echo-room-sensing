# Direct test: a wall moving at a steady known speed; distance read by the tone pipeline (received/played per tone,
# Hann, inverse FFT, peak) with Schroeder phases (Quiet tones) vs peak-tamed random-like phases (pilots design).
import numpy as np, math
SR,C,P,K0,NT=48000,343.0,2048,683,256
kk=K0+np.arange(NT); n=np.arange(P)
a=np.ones(NT)
for k in range(NT):
    e=min(k,NT-1-k); a[k]=1 if e>=16 else 0.2+0.8*(0.5-0.5*math.cos(math.pi*e/16))
def tamed(ph,amp):
    def synth(ph):
        S=np.zeros(P,complex); S[kk]=amp*P/2*np.exp(1j*ph); S[P-kk]=np.conj(S[kk]); return np.fft.ifft(S).real
    x=synth(ph)
    for _ in range(60):
        r=np.sqrt((x**2).mean()); y=np.clip(x,-1.6*r,1.6*r); ph=np.angle(np.fft.fft(y)[kk]); x=synth(ph)
    return ph
designs={'Schroeder (Quiet tones)':-np.pi*np.arange(NT)**2/NT}
amp_p=a.copy(); amp_p[[k for k in range(NT) if k%16==8]]*=2
ph_p=-np.pi*np.arange(NT)**2/NT
for j,k in enumerate([k for k in range(NT) if k%16==8]): ph_p[k]=-np.pi*j*j/16+0.3
designs['peak-tamed (pilots)']=tamed(ph_p,amp_p)
w=np.hanning(NT+2)[1:-1]
for name,ph in designs.items():
    amp=a if name.startswith('Schroeder') else amp_p
    res=[]
    for v in (-0.2,-0.1,0.0,0.1,0.2):
        T=0.4; t=np.arange(int(T*SR))/SR; d=1.0-v*t        # v>0: getting closer
        x=np.zeros_like(t)
        for k,A,p in zip(kk,amp,ph): x+=A*np.cos(2*np.pi*k*SR/P*(t-2*d/C)+p)
        s0=int(0.15*SR); seg=x[s0:s0+P]
        Y=np.fft.fft(seg)[kk]*np.exp(-2j*np.pi*kk*s0/P)
        X=amp*P/2*np.exp(1j*ph)
        prof=np.abs(np.fft.ifft(Y/X*w,8192)); i=int(np.argmax(prof))
        dist=i*(P/8192)/SR*C/2; tc=(s0+P/2)/SR
        res.append((v,100*(dist-(1.0-v*tc))))
    print(f'{name:26s}: distance error at speed (cm/s -> cm): '+', '.join(f'{100*v:+.0f}:{e:+.2f}' for v,e in res))
