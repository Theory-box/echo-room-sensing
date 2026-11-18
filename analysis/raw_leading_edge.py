import numpy as np, math
exec(open('rawan4.py').read().split("def measure")[0])
def edge_series(env, frac, navg=3):
    H=np.array([env[c+i0:c+i1]/env[c] for c in clicks])
    H=np.array([H[max(0,i-navg+1):i+1].mean(0) for i in range(len(H))])
    out=[]
    for h in H:
        m=int(np.argmax(h)); thr=frac*h[m]; j=m
        while j>0 and h[j-1]>thr: j-=1
        f=(thr-h[j-1])/(h[j]-h[j-1]) if j>0 and h[j]!=h[j-1] else 0
        out.append((i0+j-1+f)*s2m if frac<1 else (i0+m)*s2m)
    return np.array(out)
def jit(y):
    wv=2*np.pi*0.70; M=np.column_stack([np.sin(wv*tt),np.cos(wv*tt),np.ones_like(tt)]); c=np.linalg.lstsq(M,y,rcond=None)[0]; return 100*(y-M@c).std(), 100*math.hypot(c[0],c[1])
env2=np.sqrt(sum(np.abs(mf(x[:,0],subtpl(k,2)))**2 for k in range(2)))
for nm,env in (('1 band',e_full),('2 bands',env2)):
    print(nm, ' | '.join(f"{('peak' if fr==1 else f'edge {int(fr*100)}%')}: jitter {jit(edge_series(env,fr))[0]:.2f} cm" for fr in (1,0.5,0.3,0.2,0.1)))
# ringing check: direct-sound envelope shape after the peak, in dB, at 0..12 cm one-way
c=clicks[50]; d=e_full[c:c+int(0.15/s2m)]/e_full[c]
print('direct-sound tail (dB) every 1.5 cm:', ' '.join(f'{v:.0f}' for v in 20*np.log10(d[::4]+1e-9)))
for nm,env in (('1 band',e_full),('2 bands',env2)):
    for fr in (0.5,0.3,0.2,0.1):
        y=edge_series(env,fr); print(nm, f'edge {int(fr*100)}%: mean {y.mean():.3f} m, min {y.min():.3f}, share at window start (0.72 m) {np.mean(y<0.725):.2f}')
