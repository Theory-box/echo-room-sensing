// push test sim: stand facing a wall at 1.2 m (heading 0), push the phone in/out 6 cm at 0.7 Hz for 8 s.
// Echoes: the wall (moves with the phone), a ghost at 2.9 m that does NOT move (like the room-width echo), and a second
// real surface at 2.2 m straight ahead (moves). Expect: ghost found at ~2.9 m, walls not marked ghost.
const OUT=[]; const log=s=>OUT.push(s);
const binM=0.03, binS=binM*2/343*48000;
try{
 for(const [ping,rate] of [['quiettones',10],['quiettones',15]]){
  const g=0.03;
  SIM.walls=[{c:0,D:1.45,g}]; SIM.refl=[{r0:2.9,v:0,g:0.02}];
  SIM.yawF=s=>3*Math.sin(2*Math.PI*s/5);
  SIM.posF=s=>[0, 0.03*Math.sin(2*Math.PI*0.7*s)];
  SIM.walls.push({c:2,D:2.45,g:0.02});
  SIM.adv=()=>Math.round(48000/rate); SIM.off0=300.3; SIM.GT=0; SIM.noise=0.002; SIM.junk=0.4; SIM.drop=0.2; SIM.seed=7;
  $('ping').value=ping; $('rate').value=String(rate); $('range').value='5'; $('mask').value='0.3'; buildSens(); buildView('map'); $('dirf').value='map'; $('roombox').value='on';
  start(false); loopGen++; sonarLog=[]; clearMap();
  const base=performance.now();
  yawAt = t => { const y=SIM.yawF((t-base)/1000+1/rate); return ((y%360)+540)%360-180; };
  for(let i=0;i<rate*10;i++) frame(binM,binS,base+i*1000/rate);
  const pg=sonarLog.filter(f=>f.pg);
  log(`${ping} r${rate}: ghosts ${JSON.stringify(PG.ghosts.map(g=>[+g.r.toFixed(2),Math.round(g.h)]))} | checks with verdicts ${pg.length}, sample ${JSON.stringify(pg.slice(-2).map(f=>f.pg))} | status: ${$('status').textContent.slice(0,120)}`);
  stop();
 }
}catch(e){ERR.push(e.message+' '+e.stack)}
document.body.insertAdjacentHTML('beforeend','<pre id=R>RESULT\n'+OUT.join('\n')+'\nerrors='+JSON.stringify(ERR)+'</pre>');
