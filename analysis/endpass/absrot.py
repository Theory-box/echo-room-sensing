import numpy as np
from refit import sweeps, echoes, roomfit, angd, fmt
import refit
def offset(d, flt):
    v = [angd(f['my'], f['h']) for f in d['frames'] if flt(f) and f.get('my') is not None and f.get('h') is not None]
    v = np.array(v); c = np.degrees(np.angle(np.mean(np.exp(1j * np.radians(v)))))
    return c, np.std(angd(v, c))
def m90(x): return ((x + 45) % 90) - 45
if __name__ == '__main__':
  for lab, d, flt in sweeps():
      off, sd = offset(d, flt)
      h, r, sf, t = echoes(d, flt)
      row = []
      for tol, face in [(0.04, 30), (0.02, 30), (0.015, 40), (0.01, 45)]:
          refit.RB_TOL, refit.RB_FACE = tol, face
          f = roomfit(h, r, sf); row.append(f"{m90(f['rot'] + off):6.1f}[{f['D'][0]+f['D'][2]:.2f}x{f['D'][1]+f['D'][3]:.2f}]")
      refit.RB_TOL, refit.RB_FACE = 0.04, 30
      print(f"{lab:12s} compass-start {off:6.1f} (sd {sd:4.1f})  room angle by compass, tol/face 4cm/30 2cm/30 1.5cm/40 1cm/45: " + ' '.join(row))
