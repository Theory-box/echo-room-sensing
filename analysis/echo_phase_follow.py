import numpy as np, json
from scipy.io import wavfile
SR,C,P,K0,NT,HOP,M=48000,343.0,2048,683,256,256,2048
base='logs/sweep-20261118-143500-443'
d=json.load(open(base+'-sonar_log.json'))
sr,x=wavfile.read(base+'-raw_audio.wav'); x=x.astype(np.float64)[:,0]
end,nraw=int(d['raw'].split('|')[1]),int(d['raw'].split('|')[2]); start=end-nraw
kk=K0+np.arange(NT); w=np.hanning(NT+2)[1:-1]
starts=np.arange(0,len(x)-P,HOP); t=(starts+P/2)/SR
# per hop: full complex profile (all 256 tones), 1 sample per point (M=2048 over the 2048-sample period)
prof=np.array([np.fft.ifft(np.fft.fft(x[s:s+P])[kk]*np.exp(-2j*np.pi*kk*((start+s)%P)/P)*w, M) for s in starts])
mag=np.abs(prof); d0=int(np.argmax(mag.mean(0)))
s2m=C/(2*SR)
def idx(r): return (d0+int(round(r/s2m)))%M
# track the wall: start at the strongest peak 0.8-1.2 m in the first second, follow the peak within +-8 samples
i=idx(0.96)+int(np.argmax(mag[:50, idx(0.96):idx(1.03)].mean(0)))
fcen=(K0+NT/2)*SR/P
pos=[]; ph=[]
for n in range(len(starts)):
    lo=i-8; seg=mag[n, lo:lo+17]; i=lo+int(np.argmax(seg)); pos.append(i); ph.append(np.angle(prof[n,i]))
pos=np.array(pos); ph=np.array(ph)
coarse=(pos-d0)*s2m                             # envelope distance (m), 3.6 mm steps
# fine: phase change between hops, unwrapped around what the peak move predicts (each sample of delay = fc/SR turns)
fine=[coarse[0]]; 
for n in range(1,len(pos)):
    pred=(pos[n]-pos[n-1])*2*np.pi*fcen/SR      # phase change the peak shift alone implies (radians)
    dph=ph[n]-ph[n-1]-pred; dph-=2*np.pi*np.round(dph/(2*np.pi))
    # distance change = (peak shift + residual phase) ; phase grows with delay: dphase = -2pi f dtau -> sign below
    dtau=(pos[n]-pos[n-1])/SR - dph/(2*np.pi*fcen)
    fine.append(fine[-1]+dtau*C/2)
fine=np.array(fine)
a=(t>1)&(t<5); b=t>t[-1]-2
print(f'wall echo (envelope peak): {coarse[a].mean():.3f} m -> {coarse[b].mean():.3f} m = moved {100*(coarse[b].mean()-coarse[a].mean()):+.1f} cm')
print(f'wall echo (peak + phase):  {fine[a].mean():.3f} m -> {fine[b].mean():.3f} m = moved {100*(fine[b].mean()-fine[a].mean()):+.1f} cm')
print(f'still parts wobble: envelope sd {1000*coarse[a].std():.2f} mm, peak+phase sd {1000*fine[a].std():.2f} mm')
