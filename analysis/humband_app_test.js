const OUT=[];
try{
  // 1) fftN vs brute force for n=1920
  const n=1920, re=new Float64Array(n), im=new Float64Array(n); for(let i=0;i<n;i++){re[i]=Math.sin(i*0.37)+Math.cos(i*i*0.001); im[i]=0.3*Math.sin(i*0.11);}
  const r2=Float64Array.from(re), i2=Float64Array.from(im); fftN(r2,i2,false);
  let err=0; for(const k of [0,1,7,600,959,1919]){ let sr=0,si=0; for(let j=0;j<n;j++){const a=-2*Math.PI*j*k/n; sr+=re[j]*Math.cos(a)-im[j]*Math.sin(a); si+=re[j]*Math.sin(a)+im[j]*Math.cos(a);} err=Math.max(err,Math.hypot(sr-r2[k],si-i2[k])/Math.hypot(sr,si)); }
  const r3=Float64Array.from(r2), i3=Float64Array.from(i2); fftN(r3,i3,true); let e2=0; for(let j=0;j<n;j++) e2=Math.max(e2,Math.abs(r3[j]-re[j]),Math.abs(i3[j]-im[j]));
  OUT.push(`fftN 1920: max relative error ${err.toExponential(1)}, inverse round-trip ${e2.toExponential(1)}`);
  // 2) loop design
  const h=toneLoopHB(); const plain=toneLoop(false);
  OUT.push(`hum band loop: crest ${h.crest.toFixed(2)}, hum share ${(100*h.pilotShare).toFixed(0)}%, map tone ${(20*Math.log10(Math.hypot(h.X.re[80],h.X.im[80])/1920*2/(Math.hypot(plain.X.re[128],plain.X.im[128])/2048*2))).toFixed(1)} dB vs Quiet tones, peak ${Math.max(...h.x.map(Math.abs)).toFixed(3)}`);
  // 3) tracker on the synthetic recording
  const x=new XMLHttpRequest(); x.open('GET','hb_synth.wav',false); x.overrideMimeType('text/plain; charset=x-user-defined'); x.send();
  const str=x.responseText, buf=new Uint8Array(str.length); for(let i=0;i<str.length;i++) buf[i]=str.charCodeAt(i)&255;
  const f32=new Float32Array(buf.buffer.slice(44)), N=f32.length/2;
  ptReset(); const L=(HS_J+1)*HB_P, ser=[];
  for(let fr=L; fr<=N; fr+=3840){ hbTrack(f32.subarray(2*(fr-L),2*fr),L,fr,abs=>abs); if(PT&&PT.last) ser.push([fr/48000,1000*PT.cum]); }
  const at=(a,b)=>{const v=ser.filter(s=>s[0]>=a&&s[0]<b).map(s=>s[1]); return v.reduce((p,q)=>p+q,0)/v.length;};
  OUT.push(`hum-band tracker on simulated 25 cm move: ${((at(10.5,12.1)-at(2.5,3.6))/10).toFixed(1)} cm (truth -25.0)`);
}catch(e){ERR.push(e.message+' '+e.stack)}
document.body.insertAdjacentHTML('beforeend','<pre id=R>RESULT\n'+OUT.join('\n')+'\nerrors='+JSON.stringify(ERR)+'</pre>');
