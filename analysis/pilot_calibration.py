import numpy as np, json
from scipy.io import wavfile
SR,C,P,K0,NT,HOP=48000,343.0,2048,683,256,256
base='logs/sweep-20261118-143500-443'
d=json.load(open(base+'-sonar_log.json')); fr=d['frames']
sr,x=wavfile.read(base+'-raw_audio.wav'); x=x.astype(np.float64)[:,0]
end,nraw=int(d['raw'].split('|')[1]),int(d['raw'].split('|')[2]); start=end-nraw
kk=K0+8+16*np.arange(16); fc=kk.mean()*SR/P
starts=np.arange(0,len(x)-P,HOP)
B=np.array([np.fft.fft(x[s:s+P])[kk]*np.exp(-2j*np.pi*kk*((start+s)%P)/P) for s in starts])
w=np.hanning(18)[1:-1]
def run(mode, tau=3.0, guard=6, warm=40):
    S=np.zeros(16,complex); cum=0; last=None; out=[]
    for n,b in enumerate(B):
        al=max(HOP/(tau*SR),1/(n+1)); S+=al*(b-S)
        if n<=warm: out.append(cum); continue
        Dp=np.fft.ifft((b-S)*w,64); Sp=np.fft.ifft(S*w,64); d0=int(np.argmax(np.abs(Sp)))
        cand=[m for m in range(64) if min((m-d0)%64,(d0-m)%64)>guard]
        if last is not None:
            if mode=='median':
                st=np.angle(Dp[cand]*np.conj(last[cand])); step=np.median(st)
            elif mode=='power':   # angle of the power-weighted sum of phase steps
                step=np.angle(np.sum(Dp[cand]*np.conj(last[cand])))
            elif mode=='power_all':
                step=np.angle(np.sum(Dp*np.conj(last)))
            elif mode=='direct':  # no profile: per pilot, power-weighted step of the changing part
                z=b-S; step=np.angle(np.sum(z*np.conj(lastz)))
            cum+=-step*C/(2*np.pi*fc)/2
        last=Dp; lastz=b-S
        out.append(cum)
    return np.array(out)
t=(starts+P/2)/SR
yt=np.array([f['t'] for f in fr]); 
for mode in ('median','power','power_all','direct'):
    for tau in (3.0,10.0):
        c=run(mode,tau); a=c[(t>1)&(t<5)].mean(); b=c[(t>t[-1]-2)].mean()
        print(f'{mode:10s} tau {tau:4.0f}s: start {1000*a:6.1f} mm -> end {1000*b:7.1f} mm  = moved {100*(b-a):+6.1f} cm  (echo says -25.0 cm, paper 27.9)')
