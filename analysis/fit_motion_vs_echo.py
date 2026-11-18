import json,math,sys
import numpy as np
from scipy.signal import butter, filtfilt
f=sys.argv[1]; D0=float(sys.argv[2]); a0,b0=float(sys.argv[3]),float(sys.argv[4]); key=sys.argv[5] if len(sys.argv)>5 else 'tc'
d=json.load(open(f)); fr=d['frames']; T0=fr[0]['t']/1000
psi=np.radians(np.median([x['yaw'] for x in fr])+180)
tc=[];r=[];pv=[];tpv=[]
for x in fr:
  ws=[e for e in x['e'] if abs(e[0]-D0)<0.15]
  if ws: e=max(ws,key=lambda e:e[1]); tc.append(x[key]/1000-T0 if key in x else x['t']/1000-T0); r.append(e[0]-e[12]/100)
  if x.get('pv'): pv.append(x['pv'][0]/100); tpv.append((x['tc'] if 'tc' in x else x['t'])/1000-T0)
tc=np.array(tc); r=np.array(r)
fs=50; g=np.arange(a0,b0,1/fs)
rg=np.interp(g,tc,r)
lo,hi=0.4,2.5; bb,aa=butter(2,[lo/(fs/2),hi/(fs/2)],'band')
x_echo=-filtfilt(bb,aa,rg-rg.mean())          # phone forward displacement seen by the echo
if 'ac' in fr[0] or any('ac' in x for x in fr):
  A=np.array([a for x in fr for a in x.get('ac',[])],float); A=A[np.argsort(A[:,0])]; ta=A[:,0]/1000-T0
  af=A[:,1]*np.sin(psi)+A[:,2]*np.cos(psi)
  ag=np.interp(g,ta,af); ab=filtfilt(bb,aa,ag-ag.mean())
  # double integrate in frequency domain within band
  N=len(ab); Fq=np.fft.rfftfreq(N,1/fs); S=np.fft.rfft(ab); w=2*np.pi*Fq; S[1:]=S[1:]/(-(w[1:]**2)); S[0]=0
  x_acc=np.fft.irfft(S,N); x_acc=filtfilt(bb,aa,x_acc)
  def xc(u,v):
    best=None
    for L in range(-40,41):   # +-0.8 s
      if L>=0: a,b=u[L:],v[:len(v)-L]
      else: a,b=u[:L],v[-L:]
      c=np.corrcoef(a,b)[0,1]
      if best is None or c>best[0]: best=(c,L,np.dot(a,b)/np.dot(b,b))
    return best
  c,L,gn=xc(x_acc,x_echo)
  print(f'{f[-30:-16]} {a0}-{b0}s: accel-derived vs echo-derived motion: best correlation {c:.2f} when acceleration is shifted {L*1000/fs:+.0f} ms (+ = acceleration timeline is early); scale {gn:.2f}x; echo motion rms {100*x_echo.std():.2f} cm, accel motion rms {100*x_acc.std():.2f} cm')
pvg=np.interp(g,np.array(tpv),np.array(pv)); v_echo=np.gradient(x_echo,1/fs); vb=filtfilt(bb,aa,pvg-pvg.mean())
best=None
for L in range(-40,41):
  if L>=0: a,b=vb[L:],v_echo[:len(v_echo)-L]
  else: a,b=vb[:L],v_echo[-L:]
  c=np.corrcoef(a,b)[0,1]
  if best is None or c>best[0]: best=(c,L,np.dot(a,b)/np.dot(b,b))
print(f'    app velocity estimate vs echo: correlation {best[0]:.2f} at shift {best[1]*1000/fs:+.0f} ms, scale {best[2]:.2f}x; at zero shift corr {np.corrcoef(vb,v_echo)[0,1]:.2f}')
