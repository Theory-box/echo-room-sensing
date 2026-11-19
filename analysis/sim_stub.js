window.ERR=[];window.onerror=(m,u,l)=>{ERR.push(m+' @'+l)};
const SIM={GT:0,PLAY:null,PER:0,off0:300.0,refl:[],noise:0.0005,direct:[1,0.3],lag2:4,seed:7,saved:[],adv:null};
function rnd(){SIM.seed=(SIM.seed*16807)%2147483647;return SIM.seed/2147483647-0.5;}
function addF(out,L,ch,pos,g){ const n=SIM.PLAY.length, i0=Math.floor(pos), fr=pos-i0, w=[];
 for(let t=-6;t<=6;t++){const x=t-fr;const s=Math.abs(x)<1e-12?1:Math.sin(Math.PI*x)/(Math.PI*x);w.push(s*(0.5+0.5*Math.cos(Math.PI*x/7)));}
 for(let k=0;k<n;k++){const v=g*SIM.PLAY[k]; if(v===0)continue; for(let t=-6;t<=6;t++){const i=i0+k+t; if(i>=0&&i<L) out[2*i+ch]+=v*w[t+6];}}}
// finite walls (2026-11-18): a wall {c, D, lo, hi} only exists between tangent coordinates lo..hi (tangent = (cos c, -sin c));
// it answers if the foot of the perpendicular from the phone lies on it and nothing else blocks the way
function simSeen(w,dd,th){ const ph=[dd[0]+0.25*Math.sin(th*Math.PI/180), dd[1]+0.25*Math.cos(th*Math.PI/180)];
 const n=[Math.sin(w.c*Math.PI/180),Math.cos(w.c*Math.PI/180)], t=[Math.cos(w.c*Math.PI/180),-Math.sin(w.c*Math.PI/180)];
 const k=w.D-(n[0]*ph[0]+n[1]*ph[1]); if(k<=0) return false; const f=[ph[0]+k*n[0], ph[1]+k*n[1]], s=t[0]*f[0]+t[1]*f[1];
 if(s<w.lo||s>w.hi) return false;
 for(const o of SIM.walls){ if(o===w||o.lo===undefined) continue; const no=[Math.sin(o.c*Math.PI/180),Math.cos(o.c*Math.PI/180)], to=[Math.cos(o.c*Math.PI/180),-Math.sin(o.c*Math.PI/180)];
   const den=no[0]*(f[0]-ph[0])+no[1]*(f[1]-ph[1]); if(Math.abs(den)<1e-9) continue; const lam=(o.D-(no[0]*ph[0]+no[1]*ph[1]))/den; if(lam<=0.02||lam>=0.98) continue;
   const q=[ph[0]+lam*(f[0]-ph[0]), ph[1]+lam*(f[1]-ph[1])], so=to[0]*q[0]+to[1]*q[1]; if(so>=o.lo&&so<=o.hi) return false; }
 return true; }
function synth(L){ const out=new Float32Array(2*L), start=SIM.GT-L, P=SIM.PER, n=SIM.PLAY.length;
 for(let m=Math.floor((start-n-2*P)/P); m*P+SIM.off0 < SIM.GT; m++){ const te=m*P+SIM.off0; if(te+n+2*P < start) continue;
   const pos=te-start, ts=te/48000;
   addF(out,L,0,pos,SIM.direct[0]); addF(out,L,1,pos+SIM.lag2,SIM.direct[1]);
   const h=(x)=>{let v=Math.sin(x*12.9898+78.233)*43758.5453;return v-Math.floor(v);};for(const [ri,r] of SIM.refl.entries()){ if(SIM.drop && h(m*7+ri)<SIM.drop) continue; const R=r.r0-r.v*ts, dl=2*R/343*48000; addF(out,L,0,pos+dl,r.g); addF(out,L,1,pos+dl+(r.l2||10),r.g*0.8);}if(SIM.walls){const th=SIM.yawF(ts);for(const [wi,w] of SIM.walls.entries()){let rel=((w.c-th)%360+540)%360-180; if(Math.abs(rel)>60 && !w.omni) continue; if(SIM.drop && h(m*11+wi*3)<SIM.drop) continue; const cr=Math.cos(rel*Math.PI/180), dd=SIM.posF?SIM.posF(ts):[0,0], R=w.D-0.25*cr-(dd[0]*Math.sin(w.c*Math.PI/180)+dd[1]*Math.cos(w.c*Math.PI/180)), dl=2*R/343*48000, g=w.omni?w.g:w.g*cr**4; if(w.lo!==undefined && !simSeen(w,dd,th)) continue; addF(out,L,0,pos+dl,g); addF(out,L,1,pos+dl+10,g*0.8);}} if(SIM.junk && h(m*3.1)<SIM.junk){ const R=0.6+3.8*h(m*5.7), dl=2*R/343*48000; addF(out,L,0,pos+dl,0.03); addF(out,L,1,pos+dl+5,0.02);} }
 for(let i=0;i<out.length;i++) out[i]+=SIM.noise*rnd()*3.46;
 return out;}
function b64_(f){const u=new Uint8Array(f.buffer);let s='';for(let i=0;i<u.length;i+=0x8000)s+=String.fromCharCode.apply(null,u.subarray(i,i+0x8000));return btoa(s);}
function unb64_(b){const bin=atob(b),u=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);return new Float32Array(u.buffer);}
window.Native={hasMicPermission:()=>true,sonarStart:(b,loop,sr)=>{SIM.PLAY=unb64_(b);SIM.PER=loop;return 'ok';},sonarStop(){},sonarRestoreVolume(){},setReversed(){},
 orientation:()=>JSON.stringify({yaw:0,gyro:0,g:[0,0,9.8]}),
 sonarReadBoth:(L)=>{SIM.GT+=SIM.adv?SIM.adv():SIM.PER;return SIM.GT+'|'+b64_(synth(L));},newSession:()=>'s',saveSessionText:(f,t)=>{SIM.saved.push(t);return 'ok';}};
