import numpy as np, importlib.util, json
spec=importlib.util.spec_from_file_location('dp','doppler.py'); dp=importlib.util.module_from_spec(spec); spec.loader.exec_module(dp)
spec2=importlib.util.spec_from_file_location('d2','doppler2.py'); d2=importlib.util.module_from_spec(spec2); spec2.loader.exec_module(d2)
SR,C,P,HOP=48000,343.0,2048,256
VLANE=23.4375*C/(2*19000)    # one tone spacing of Doppler shift, m/s
def sensor_velocity(d, fr, start, t_audio, lag_s=0.33, tau=1.2):
    ok=[f for f in fr if f.get('tc')]; k,b0=np.polyfit([f['fr'] for f in ok],[f['tc'] for f in ok],1)
    tms=k*(start+t_audio*SR)+b0
    yt=np.array([f['t'] for f in fr],float); psi=np.unwrap(np.radians(np.array([f['yaw'] for f in fr])+180))
    A=np.array([a for f in fr for a in f.get('ac',[])],float); A=A[np.argsort(A[:,0])]
    pa=np.interp(A[:,0],yt,psi); af=A[:,1]*np.sin(pa)+A[:,2]*np.cos(pa)
    v=np.zeros(len(A)); m=0
    for i in range(1,len(A)):
        dt=(A[i,0]-A[i-1,0])/1000; km=1-np.exp(-dt/3); m+=km*(af[i]-m); v[i]=v[i-1]*np.exp(-dt/tau)+(af[i]-m)*dt
    return np.interp(tms-lag_s*1000, A[:,0], v)     # forward velocity (m/s, + = toward what's ahead)
def evaluate(base, truth=None, label=''):
    d,fr,x,start=dp.load(base); r=d2.remove_static(x,start)
    fine=np.arange(-0.10,0.101,0.01)
    t,vm,e=dp.run(r,start,fine,stat_tau=1e9)
    vs=sensor_velocity(d,fr,start,t)
    n=np.round((vs-vm)/VLANE); vlane=vm+n*VLANE
    out={}
    for name,vv in (('sensor only',vs),('Doppler only (+-10 cm/s)',vm),('Doppler + sensor lane',vlane)):
        disp=-np.cumsum(vv)*HOP/SR
        if truth is not None:
            a=(t>1)&(t<5); b=t>t[-1]-1.5; print(f'  {label} {name:26s}: moved {100*(disp[b].mean()-disp[a].mean()):+6.1f} cm (truth {truth:+.1f})')
        out[name]=disp
    return t,out,vs
if __name__=='__main__':
    for lag in (0.0,0.33):
        print('sensor lag correction', lag, 's')
        sensor_velocity.__defaults__=(lag,1.2)
        evaluate('logs/sweep-20261118-143500-443', truth=-25.0, label='calibration')
