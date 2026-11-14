"use strict";
// Shared DSP core: used by diagnostic/index.html (web) and the Android app (android/).
// ---------- DSP core (pure functions) ----------
function fft(re, im, inv){
  const n = re.length;
  for (let i=1,j=0;i<n;i++){ let bit=n>>1; for(;j&bit;bit>>=1) j^=bit; j^=bit;
    if(i<j){ let t=re[i]; re[i]=re[j]; re[j]=t; t=im[i]; im[i]=im[j]; im[j]=t; } }
  for (let len=2; len<=n; len<<=1){
    const ang = 2*Math.PI/len*(inv?1:-1), half=len>>1;
    const wr=Math.cos(ang), wi=Math.sin(ang);
    for (let i=0;i<n;i+=len){ let cr=1, ci=0;
      for (let j=0;j<half;j++){ const a=i+j, b=a+half;
        const xr=re[b]*cr-im[b]*ci, xi=re[b]*ci+im[b]*cr;
        re[b]=re[a]-xr; im[b]=im[a]-xi; re[a]+=xr; im[a]+=xi;
        const t=cr*wr-ci*wi; ci=cr*wi+ci*wr; cr=t; } } }
  if (inv) for (let i=0;i<n;i++){ re[i]/=n; im[i]/=n; }
}
// corr[k] = sum_n x[n+k]*t[n], k = 0..x.length-1
function xcorr(x, t){
  let N=1; while (N < x.length + t.length) N<<=1;
  const ar=new Float64Array(N), ai=new Float64Array(N), br=new Float64Array(N), bi=new Float64Array(N);
  ar.set(x); br.set(t); fft(ar,ai,false); fft(br,bi,false);
  for (let i=0;i<N;i++){ const r=ar[i]*br[i]+ai[i]*bi[i], m=ai[i]*br[i]-ar[i]*bi[i]; ar[i]=r; ai[i]=m; }
  fft(ar,ai,true);
  return ar.slice(0, x.length);
}
function rms(a, s=0, e=a.length){ let q=0; s=Math.max(0,s); e=Math.min(a.length,e); for(let i=s;i<e;i++) q+=a[i]*a[i]; return Math.sqrt(q/Math.max(1,e-s)); }
const db = v => 20*Math.log10(Math.max(v,1e-12));
function median(a){ const b=Array.from(a).sort((x,y)=>x-y); return b[b.length>>1]; }
function parabolic(a,i){ if(i<=0||i>=a.length-1) return i; const y0=a[i-1],y1=a[i],y2=a[i+1], d=y0-2*y1+y2; return d===0?i:i+0.5*(y0-y2)/d; }
function argmax(a,s=0,e=a.length){ let bi=s, bv=-Infinity; for(let i=s;i<e;i++) if(a[i]>bv){bv=a[i];bi=i;} return bi; }

// Signal generators. Returns {I,Q} with window w.
function linChirp(sr, f0, f1, T, taper){
  const n=Math.round(T*sr), I=new Float32Array(n), Q=new Float32Array(n);
  for(let i=0;i<n;i++){ const t=i/sr, ph=2*Math.PI*(f0*t+(f1-f0)*t*t/(2*T));
    let w; if(taper==='hann') w=0.5-0.5*Math.cos(2*Math.PI*i/(n-1));
    else { const r=0.1*n; w = i<r ? 0.5-0.5*Math.cos(Math.PI*i/r) : i>n-1-r ? 0.5-0.5*Math.cos(Math.PI*(n-1-i)/r) : 1; }
    I[i]=w*Math.cos(ph); Q[i]=w*Math.sin(ph); }
  return {I,Q};
}
function logSweepPhase(t, f1, f2, T){ const K=Math.log(f2/f1); return 2*Math.PI*f1*T/K*(Math.exp(t*K/T)-1); }
function logSweep(sr, f1, f2, T){
  const n=Math.round(T*sr), s=new Float32Array(n), fade=Math.round(0.01*sr);
  for(let i=0;i<n;i++){ let w=1; if(i<fade) w=0.5-0.5*Math.cos(Math.PI*i/fade); else if(i>n-1-fade) w=0.5-0.5*Math.cos(Math.PI*(n-1-i)/fade);
    s[i]=w*Math.sin(logSweepPhase(i/sr,f1,f2,T)); }
  return s;
}

// Test plan (times in seconds from buffer start)
function makePlan(sr){
  const S = x=>Math.round(x*sr);
  const P = { sr, A:0.4, total:S(12.0),
    sweep:{ start:S(1.0), f1:50, f2:23500, T:3.0 },
    chirpA:{ f0:1000, f1:18000, T:0.06, L:[0,1,2,3].map(k=>S(4.5)+k*S(0.3)), R:[0,1,2,3].map(k=>S(6.0)+k*S(0.3)) },
    us:{ f0:18000, f1:22000, T:0.04, starts:Array.from({length:16},(_,k)=>S(7.5)+k*S(0.25)) } };
  P.sweepSig = logSweep(sr, P.sweep.f1, P.sweep.f2, P.sweep.T);
  P.chirpSig = linChirp(sr, P.chirpA.f0, P.chirpA.f1, P.chirpA.T, 'tukey');
  P.usSig = linChirp(sr, P.us.f0, P.us.f1, P.us.T, 'hann');
  return P;
}
function buildPlayback(P){
  const L=new Float32Array(P.total), R=new Float32Array(P.total);
  const put=(dst,sig,at)=>{ for(let i=0;i<sig.length&&at+i<dst.length;i++) dst[at+i]+=P.A*sig[i]; };
  put(L,P.sweepSig,P.sweep.start); put(R,P.sweepSig,P.sweep.start);
  P.chirpA.L.forEach(s=>put(L,P.chirpSig.I,s));
  P.chirpA.R.forEach(s=>put(R,P.chirpSig.I,s));
  P.us.starts.forEach(s=>{ put(L,P.usSig.I,s); put(R,P.usSig.I,s); });
  return {L,R};
}

// Coherent-average segments then I/Q matched filter -> envelope
function profile(ch, starts, offset, sig, pre, winLen){
  const avg=new Float64Array(winLen); let cnt=0;
  for(const s of starts){ const b=offset+s-pre; if(b<0||b+winLen>ch.length) continue; for(let i=0;i<winLen;i++) avg[i]+=ch[b+i]; cnt++; }
  if(!cnt) return null;
  for(let i=0;i<winLen;i++) avg[i]/=cnt;
  const ci=xcorr(avg,sig.I), cq=xcorr(avg,sig.Q), env=new Float64Array(winLen);
  for(let i=0;i<winLen;i++) env[i]=Math.hypot(ci[i],cq[i]);
  return env;
}
function echoes(env, sr, p0, noise, maxN=6){
  const out=[], skip=Math.round(0.0015*sr), k=5, floor=env[Math.round(p0)]*0.0056; // -45 dB
  for(let i=Math.round(p0)+skip;i<env.length-k;i++){
    let pk=true; for(let j=1;j<=k;j++) if(env[i]<env[i-j]||env[i]<env[i+j]){pk=false;break;}
    if(pk && env[i]>4*noise && env[i]>floor) out.push(i);
  }
  out.sort((a,b)=>env[b]-env[a]);
  return out.slice(0,maxN).sort((a,b)=>a-b).map(i=>({ m:+((i-p0)/sr*343/2).toFixed(3), dB:+db(env[i]/env[Math.round(p0)]).toFixed(1) }));
}

function analyze(ch0, ch1, P){
  const sr=P.sr, R={};
  const S = x=>Math.round(x*sr);
  const mix = ch0.map((v,i)=>v+(ch1?ch1[i]:0));
  // 1. alignment via sweep
  const seg = mix.subarray ? mix.subarray(0, Math.min(mix.length, S(6.5))) : mix.slice(0,S(6.5));
  const c = xcorr(seg, P.sweepSig);
  const ca = c.map(Math.abs), p = argmax(ca);
  const offset = p - P.sweep.start;
  R.offsetSamples = offset; R.alignConf = +(ca[p]/(median(ca)+1e-12)).toFixed(1);
  // 2. levels
  const nb = offset + S(0.1), ne = offset + S(0.9);
  const chans = ch1 ? [ch0,ch1] : [ch0];
  R.noiseFloor_dBFS = chans.map(ch=>+db(rms(ch,nb,ne)).toFixed(1));
  R.clippedSamples = chans.map(ch=>{ let n=0; for(const v of ch) if(Math.abs(v)>0.99) n++; return n; });
  // 3. channel identity during sweep
  const sb=offset+P.sweep.start, se=sb+S(P.sweep.T);
  if(ch1){
    // use the left-speaker-only chirp section: asymmetric, so two real mics must differ
    const cb=offset+P.chirpA.L[0], ce=offset+P.chirpA.L[3]+S(0.25);
    const r0=rms(ch0,cb,ce), r1=rms(ch1,cb,ce); let dot=0,d2=0;
    for(let i=cb;i<ce;i++){ dot+=ch0[i]*ch1[i]; d2+=(ch0[i]-ch1[i])**2; }
    const n=ce-cb, corr=dot/n/(r0*r1+1e-20), diff=Math.sqrt(d2/n)/(r0+1e-20);
    R.chanCorr=+corr.toFixed(5); R.chanDiffRatio=+diff.toFixed(4); R.ch1rel_dB=+db(r1/(r0+1e-20)).toFixed(1);
    R.channels = r1 < 1e-5 ? 'MONO (ch2 silent)' : (corr>0.9999 && diff<0.01) ? 'DUPLICATE (same mic twice)' : 'DISTINCT';
  } else R.channels='MONO (1 channel)';
  // 4. frequency response via demodulation at instantaneous sweep phase
  const freqs=[100,200,300,500,1000,2000,4000,8000,12000,16000,17000,18000,19000,20000,21000,22000,23000];
  const {f1,f2,T}=P.sweep, K=Math.log(f2/f1), W=S(0.02);
  R.freqResp_dB = {};
  for(const f of freqs){
    const tf=T*Math.log(f/f1)/K, nc=sb+Math.round(tf*sr);
    const vals = chans.map(ch=>{ let re=0,im=0,cnt=0;
      for(let n=Math.max(sb,nc-(W>>1)); n<Math.min(se,nc+(W>>1)); n++){ const ph=logSweepPhase((n-sb)/sr,f1,f2,T); re+=ch[n]*Math.cos(ph); im-=ch[n]*Math.sin(ph); cnt++; }
      return +db(2*Math.hypot(re,im)/Math.max(cnt,1)/P.A).toFixed(1); });
    R.freqResp_dB[f]=vals;
  }
  // 5. speaker x mic direct-path delays (audible chirp)
  const pre=S(0.002), win=S(0.12);
  R.delays={}; R.audibleEchoes={};
  for(const spk of ['L','R']){
    R.delays[spk]=chans.map((ch,mi)=>{
      const env=profile(ch, P.chirpA[spk], offset, P.chirpSig, pre, win); if(!env) return null;
      const pi=argmax(env,0,S(0.02)), pf=parabolic(env,pi);
      if(spk==='L'){ const nz=median(env.subarray(Math.round(win*0.75))); R.audibleEchoes['mic'+(mi+1)]=echoes(env,sr,pf,nz); }
      return +(pf-pre).toFixed(2);
    });
  }
  if(ch1 && R.delays.L[1]!=null && R.delays.R[1]!=null){
    const dL=R.delays.L[0]-R.delays.L[1], dR=R.delays.R[0]-R.delays.R[1];
    R.micTimeDiff_L_us=+(dL/sr*1e6).toFixed(1); R.micTimeDiff_R_us=+(dR/sr*1e6).toFixed(1);
    R.geometrySwing_samples=+(dL-dR).toFixed(2);
    R.geometrySwing_cm=+((dL-dR)/sr*34300).toFixed(1);
  }
  // 6. ultrasonic
  const upre=S(0.002), uwin=S(0.2);
  R.ultrasonic=chans.map(ch=>{
    const env=profile(ch, P.us.starts, offset, P.usSig, upre, uwin); if(!env) return null;
    const pi=argmax(env,0,S(0.02)), pf=parabolic(env,pi), nz=median(env.subarray(Math.round(uwin*0.75)));
    return { snr_dB:+db(env[pi]/(nz+1e-20)).toFixed(1), echoes:echoes(env,sr,pf,nz), _env:env, _p0:pf };
  });
  return R;
}
if (typeof module!=='undefined') module.exports={fft,xcorr,makePlan,buildPlayback,analyze};
