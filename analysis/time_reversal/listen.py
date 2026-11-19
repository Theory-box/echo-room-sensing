# listening version: the time-reversed sound 8 times, 2.5 s apart
import numpy as np
from common import *
tr=np.load('tr_sig.npy'); seq=[np.zeros(20*SR)]
for k in range(8): seq+=[tr,np.zeros(int(2.5*SR))]
out=np.concatenate(seq); save('listen.wav',out); print('listen.wav %.1f s'%(len(out)/SR))
