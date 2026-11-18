const OUT=[];
try{
  const x=new XMLHttpRequest(); x.open('GET','s140553.json',false); x.send(); const fr=JSON.parse(x.responseText).frames;
  RBOX={h:[],r:[],last:0,fit:null};
  for(const f of fr) for(const e of f.e) if(e[10]&&e[0]>0.35){ RBOX.h.push(f.h); RBOX.r.push(e[0]-(e[12]||0)/100); }
  const t0=performance.now(); const fit=roomFit(); const ms=performance.now()-t0;
  OUT.push(`app roomFit on 14:05 sweep: rot ${fit.rot}, walls ${fit.D.map(v=>v.toFixed(2)).join(', ')}, votes ${fit.votes.join(', ')}, clutter ${fit.clutter}, echoes ${fit.n}, ${ms.toFixed(0)} ms`);
  $('dirf').value='map'; $('roombox').value='on'; RBOX.fit=fit; renderMap(5); OUT.push('drawn ok');
}catch(e){ERR.push(e.message+' '+e.stack)}
document.body.insertAdjacentHTML('beforeend','<pre id=R>RESULT\n'+OUT.join('\n')+'\nerrors='+JSON.stringify(ERR)+'</pre>');
