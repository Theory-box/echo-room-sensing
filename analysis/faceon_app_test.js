// face-on dots sim: room with walls; (a) slow sweep +-25 deg across the wall at heading 0 (period 6 s) -> amber while
// near square-on, green mark after a pass; (b) fast full turns (36 deg/s) -> few/no green; (c) a push facing a wall.
const OUT=[]; const log=s=>OUT.push(s);
const binM=0.03, binS=binM*2/343*48000;
try{
 const cases=[['slow sweep +-25 across a wall',s=>25*Math.sin(2*Math.PI*s/6),s=>[0,0]],
              ['fast turning 36 deg/s',s=>(36*s)%360,s=>[0,0]],
              ['facing wall, pushing 6 cm',s=>2*Math.sin(2*Math.PI*s/5),s=>[0,0.03*Math.sin(2*Math.PI*0.7*s)]]];
 for(const [name,yf,pf] of cases){
  const g=0.03; SIM.walls=[{c:0,D:1.45,g},{c:90,D:1.3,g},{c:180,D:1.5,g},{c:270,D:1.6,g}]; SIM.refl=[];
  SIM.yawF=yf; SIM.posF=pf; SIM.adv=()=>Math.round(48000/10); SIM.off0=300.3; SIM.GT=0; SIM.noise=0.002; SIM.junk=0.4; SIM.drop=0.2; SIM.seed=7;
  $('ping').value='quiettones'; $('rate').value='10'; buildSens(); buildView('map'); $('dirf').value='map'; $('roombox').value='on';
  start(false); loopGen++; sonarLog=[]; clearMap(); const base=performance.now();
  yawAt = t => { const y=SIM.yawF((t-base)/1000+1/10); return ((y%360)+540)%360-180; };
  for(let i=0;i<200;i++) frame(binM,binS,base+i*100);
  const amber=sonarLog.filter(f=>f.fl).length, fo=sonarLog.filter(f=>f.fo).map(f=>f.fo);
  log(`${name}: amber shown in ${amber}/${sonarLog.length} readings | green marks ${FO.good.length}: ${JSON.stringify(fo.slice(0,6))}`);
  renderMap(5); stop();
 }
}catch(e){ERR.push(e.message+' '+e.stack)}
document.body.insertAdjacentHTML('beforeend','<pre id=R>RESULT\n'+OUT.join('\n')+'\nerrors='+JSON.stringify(ERR)+'</pre>');
