const OUT=[]; const log=s=>OUT.push(s);
const binM=0.03, binS=binM*2/343*48000;
try{
 const cases=[['quiettones',2,0.02,0,15],['quiettones',4,0.02,0,20],['quiettones',8,0.02,0,30],['quiettones',15,0.02,0,30],['strong',2,0.03,0,15],['strong',4,0.03,0,20],['strong',15,0.03,0,30],['mid',4,0.03,0,20],['mid',8,0.03,0,30],['mid',15,0.03,0,30],['wide',4,0.02,0,20],['wide',8,0.02,0,30]];
 for(const mode of ['power']){ let errs=[], miss=0, fal=0;
 for(const [ping,rate,g,clean,turn] of cases){
  const W=[{c:0,D:2.0,g},{c:90,D:1.5,g},{c:180,D:2.5,g},{c:270,D:3.2,g}];
  SIM.yawF=s=>(turn*s)%360;
  SIM.adv=()=>Math.round(48000/rate); SIM.off0=300.3; SIM.refl=[{r0:1.05,v:0,g:g*0.5}]; SIM.walls=W; SIM.GT=0; SIM.noise=0.002; SIM.junk=clean?0:0.4; SIM.drop=clean?0:0.2; SIM.seed=7;
  $('ping').value=ping; $('rate').value=String(rate); $('range').value='5'; $('mask').value='0.3'; buildSens(); buildView('map'); $('dirf').value='map'; $('walls').value='line';
  start(false); loopGen++; sonarLog=[];
  const base=performance.now();
  yawAt = t => { const y=SIM.yawF((t-base)/1000+1/rate); return ((y%360)+540)%360-180; };
  const N=Math.round(rate*Math.max(26,780/Math.abs(turn))); for(let i=0;i<N;i++){ frame(binM,binS,base+i*1000/rate);}
  const off=yaw0;
  const VW=WALLS.filter(w=>!wallHidden(w));
  const near=(w,t)=>Math.abs(angDiff(w.a,t.c-off))<25&&Math.abs(w.D-t.D)<0.15;
  const match=W.map(t=>{const m=VW.filter(w=>near(w,t)); if(m.length) errs.push(Math.abs(angDiff(m[0].a,t.c-off))); else miss++; return m.length?`${t.c}°: ${angDiff(m[0].a,t.c-off).toFixed(1)}° ${(100*(m[0].D-t.D)).toFixed(1)}cm${m.length>1?' x'+m.length:''}`:`${t.c}°: MISSED`;});
  const extra=VW.filter(w=>!W.some(t=>near(w,t))); fal+=extra.length;
  { const P=sonarLog.slice(10); const bad=P.filter(f=>!Array.isArray(f.p)||f.p.length<100).length;
    const med=a=>a.slice().sort((x,y)=>x-y)[a.length>>1];
    const wallPk=P.filter(f=>W.some(t=>{const i=Math.floor((t.D-0.25)/0.03); return Math.max(...f.p.slice(Math.max(0,i-2),i+3))>=med(f.p)+15;})).length;
    log(`   raw p: frames ${P.length}, missing ${bad}, bins ${P[0].p.length}, bytes/frame ${JSON.stringify(P[0].p).length}, median ${med(P[0].p)} dB, max ${Math.max(...P[0].p)} dB, frames with a wall >=15 dB over median ${(100*wallPk/P.length).toFixed(0)}%`); }
  { const errs=[]; for(const f of sonarLog.slice(10)){ const th=SIM.yawF(0)!==undefined?null:null; for(const e of f.e){ let best=9; for(const w of W){ const rel=angDiff(f.h, w.c-off); if(Math.abs(rel)>60) continue; const R=w.D-0.25*Math.cos(rel*Math.PI/180); if(Math.abs(e[0]-R)<Math.abs(best)) best=e[0]-R; } if(Math.abs(best)<0.1) errs.push(Math.abs(best)*100); } }
    errs.sort((x,y)=>x-y); log(`   echo distance error vs truth: median ${errs[errs.length>>1].toFixed(2)} cm, 90% ${errs[Math.floor(errs.length*0.9)].toFixed(2)} cm (n=${errs.length})`); }
  const allE=sonarLog.slice(10); const wallDet=allE.filter(f=>f.e.some(e=>W.some(t=>Math.abs(e[0]-(t.D-0.25))<0.08))).length; log(`   echoes/frame ${(allE.reduce((a,f)=>a+f.e.length,0)/allE.length).toFixed(2)}, frames with a wall echo ${(100*wallDet/allE.length).toFixed(0)}%, errors ${ERR.length}`);
  log(`[${mode}] ${ping} r${rate} g${g} turn ${turn}°/s${clean?' CLEAN':''}: ${match.join(' | ')} | false ${extra.length} ${JSON.stringify(extra.map(w=>[Math.round(angDiff(w.a,-off)),+w.D.toFixed(2)]))}`);
 }
 errs.sort((a,b)=>a-b); log(`== ${mode}: found ${errs.length}/${errs.length+miss}, median dir error ${errs[errs.length>>1].toFixed(1)}°, 90th pct ${errs[Math.floor(errs.length*0.9)].toFixed(1)}°, max ${errs[errs.length-1].toFixed(1)}°, false walls ${fal}`);
 }
}catch(e){ERR.push(e.message+' '+e.stack)}
document.body.insertAdjacentHTML('beforeend','<pre id=R>RESULT\n'+OUT.join('\n')+'\nerrors='+JSON.stringify(ERR)+'</pre>');
try{ // UI: walls row only in Map; arc mode draws no lines; log fields
 buildView('full'); $('dirf').value='full'; showViewHelp(); const hid=$('wallsrow').style.display;
 $('dirf').value='map'; showViewHelp(); const vis=$('wallsrow').style.display;
 $('walls').value='arc'; renderMap(5);
 const f=sonarLog.find(f=>f.rcd); 
 document.body.insertAdjacentHTML('beforeend','<pre id=U>UI hidden-in-radar='+(hid==='none')+' visible-in-map='+(vis==='')+' settings='+JSON.stringify(curSettings())+' sample rcd='+JSON.stringify(f&&f.rcd)+' nw='+(f&&f.nw)+'</pre>');
}catch(e){document.body.insertAdjacentHTML('beforeend','<pre id=U>UIERR '+e.message+'</pre>');}
