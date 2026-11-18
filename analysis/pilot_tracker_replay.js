const OUT=[];
try{
  const x=new XMLHttpRequest(); x.open('GET','push_pil.wav',false); x.overrideMimeType('text/plain; charset=x-user-defined'); x.send();
  const str=x.responseText, n=str.length, buf=new Uint8Array(n); for(let i=0;i<n;i++) buf[i]=str.charCodeAt(i)&255;
  const f32=new Float32Array(buf.buffer.slice(44)); const N=f32.length/2;
  $('ping').value='quietpilots'; buildSens(); start(false);
  setTimeout(()=>{ try{
    stop(); ptReset(); const L=(HS_J+1)*HS_P; let ms=0; const t0=performance.now();
    const ser=[]; for(let fr=L; fr<=N; fr+=4096){ const xr=f32.subarray(2*(fr-L),2*fr); pilotTrack(xr,L,fr,abs=>abs); if(PT.last) ser.push([fr,+(1000*PT.cum).toFixed(3)]); }
    ms=performance.now()-t0;
    OUT.push(JSON.stringify({ms:Math.round(ms), windows:PT.hist.length, hist:ser}));
  }catch(e){ERR.push(e.message+' '+e.stack)}
  document.body.insertAdjacentHTML('beforeend','<pre id=R>RESULT\n'+OUT.join('\n')+'\nerrors='+JSON.stringify(ERR)+'</pre>'); },500);
}catch(e){ERR.push(e.message+' '+e.stack); document.body.insertAdjacentHTML('beforeend','<pre id=R>RESULT\nerrors='+JSON.stringify(ERR)+'</pre>');}
