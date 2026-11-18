# Synthetic aperture from a turn: the phone swings on a ~25 cm circle around you while turning; combining the echoes
# COHERENTLY (keeping phase) along that path could sharpen direction ~10x -- if the path is known to ~mm. Hand wobble
# is unknown -> try a simple autofocus (per-reading phase correction that best agrees with the current image).
import numpy as np, math, sys
SR, C, P, K0, NT = 48000, 343.0, 2048, 683, 256
fk = (K0 + np.arange(NT)) * SR / P; f0 = fk[0]; df = SR / P
rng = np.random.default_rng(3)
ARM = 0.25
def scene():
    pts = []
    for (cx, cy, nx, ny, L) in ((0, 1.6, 0, -1, 3.0), (1.3, 0, -1, 0, 3.0), (0, -1.9, 0, 1, 3.0), (-1.5, 0, 1, 0, 3.0)):   # 4 walls
        for s in np.arange(-L / 2, L / 2, 0.01):
            x = cx + (-ny) * s; y = cy + nx * s
            pts.append((x, y, 0.02 * rng.normal() + 0.02j * rng.normal(), (nx, ny)))   # rough wall: many small scatterers
    pts.append((0.6, 0.9, 0.6, None)); pts.append((-0.7, -0.6, 0.6, None))           # two small objects (points)
    return pts
PTS = scene()
X = np.array([p[0] for p in PTS]); Y = np.array([p[1] for p in PTS]); G = np.array([p[2] for p in PTS], complex)
NRM = [p[3] for p in PTS]
NX = np.array([n[0] if n else 0 for n in NRM]); NY = np.array([n[1] if n else 0 for n in NRM]); ISPT = np.array([n is None for n in NRM])
def path(T=24.0, rate=24, wob=0.01):
    t = np.arange(0, T, 1 / rate); psi = np.radians(-180 + 360 * t / T)
    # smooth random wobble (2-D), rms `wob`
    def smooth():
        w = rng.normal(size=len(t)); k = np.exp(-0.5 * (np.arange(-30, 31) / 8) ** 2); w = np.convolve(w, k / k.sum(), 'same'); return w / w.std()
    wx, wy = wob * smooth(), wob * smooth()
    px = ARM * np.sin(psi) + wx; py = ARM * np.cos(psi) + wy
    return t, psi, px, py, wx, wy
def measure(psi, px, py, snr_noise=0.002):
    """per reading: complex distance profile (as the tone pipeline makes), 4096 points over one 2048-sample period"""
    w = np.hanning(NT + 2)[1:-1]; profs = []
    for a, x0, y0 in zip(psi, px, py):
        dx, dy = X - x0, Y - y0; R = np.hypot(dx, dy); ux, uy = dx / R, dy / R
        ang = np.degrees(np.arccos(np.clip(ux * np.sin(a) + uy * np.cos(a), -1, 1)))
        beam = np.where(ang < 90, np.cos(np.radians(ang)) ** 4, 0.0)
        spec = np.where(ISPT, 1.0, np.clip(-(ux * NX + uy * NY), 0, 1) ** 2)    # walls reflect mostly back along their normal
        amp = G * beam * spec / R
        H = (amp[None, :] * np.exp(-2j * np.pi * fk[:, None] * (2 * R[None, :] / C))).sum(1)
        H += snr_noise * (rng.normal(size=NT) + 1j * rng.normal(size=NT))
        profs.append(np.fft.ifft(H * w, 4096))
    return np.array(profs)
def image(profs, psi, px, py, grid, coherent, phase_corr=None):
    gx, gy = grid; I = np.zeros(gx.shape, complex); s_per = P / 4096 / SR      # seconds of delay per profile point
    for i, (a, x0, y0) in enumerate(zip(psi, px, py)):
        dx, dy = gx - x0, gy - y0; R = np.hypot(dx, dy); tau = 2 * R / C
        cosang = (dx * np.sin(a) + dy * np.cos(a)) / R
        m = cosang > 0.5                                   # only where this reading's beam points (+-60 deg)
        idx = np.round(tau / s_per).astype(int) % 4096
        v = profs[i][idx]
        if coherent:
            v = v * np.exp(2j * np.pi * f0 * tau)
            if phase_corr is not None: v = v * np.exp(-1j * phase_corr[i])
        else: v = np.abs(v)
        I += np.where(m, v, 0)
    return np.abs(I)
def autofocus(profs, psi, px, py, grid, iters=6):
    gx, gy = grid; s_per = P / 4096 / SR; phc = np.zeros(len(psi))
    contrib = []
    for i, (a, x0, y0) in enumerate(zip(psi, px, py)):
        dx, dy = gx - x0, gy - y0; R = np.hypot(dx, dy); tau = 2 * R / C
        m = (dx * np.sin(a) + dy * np.cos(a)) / R > 0.5
        v = profs[i][np.round(tau / s_per).astype(int) % 4096] * np.exp(2j * np.pi * f0 * tau)
        contrib.append(np.where(m, v, 0))
    contrib = np.array(contrib)
    for _ in range(iters):
        Ic = (contrib * np.exp(-1j * phc)[:, None, None]).sum(0)
        phc = np.angle((contrib * np.conj(Ic)[None]).sum((1, 2)))      # phase of each reading vs the current image
    return np.abs((contrib * np.exp(-1j * phc)[:, None, None]).sum(0))
def point_width(I, grid, x0, y0):
    """angular width (deg, -6 dB) of the image around a point object, seen from the turning spot"""
    gx, gy = grid; R0 = math.hypot(x0, y0); a0 = math.degrees(math.atan2(x0, y0))
    rr = np.hypot(gx, gy); aa = np.degrees(np.arctan2(gx, gy))
    ring = np.abs(rr - R0) < 0.04; sel = ring & (np.abs(((aa - a0 + 180) % 360) - 180) < 40)
    vals = I[sel]; angs = ((aa[sel] - a0 + 180) % 360) - 180
    if vals.max() <= 0: return float('nan')
    o = np.argsort(angs); a_s = angs[o]; v_s = vals[o]; pk = v_s.max()
    above = a_s[v_s >= pk / 2]
    return above.max() - above.min()
if __name__ == '__main__':
    gxs = np.arange(-1.6, 1.6, 0.015); gys = np.arange(-2.0, 1.8, 0.015); grid = np.meshgrid(gxs, gys)
    for wob in (0.0, 0.01, 0.02):
        t, psi, px, py, wx, wy = path(wob=wob)
        profs = measure(psi, px, py)
        nomx, nomy = ARM * np.sin(psi), ARM * np.cos(psi)       # what we'd assume: no wobble
        out = []
        for lab, I in (('no phase (like today)', image(profs, psi, nomx, nomy, grid, False)),
                       ('phase kept, true path', image(profs, psi, px, py, grid, True)),
                       ('phase kept, wobble unknown', image(profs, psi, nomx, nomy, grid, True)),
                       ('phase kept + autofocus', autofocus(profs, psi, nomx, nomy, grid))):
            w1 = point_width(I, grid, 0.6, 0.9); w2 = point_width(I, grid, -0.7, -0.6)
            out.append(f'{lab}: {w1:.1f}° / {w2:.1f}°')
        print(f'hand wobble {100*wob:.0f} cm rms -> object sharpness (-6 dB width): ' + ' | '.join(out))
