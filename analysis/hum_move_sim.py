import numpy as np, importlib.util, math
spec=importlib.util.spec_from_file_location('hum2','hum2.py'); H=importlib.util.module_from_spec(spec); spec.loader.exec_module(H)
SR,C=48000,343.0; h=H.HUM16; rng=np.random.default_rng(1)
def move(t0,dur,d0,dist):
    def f(t):
        u=np.clip((t-t0)/dur,0,1); return d0-dist*(u-np.sin(2*np.pi*u)/(2*np.pi))
    return f
T=14; t=np.arange(T*SR)/SR
for dur in (8.0,4.0,2.0,1.0):
    x=np.zeros_like(t)
    for g,dfun in ((1.0,lambda t:0.02+0*t),(0.05,lambda t:0.84+0*t),(0.012,move(4,dur,1.0,0.25))):
        tau=2*dfun(t)/C
        for k in range(h.n): x+=g/4*np.cos(2*np.pi*h.fk[k]*(t-tau)+h.ph[k])
    x+=2e-5*rng.standard_normal(len(t))
    tb,cum=h.track(x)
    a=cum[(tb>2)&(tb<3.5)].mean(); b=cum[tb>tb[-1]-1.5].mean()
    print(f'hum (16 tones, 4 ms blocks): move 25 cm in {dur:.0f} s (peak {50/dur:.0f} cm/s): tracker {100*(b-a):+6.1f} cm (truth -25.0)')
