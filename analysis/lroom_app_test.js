// L-shaped room, 3 spots. Sim frame: x east, y north. Main part x -1.5..1.5, y -1..2; leg x 1.5..3.6, y -1..1.
const OUT=[]; const log=s=>OUT.push(s);
const binM=0.03, binS=binM*2/343*48000;
try{
 const g=0.03;
 const LROOM=[{n:'N main',c:0,D:2,lo:-1.5,hi:1.5},{n:'W',c:270,D:1.5,lo:-1,hi:2},{n:'S',c:180,D:1,lo:-3.6,hi:1.5},
   {n:'E main',c:90,D:1.5,lo:-2,hi:-1.0},{n:'N leg',c:0,D:1.0,lo:1.5,hi:3.6},{n:'E end',c:90,D:3.6,lo:-1,hi:1}];
 SIM.walls=LROOM.map(w=>Object.assign({g},w)); SIM.refl=[];
 // script: [t0, t1, kind, ...]
 const S1=[0,0], S2=[2.6,0], S3=[-0.5,1.4];
 let phase=0;
 const plan=[ // [duration s, yaw fn(s within), pos fn(s within), action at start]
   [24, s=>(30*s)%360, s=>S1, null],
   [7, s=>90+15*Math.sin(2*Math.PI*s/2), s=>{const k=Math.min(1,s/6); return [S1[0]+k*(S2[0]-S1[0]), S1[1]+k*(S2[1]-S1[1])];}, 'pause'],
   [14, s=>(90+30*s)%360, s=>S2, 'resume'],
   [9, s=>-66+15*Math.sin(2*Math.PI*s/2), s=>{const k=Math.min(1,s/8); return [S2[0]+k*(S3[0]-S2[0]), S2[1]+k*(S3[1]-S2[1])];}, 'pause'],
   [14, s=>(-66+30*s)%360, s=>S3, 'resume'],
 ];
 let segStart=0, segIdx=0; const segAt=t=>{let acc=0; for(let i=0;i<plan.length;i++){ if(t<acc+plan[i][0]) return [i,t-acc]; acc+=plan[i][0]; } return [plan.length-1, plan[plan.length-1][0]];};
 SIM.yawF=ts=>{const [i,s]=segAt(ts); return plan[i][1](s);}; SIM.posF=ts=>{const [i,s]=segAt(ts); return plan[i][2](s);};
 SIM.adv=()=>Math.round(48000/10); SIM.off0=300.3; SIM.GT=0; SIM.noise=0.002; SIM.junk=0.4; SIM.drop=0.2; SIM.seed=21;
 $('ping').value='quiettones'; $('rate').value='10'; buildSens(); buildView('map'); $('dirf').value='map'; $('roombox').value='on';
 start(false); loopGen++; sonarLog=[]; clearMap(); const base=performance.now();
 yawAt = t => { const y=SIM.yawF((t-base)/1000+0.1); return ((y%360)+540)%360-180; };
 const total=plan.reduce((a,p)=>a+p[0],0); let lastSeg=-1; const found=[];
 for(let i=0;i<total*10;i++){ const ts=i/10, [si]=segAt(ts);
   if(si!==lastSeg){ lastSeg=si; const act=plan[si][3]; if(act==='pause'||act==='resume'){ $('moved').onclick(); } }
   frame(binM,binS,base+i*100); const f=sonarLog[sonarLog.length-1]; if(f.mv){ found.push([ts,f.mv,$('status').textContent.slice(0,260)]); }
 }
 const y0=yaw0||0, toApp=p=>{const r=Math.hypot(p[0],p[1]), ph=Math.atan2(p[0],p[1])-y0*Math.PI/180; return [r*Math.sin(ph), r*Math.cos(ph)];};
 log(`yaw0 ${y0.toFixed(1)} | locked box rot ${SLM&&SLM.rot} D ${SLM&&SLM.D.map(v=>v.toFixed(2)).join(' ')} (true main part: N 2, W 1.5, S 1, E 1.5 / leg end 3.6)`);
 for(const [ts,mv,st] of found){ log(`at ${ts.toFixed(1)} s: found ${JSON.stringify(mv)}\n   status: ${st}`); }
 for(const [nm,P] of [['spot2',S2],['spot3',S3]]){ const a=toApp(P); log(`truth ${nm} in app frame: ${a.map(v=>v.toFixed(2)).join(', ')}`); }
 log(`final pos ${SLM.x.toFixed(2)}, ${SLM.y.toFixed(2)} | extra wall pieces: ${JSON.stringify(XW.map(w=>({j:w.j,D:+w.D.toFixed(2),heard:w.heard.map(v=>+v.toFixed(2)),miss:w.miss.map(v=>+v.toFixed(2)),spots:w.spots})))}`);
 log(`box wall bounds: ${SLM.wb.map((w,j)=>j+':'+wallBounds(w).map(v=>isFinite(v)?v.toFixed(2):(v>0?'+inf':'-inf')).join('..')).join(' | ')}`);
 renderMap(5); stop();
}catch(e){ERR.push(e.message+' '+e.stack)}
document.body.insertAdjacentHTML('beforeend','<pre id=R>RESULT\n'+OUT.join('\n')+'\nerrors='+JSON.stringify(ERR)+'</pre>');
