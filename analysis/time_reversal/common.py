import numpy as np
from scipy.io import wavfile
SR=48000; F0,F1,T=2000,7000,0.06; GAP=1.0; NCH=6; AMP=0.3
def chirp():
    n=int(T*SR); t=np.arange(n)/SR
    c=np.sin(2*np.pi*(F0*t+(F1-F0)/(2*T)*t*t))
    f=int(0.005*SR); w=np.ones(n); w[:f]=np.linspace(0,1,f); w[-f:]=np.linspace(1,0,f)
    return c*w
def band(x,lo=F0,hi=F1):
    X=np.fft.rfft(x); f=np.fft.rfftfreq(len(x),1/SR); X[(f<lo)|(f>hi)]=0; return np.fft.irfft(X,len(x))
def save(path,x):
    x=np.clip(x,-1,1); st=np.stack([x,x],1); wavfile.write(path,SR,(st*32767).astype(np.int16))
