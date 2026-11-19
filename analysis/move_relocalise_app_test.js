// two-spot sim: spot 1 (0,0) turn twice -> lock; tap I moved; teleport to (dx, dy) (sim frame) and add gyro drift;
// turn once -> relocalisation. Report the found position (app frame) vs truth projected into the app frame.
const OUT=[]; const log=s=>OUT.push(s);
const binM=0.03, binS=binM*2/343*48000;
try{
 for(const [dx,dy,drift,walls,label] of [[0.40,-0.30,5,null,'move 40/-30 cm, drift +5'],[-0.35,0.25,-4,null,'move -35/+25 cm, drift -4'],[0.5,0,0,'nowall3','move 50 cm, wall at 270 missing'],[0,0,0,null,'no move (tap, stay)']]){
  const g=0.03; SIM.walls=[{c:0,D:1.45,g},{c:90,D:1.3,g},{c:180,D:1.4,g},{c:270,D:1.5,g}].filter(w=>!(walls==='nowall3'&&w.c===270)); SIM.refl=[{r0:3.3,v:0,g:0.01}];
  let moved=false, tMove=0;
  SIM.yawF=s=> moved ? (36*(s-tMove))%360 + drift : (24*s)%360;
  SIM.posF=s=> moved ? [dx,dy] : [0,0];
  SIM.adv=()=>Math.round(48000/10); SIM.off0=300.3; SIM.GT=0; SIM.noise=0.002; SIM.junk=0.4; SIM.drop=0.2; SIM.seed=11;
  $('ping').value='quiettones'; $('rate').value='10'; buildSens(); buildView('map'); $('dirf').value='map'; $('roombox').value='on';
  start(false); loopGen++; sonarLog=[]; clearMap(); const base=performance.now();
  yawAt = t => { const y=SIM.yawF((t-base)/1000+1/10); return ((y%360)+540)%360-180; };
  let i=0; for(;i<300;i++) frame(binM,binS,base+i*100);
  const lockRot=SLM?SLM.rot:null, p1=SLM?[SLM.x,SLM.y]:null;
  $('moved').onclick(); moved=true; tMove=i/10;
  let found=null; for(;i<520;i++){ frame(binM,binS,base+i*100); const f=sonarLog[sonarLog.length-1]; if(f.mv){found=f.mv;break;} }
  // truth in the app frame: sim heading 0 = app heading -yaw0-ish; use the locked box rotation to map: app = sim rotated by (lockRot - 0)
  const a=lockRot*Math.PI/180, tx=dx*Math.cos(a)-dy*Math.sin(a)*-1, ty=dy*Math.cos(a)+dx*Math.sin(a)*-1;
  log(`${label}: locked rot ${lockRot}, pos before ${p1&&p1.map(v=>v.toFixed(2))} | found ${found?JSON.stringify(found):'NOT FOUND'} | app pos now ${SLM.x.toFixed(2)}, ${SLM.y.toFixed(2)} (|p| ${Math.hypot(SLM.x,SLM.y).toFixed(2)} vs true ${Math.hypot(dx,dy).toFixed(2)}) | HCORR ${HCORR.toFixed(1)} (drift added ${drift}) | status: ${$('status').textContent.slice(0,170)}`);
  // after: keep turning 10 s more at the new spot -> position should hold, per-turn checks logged
  for(let k=0;k<100;k++,i++) frame(binM,binS,base+i*100);
  const tcs=sonarLog.filter(f=>f.tk).map(f=>f.tk);
  log(`   after 10 s more: pos ${SLM.x.toFixed(2)}, ${SLM.y.toFixed(2)} | turn checks ${JSON.stringify(tcs.slice(-3))}`);
  stop();
 }
}catch(e){ERR.push(e.message+' '+e.stack)}
document.body.insertAdjacentHTML('beforeend','<pre id=R>RESULT\n'+OUT.join('\n')+'\nerrors='+JSON.stringify(ERR)+'</pre>');
