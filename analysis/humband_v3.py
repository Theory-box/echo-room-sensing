import numpy as np, importlib.util
spec=importlib.util.spec_from_file_location('v2','humband_v2.py'); v2=importlib.util.module_from_spec(spec); spec.loader.exec_module(v2)
# keep the app's 2048-sample cycle (23.4375 Hz grid); hum spacing 8 or 16 grid steps (187.5 / 375 Hz) = whole cycles in
# 256 / 128 samples; read with a Hann window two such cycles long
v2.P=2048; v2.DF=48000/2048
for sp_steps,label in ((8,'187.5 Hz'),(16,'375 Hz')):
    sp=sp_steps*v2.DF; blk=int(48000/sp)
    for n_h in (8,):
        hum_f=[ (int(17250/v2.DF)//sp_steps)*sp_steps*v2.DF - sp*(n_h-1-i) for i in range(n_h)]   # ending just below ~17.25 kHz
        hk,mk,tones,amp,ph=v2.design(hum_f,max(hum_f)+3*sp,22000,3.0)
        share=(amp[:len(hk)]**2).sum()/(amp**2).sum()
        print(f'== hum {n_h} tones {label} apart, {min(hum_f)/1000:.2f}-{max(hum_f)/1000:.2f} kHz; map {(max(hum_f)+3*sp)/1000:.2f}-22 kHz; hum {100*share:.0f}% of power; map tone amp {amp[-60]:.4f} (plain 0.0587)')
        for dur in (8.0,2.0,1.0):
            x=v2.room(tones,amp,ph,12,[(1.0,lambda t:0.02+0*t),(0.05,lambda t:0.84+0*t),(0.012,v2.move(4,dur,1.0,0.25))])
            tt,cum=v2.hum_track(x,hk,win=2*blk,hop=blk)
            a0=cum[(tt>2)&(tt<3.5)].mean(); b0=cum[tt>tt[-1]-1.5].mean()
            print(f'   25 cm in {dur:.0f} s (peak {50/dur:.0f} cm/s): hum reads {100*(b0-a0):+6.1f} cm  (window {2*blk})')
