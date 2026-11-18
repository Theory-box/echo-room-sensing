const OUT=[]; const log=s=>OUT.push(s);
const binM=0.03, binS=binM*2/343*48000;
try{
 // walking detector: parse a bouncing vertical acceleration from Native.motion
 { let k=0; Native.motion=()=>{ let s=[]; for(let i=0;i<10;i++){ k++; s.push(`${(10-i)*5},0.1,0.05,${(1.6*Math.sin(2*Math.PI*1.8*k/100)).toFixed(3)}`);} return s.join(';'); };
   for(let i=0;i<6;i++) motionTick(0); const w1=slWalking(performance.now()), r1=wkRms;
   Native.motion=()=>{ let s=[]; for(let i=0;i<10;i++){ k++; s.push(`${(10-i)*5},0.8,0.6,${(0.15*Math.sin(2*Math.PI*1.8*k/100)).toFixed(3)}`);} return s.join(';'); };
   wkUntil=0; UPH=[]; for(let i=0;i<6;i++) motionTick(0); log(`walking detector: bounce 1.6 m/s2 -> walking=${w1} (rms ${r1.toFixed(2)}); arm sweep (sideways 0.8, up 0.15) -> walking=${slWalking(performance.now())} (rms ${wkRms.toFixed(2)})`);
   delete Native.motion; }
 for(const [ping,rate,walkTo,sweep] of [['quiettones',10,0.8,40],['quiettones',10,1.0,60],['quiettones',10,0.6,90]]){
  const g=0.03, W=[{c:0,D:1.6,g},{c:90,D:1.3,g},{c:180,D:1.4,g},{c:270,D:1.5,g}];
  const TT=24, TW=4;   // turn 2x in 24 s, walk for 4 s, then stand
  SIM.yawF=s=> s<TT ? (30*s)%360 : sweep*Math.sin(2*Math.PI*(s-TT)/3);
  SIM.posF=s=> s<TT ? [0,0] : [0, walkTo*Math.min(1,(s-TT)/TW)];
  SIM.adv=()=>Math.round(48000/rate); SIM.off0=300.3; SIM.refl=[{r0:1.05,v:0,g:0.02}]; SIM.walls=W; SIM.GT=0; SIM.noise=0.002; SIM.junk=0.4; SIM.drop=0.2; SIM.seed=7;
  $('ping').value=ping; $('rate').value=String(rate); $('range').value='5'; $('mask').value='0.3'; buildSens(); buildView('map'); $('dirf').value='map'; $('walls').value='line'; $('roombox').value='on';
  start(false); loopGen++; sonarLog=[]; clearMap();
  const base=performance.now();
  yawAt = t => { const y=SIM.yawF((t-base)/1000+1/rate); return ((y%360)+540)%360-180; };
  let simWalk=false, tl=null; slWalking=()=>simWalk;
  const N=Math.round(rate*(TT+TW+10)); const rows=[];
  for(let i=0;i<N;i++){ const s=i/rate; simWalk = s>=TT-0.2 && s<TT+TW+0.5; frame(binM,binS,base+i*1000/rate);
    if(SLM && tl===null) tl=s; if(SLM && i%Math.round(rate/2)==0) rows.push([s, SLM.x, SLM.y, SIM.posF(s)[1]]); }
  const lk=sonarLog.find(f=>f.slk), nsl=sonarLog.filter(f=>f.sl).length;
  log(`${ping} r${rate}, walk ${walkTo} m toward the 1.6 m wall sweeping +-${sweep}: locked at ${lk?tl.toFixed(1)+' s, box '+JSON.stringify(lk.slk):'NEVER'} | frames with sl ${nsl}`);
  if(rows.length){ const e=rows.filter(r=>r[0]>=TT).map(r=>Math.hypot(r[1],r[2]-r[3])); e.sort((a,b)=>a-b);
    const pre=rows.filter(r=>r[0]<TT).map(r=>Math.hypot(r[1],r[2]));
    log(`   before walking: max drift ${(100*Math.max(0,...pre)).toFixed(1)} cm | from walk start: median error ${(100*e[e.length>>1]).toFixed(1)} cm, max ${(100*e[e.length-1]).toFixed(1)} cm`);
    log('   trace (s: est x,y | true y): '+rows.filter(r=>r[0]>=TT-1).filter((r,i)=>i%2==0).map(r=>`${r[0].toFixed(0)}: ${(100*r[1]).toFixed(0)},${(100*r[2]).toFixed(0)}|${(100*r[3]).toFixed(0)}`).join('  ')); }
  log('   moves-with-you distances: '+JSON.stringify(WY.dist.map(d=>[+d.r.toFixed(2),d.n])));
  renderMap(5); stop();
 }
 log('errors '+ERR.length);
}catch(e){ERR.push(e.message+' '+e.stack)}
document.body.insertAdjacentHTML('beforeend','<pre id=R>RESULT\n'+OUT.join('\n')+'\nerrors='+JSON.stringify(ERR)+'</pre>');
