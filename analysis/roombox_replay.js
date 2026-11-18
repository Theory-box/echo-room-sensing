const OUT=[]; const FILES=["rb_161659-916.json","rb_161753-114.json","rb_161829-437.json","rb_161910-971.json","rb_162000-283.json","rb_162107-513.json","rb_141954-224.json","rb_140553-471.json","rb_140408-771.json","rb_125027-701.json","rb_120930-256.json","rb_121133-233.json","rb_121421-809.json","rb_123840-246.json","rb_154811-707.json"];
try{
  const orig=ringFree;
  for(const f of FILES){
    const x=new XMLHttpRequest(); x.open('GET',f,false); x.send(); const d=JSON.parse(x.responseText); const fr=d.frames;
    const hs=fr.map(q=>q.h); if(Math.max(...hs)-Math.min(...hs)<300) continue;
    RBOX={h:[],r:[],last:0,fit:null};
    for(const q of fr) for(const e of q.e) if(e[10]&&e[0]>0.35){ RBOX.h.push(q.h); RBOX.r.push(e[0]-(e[12]||0)/100); }
    const fmt=fit=>{const D=fit.D,w1=D[0]+D[2],w2=D[1]+D[3]; const st=fit.votes.map(v=>v>2*fit.clutter?'*':'.').join(''); return Math.min(w1,w2).toFixed(2)+' x '+Math.max(w1,w2).toFixed(2)+' m ['+D.map(v=>v.toFixed(2)).join(' ')+'] '+st;};
    ringFree=(h,r)=>({h,r,rings:[]}); const a=roomFit(); ringFree=orig; const b=roomFit();
    OUT.push(f.slice(3,13)+' '+d.settings.ping.padEnd(12)+' without: '+fmt(a).padEnd(46)+' with ring exclusion: '+fmt(b)+(b.rings.length?'  rings '+JSON.stringify(b.rings):''));
  }
}catch(e){ERR.push(e.message+' '+e.stack)}
document.body.insertAdjacentHTML('beforeend','<pre id=R>RESULT\n'+OUT.join('\n')+'\nerrors='+JSON.stringify(ERR)+'</pre>');
