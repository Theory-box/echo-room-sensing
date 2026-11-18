import numpy as np, importlib.util
from scipy.signal import butter, filtfilt
spec=importlib.util.spec_from_file_location('d3','doppler3.py'); d3=importlib.util.module_from_spec(spec); spec.loader.exec_module(d3)
SR=48000
# calibration: speeds while resting (should be ~0) and during the move
t,out,vs=d3.evaluate('logs/sweep-20261118-143500-443')
vm=-np.gradient(out['Doppler only (+-10 cm/s)'])/(256/SR)
for s in range(0,int(t[-1])):
    m=(t>=s)&(t<s+1); print(f'  calib {s:2d}s Doppler speed median {100*np.median(vm[m]):+5.1f} cm/s, spread {100*np.std(vm[m]):4.1f}')
# push run: band-passed Doppler displacement vs sensor forward (like before)
t,out,vs=d3.evaluate('logs/sweep-20261118-142308-495')
fs=SR/256; bb,aa=butter(2,[0.15/(fs/2),2.0/(fs/2)],'band')
dd=filtfilt(bb,aa,out['Doppler only (+-10 cm/s)']-np.mean(out['Doppler only (+-10 cm/s)']))
sd=filtfilt(bb,aa,-np.cumsum(vs)*256/SR)   # sensor displacement (path change sign)
best=None
for L in range(-130,131):
    a,b=(dd[L:],sd[:len(sd)-L]) if L>=0 else (dd[:L],sd[-L:])
    c=np.corrcoef(a,b)[0,1]
    if best is None or abs(c)>abs(best[0]): best=(c,L/fs*1000,np.dot(a,b)/np.dot(b,b))
print(f'push run: Doppler-only movement vs sensor: corr {best[0]:+.2f} at {best[1]:+.0f} ms, scale {best[2]:+.2f} (pilot tracker was 0.69-0.71, scale 0.18-0.23)')
