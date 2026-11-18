# 2-D autofocus: per reading, search the phone's unknown shift (dx, dy) that makes its contribution agree best with the
# current image, evaluated on the brightest pixels; iterate. Wobble 1 cm rms (smooth).
import numpy as np, importlib.util, sys, math
spec=importlib.util.spec_from_file_location('ss','sar_sim.py'); ss=importlib.util.module_from_spec(spec); sys.argv=['x']; spec.loader.exec_module(ss)
gxs=np.arange(-1.6,1.6,0.015); gys=np.arange(-2.0,1.8,0.015); grid=np.meshgrid(gxs,gys); gx,gy=grid
for wob in (0.005,0.01):
    t,psi,px,py,wx,wy=ss.path(wob=wob); profs=ss.measure(psi,px,py)
    nomx,nomy=ss.ARM*np.sin(psi),ss.ARM*np.cos(psi)
    Iinc=ss.image(profs,psi,nomx,nomy,grid,False)
    sel=np.argsort(Iinc.ravel())[-3000:]; sx=gx.ravel()[sel]; sy=gy.ravel()[sel]          # brightest pixels (walls/objects)
    s_per=ss.P/4096/ss.SR; f0=ss.f0
    def contrib(i,dx,dy):
        x0=nomx[i]+dx; y0=nomy[i]+dy; ddx,ddy=sx-x0,sy-y0; R=np.hypot(ddx,ddy); tau=2*R/ss.C
        m=(ddx*np.sin(psi[i])+ddy*np.cos(psi[i]))/R>0.5
        v=profs[i][np.round(tau/s_per).astype(int)%4096]*np.exp(2j*np.pi*f0*tau); return np.where(m,v,0)
    est=np.zeros((len(psi),2)); cand=[(a,b) for a in np.arange(-0.03,0.0301,0.003) for b in np.arange(-0.03,0.0301,0.003)]
    for it in range(4):
        Ic=sum(contrib(i,*est[i]) for i in range(len(psi)))
        for i in range(len(psi)):
            ref=Ic-contrib(i,*est[i]); best=None
            for (a,b) in cand:
                v=np.abs(np.vdot(ref,contrib(i,a,b)))
                if best is None or v>best[0]: best=(v,a,b)
            est[i]=best[1:]
        err=np.hypot(est[:,0]-wx,est[:,1]-wy)
        print(f'  wobble {100*wob:.1f} cm, round {it+1}: shift estimate error median {1000*np.median(err):.1f} mm')
    I=ss.image(profs,psi,nomx+est[:,0],nomy+est[:,1],grid,True)
    print(f'wobble {100*wob:.1f} cm rms: object widths with 2-D autofocus {ss.point_width(I,grid,0.6,0.9):.1f}° / {ss.point_width(I,grid,-0.7,-0.6):.1f}° (true path 1.3-1.6°, like today ~42-45°)')
