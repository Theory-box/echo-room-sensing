import json,collections,math,statistics as stt
def ad(a,b): return (a-b+540)%360-180
S={'1':'sweep-20261118-121421-809-sonar_log.json','2':'sweep-20261118-120930-256-sonar_log.json','4':'sweep-20261118-121133-233-sonar_log.json'}
q=lambda a,p: a[min(len(a)-1,int(p*len(a)))] if a else float('nan')
for k,f in S.items():
  d=json.load(open(f)); fr=d['frames']; n=len(fr)
  E=[e for x in fr for e in x['e']]
  conf=sum(1 for e in E if e[10]); 
  tr=collections.defaultdict(list)
  for i,x in enumerate(fr):
    for e in x['e']:
      if e[9] and e[10]: tr[e[9]].append((i,e[0],x['h'],x['gy']))
  steps=sorted(abs(b[1]-a[1])*100 for v in tr.values() for a,b in zip(v,v[1:]) if b[0]==a[0]+1)
  # within-track wobble: sd of distance over 1 s windows for tracks while turning slowly
  wob=[]
  for v in tr.values():
    for j in range(0,len(v)-15,15):
      seg=v[j:j+15]
      if seg[-1][0]-seg[0][0]==14: wob.append(stt.pstdev([s[1] for s in seg])*100)
  wob.sort()
  W=[w for x in fr for w in x.get('rcd',[]) if w[5]==1]
  R=[w for x in fr for w in x.get('rcd',[])]
  lens=sorted(len(v) for v in tr.values())
  print(f"bands {k}: {n} readings ({n/15:.0f} s) | echoes/reading {len(E)/n:.2f}, confirmed {100*conf/len(E):.0f}% | confirmed tracks {len(tr)}, median life {q(lens,.5)} readings")
  print(f"   distance step between readings (same echo): median {q(steps,.5):.2f} cm, 90% {q(steps,.9):.2f} cm | 1-s wobble sd median {q(wob,.5):.2f} cm, 90% {q(wob,.9):.2f} cm")
  print(f"   wall regions: {len(R)} ended, {len(W)} became walls ({len(W)/(n/15)*60:.0f} per min); final walls nw={fr[-1].get('nw')}")
  # walls list for cross-session comparison
  print('   walls (dist m @ heading):', sorted((round(w[1],2),w[2]) for w in W)[:40])
