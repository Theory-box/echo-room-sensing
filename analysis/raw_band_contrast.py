import numpy as np
exec(open('rawan4.py').read().split("def measure")[0])
def prof(env, navg=3):
    H=np.array([env[c:c+int(5.0/s2m)]/env[c] for c in clicks if c+int(5.0/s2m)<=len(env)])
    return np.array([H[max(0,i-navg+1):i+1].mean(0) for i in range(len(H))])
def stats(env,name):
    H=prof(env); i0w,i1w=int(0.72/s2m),int(1.14/s2m); a,b=int(0.5/s2m),int(4.5/s2m)
    wall=20*np.log10(H[:,i0w:i1w].max(1)); med=20*np.log10(np.median(H[:,a:b],1)); tail=20*np.log10(np.percentile(H[:,int(4.6/s2m):],30,axis=1))
    # count distinct peaks above (median+7 dB) in 0.5-4.5 m, the app's Quiet-like threshold
    npk=[]
    for h,m in zip(H,med):
        L=20*np.log10(h[a:b]+1e-12); thr=m+7; pk=np.where((L[1:-1]>=thr)&(L[1:-1]>=L[:-2])&(L[1:-1]>L[2:]))[0]
        # merge peaks closer than 12 cm
        cnt=0; last=-1e9
        for p in pk:
            if p-last>int(0.12/s2m): cnt+=1; last=p
        npk.append(cnt)
    print(f'{name:12s}: wall above median {np.median(wall-med):5.1f} dB, above noise {np.median(wall-tail):5.1f} dB, peaks over median+7 dB per reading {np.median(npk)}')
stats(e_full,'1 band')
for K in (2,4):
    env=np.zeros(len(x))
    for k in range(K): env+=np.abs(mf(x[:,0],subtpl(k,K)))**2
    stats(np.sqrt(env),f'{K} bands')
