import math, numpy as np
import slam5 as B, slam7 as D
class T8(D.T7):
    def __init__(self, *a, rtail=4.0, **k): super().__init__(*a, **k); self.rtail = rtail; self.lastwalk = -1e9; self.allow = False
    def step(self, t, theta, dets, walking):
        if walking: self.lastwalk = t
        rn = self.rneed
        if not walking and t - self.lastwalk > self.rtail: self.rneed = 10 ** 9   # recovery off
        try: return super().step(t, theta, dets, walking)
        finally: self.rneed = rn
def run(**kw):
    orig = B.T5; B.T5 = lambda *x, **k: T8(*x, **k)
    try: return B.same_spot(**kw), B.sims(**kw)
    finally: B.T5 = orig
for kw in (dict(rtail=3.0), dict(rtail=5.0), dict(rtail=5.0, rneed=4)):
    a, b = run(hold=1.0, agree=0.06, **kw); print('recovery after walking', kw, '\n   same-spot max drift:', a, '\n   sims:', b)
