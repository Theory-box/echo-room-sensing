import numpy as np, importlib.util
from scipy.signal import firwin, lfilter
spec=importlib.util.spec_from_file_location('hb','humband_sim.py'); hb=importlib.util.module_from_spec(spec); spec.loader.exec_module(hb)
SR,C,P=48000,343.0,2048
def track_slots(x, hk, win=192, hop=192, M=64, guard=6, tau_s=3.0):
    """robust hum tracker (as for the 16-tone hum): short blocks -> per-tone values -> static removed -> coarse profile
    across the hum tones -> median phase change over slots away from the direct sound"""
    hk=np.array(hk); n=np.arange(win)
    E=np.exp(-2j*np.pi*np.outer(hk,n)/P)
    starts=np.arange(0,len(x)-win,hop)
    B=np.array([(E@x[s:s+win])*np.exp(-2j*np.pi*hk*s/P) for s in starts])
    w=np.hanning(len(hk)+2)[1:-1]
    S=B.mean(0); d0=int(np.argmax(np.abs(np.fft.ifft(S*w,M))))
    Pr=np.fft.ifft((B-S)*w,M,axis=1)
    cand=[m for m in range(M) if min((m-d0)%M,(d0-m)%M)>guard]
    fc=hk.mean()*SR/P
    Mo=np.array([-(np.unwrap(np.angle(Pr[:,m]))-np.angle(Pr[0,m]))*C/(2*np.pi*fc)/2 for m in cand])
    return (starts+win/2)/SR, np.median(Mo,0)
designs=[('6 hum tones 15.3-17.1 kHz (375 Hz apart)',[651,667,683,699,715,731],779,938,3.0),
         ('12 hum tones 14.1-17.1 kHz (250 Hz-ish: every 11th... )',list(range(603,732,11)),779,938,2.0)]
bp=firwin(401,[14000,17400],pass_zero=False,fs=SR,window=('kaiser',8))
for name,hk,m0,m1,g in designs:
    tones,amp,ph,_=hb.design(hk,m0,m1,g)
    print('==',name,f'(hum gain {g}, map tone amp {amp[-50]:.4f} vs plain 0.0587)')
    for dur in (8.0,2.0,1.0):
        x=hb.synth_room(tones,amp,ph,12,[(1.0,lambda t:0.02+0*t),(0.05,lambda t:0.84+0*t),(0.012,hb.move(4,dur,1.0,0.25))])
        xf=lfilter(bp,[1.0],x)
        for lab,sig in (('no filter',x),('band filter',xf)):
            blk=int(round(SR/((hk[1]-hk[0])*SR/P)))   # block = one cycle of the hum spacing
            tt,cum=track_slots(sig,hk,win=blk,hop=blk)
            a0=cum[(tt>2)&(tt<3.5)].mean(); b0=cum[tt>tt[-1]-1.5].mean()
            print(f'   25 cm in {dur:.0f} s, {lab:11s} (block {blk}): reads {100*(b0-a0):+6.1f} cm')
