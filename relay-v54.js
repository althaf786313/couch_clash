/* v5.4: relay-aware client. No-relay pages explain themselves; ?relay= works. */
const fs=require('fs'); const {JSDOM,VirtualConsole}=require('jsdom');
const html=fs.readFileSync('/home/user/couch-clash/index.html','utf8');
function c(){return new Proxy({},{get(o,k){if(k in o)return o[k];
 if(['createLinearGradient','createRadialGradient','createPattern'].includes(k))return()=>({addColorStop(){}});
 if(k==='measureText')return()=>({width:10});return()=>{};},set(o,k,v){o[k]=v;return true;}})}
class ES{constructor(u){this.url=u;this.onmessage=null;ES.last=this;}emit(o){if(this.onmessage)this.onmessage({data:JSON.stringify(o)});}close(){}}
function run(o){o=o||{};const errors=[],hits=[];
 const vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(String(e.stack||e.message)));
 vc.on('error',(...a)=>errors.push('console.error: '+a.join(' ')));
 const RECT={width:900,height:600,left:0,top:0,right:900,bottom:600};
 const dom=new JSDOM(html,{runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc,
  url:o.url||'https://game.example.com/',beforeParse(w){
   w.HTMLCanvasElement.prototype.getContext=()=>c();
   w.HTMLElement.prototype.getBoundingClientRect=function(){
    if(this.id==='steerWheel')return{width:120,height:120,left:20,top:400,right:140,bottom:520};
    return RECT;};
   w.matchMedia=()=>({matches:false,addEventListener(){}});
   w.AudioContext=class{constructor(){this.currentTime=0;this.destination={};}createGain(){return{gain:{value:0,setValueAtTime(){}}};}createOscillator(){return{frequency:{value:0,setValueAtTime(){}},connect(){},start(){},stop(){}};}resume(){}};
   w.EventSource=ES;
   w.fetch=o.fetchImpl || ((p,cfg)=>{
    const b=cfg&&cfg.body?JSON.parse(cfg.body):{};hits.push({p,b});
    if(o.rejectAll) return Promise.reject(new Error('no relay on a static host'));
    if(o.onlyRelay && !String(p).startsWith(o.onlyRelay)) return Promise.reject(new Error('wrong origin'));
    return Promise.resolve({ok:true,json:async()=>String(p).includes('/api/room')
      ?{code:'K7R2',token:'t',role:'host',options:{bestOf:3,roundSeconds:60}}
      :{ok:true}});
   });
   w.requestAnimationFrame=cb=>{w.__raf=cb;return 1;};w.cancelAnimationFrame=()=>{};
   w.HTMLElement.prototype.requestFullscreen=()=>Promise.resolve();
   w.document.exitFullscreen=()=>Promise.resolve();
   w.document.elementFromPoint=()=>{throw new Error('elementFromPoint must NOT be used');};
  }});return{dom,errors,hits};}
function ok(c,m){if(!c){console.error('FAIL:',m);process.exitCode=1;}else console.log('  ok',m);}
function eq(a,b,m){ok(a===b,m+' | got '+JSON.stringify(a));}
function pickOnline(d){
 [...d.querySelectorAll('#modeSeg .mode-card')].find(c=>c.dataset.mode==='online').click();
 return s=>d.querySelector(s);}
(async()=>{
 console.log('=== A. same-origin server build (no regression) ===');
 {const {dom,errors,hits}=run();const w=dom.window,d=w.document,q=s=>d.querySelector(s);
  await new Promise(r=>setTimeout(r,160));
  eq(errors.length,0,'startup clean');
  ok(q('#relayRow').classList.contains('collapsed'),'relay row stays collapsed when healthy');
  ok(q('#liveBadge').textContent.includes('LIVE SERVER'),'badge says LIVE SERVER');
  await pickOnline(d);hits.length=0;
  d.getElementById('startBtn').click();await new Promise(r=>setTimeout(r,120));
  ok(hits.some(h=>h.p==='https://game.example.com/api/room'),'create room POSTs to own origin');
  eq(d.getElementById('lobby').classList.contains('hidden'),false,'lobby opens');
  ok(ES.last && ES.last.url.startsWith('https://game.example.com/api/events'),'EventSource on own origin');
  eq(errors.length,0,'no errors');dom.window.close();}

 console.log('=== B. STATIC page with NO relay (the reported bug) ===');
 {const {dom,errors}=run({rejectAll:true});const w=dom.window,d=w.document,q=s=>d.querySelector(s);
  await new Promise(r=>setTimeout(r,160));
  eq(errors.length,0,'startup clean with no server');
  eq(q('#fatal').style.display,'none','no fatal banner');
  ok(!q('#relayRow').classList.contains('collapsed'),'relay panel AUTO-OPENS');
  ok(q('#relayStatus').textContent.includes('NO RELAY'),'status explains NO RELAY');
  ok(q('#relayHelp').textContent.includes('no /api/* relay'),'help explains the missing relay');
  ok(q('#liveBadge').textContent.includes('NO RELAY'),'corner badge says NO RELAY');
  await pickOnline(d);
  d.getElementById('startBtn').click();await new Promise(r=>setTimeout(r,120));
  const t=q('#toast').textContent;
  ok(t.includes('RELAY'),'error toast points at ⚙ RELAY, not a vague message: '+JSON.stringify(t));
  ok(!t.includes('Are you on the live preview'),'old vague toast is gone');
  ok(!q('#relayRow').classList.contains('collapsed'),'failed create keeps the fix visible');
  ok(q('#relayStatus').textContent.includes('FAILED'),'failure reason recorded');
  eq(errors.length,0,'no errors');dom.window.close();}

 console.log('=== C. ?relay= override: static page reaches the live server ===');
 {const R='https://relay.example.com';
  const {dom,errors,hits}=run({url:'https://static.example.com/?relay='+encodeURIComponent(R),onlyRelay:R});
  const w=dom.window,d=w.document,q=s=>d.querySelector(s);
  await new Promise(r=>setTimeout(r,160));
  eq(errors.length,0,'startup clean');
  ok(q('#relayStatus').textContent.includes('RELAY OK'),'probe found the external relay');
  ok(q('#relayInput').value===R,'relay input prefilled from ?relay=');
  await pickOnline(d);hits.length=0;
  d.getElementById('startBtn').click();await new Promise(r=>setTimeout(r,120));
  ok(hits.some(h=>h.p===R+'/api/room'),'CREATE ROOM POSTs to the external relay');
  ok(ES.last && ES.last.url.startsWith(R+'/api/events'),'EventSource uses external relay');
  ok(d.getElementById('qrImg').src.startsWith(R+'/api/qr'),'QR uses external relay');
  ok(d.getElementById('inviteInput').value.startsWith(R+'/?room='),'invite sends friend to the relay page');
  eq(errors.length,0,'no errors');dom.window.close();}

 console.log('=== D. USE button repairs a broken page live ===');
 {const R='https://relay.example.com';let mode='dead';const hits=[];
  // Custom fetch installed BEFORE scripts run: dead until USE is clicked.
  const {dom,errors}=run({url:'https://static.example.com/',fetchImpl:(p,cfg)=>{
    hits.push({p});
    if(mode==='dead') return Promise.reject(new Error('404 HTML'));
    return Promise.resolve({ok:true,json:async()=>String(p).includes('/api/health')
      ?{ok:true}:{code:'K7R2',token:'t',role:'host',options:{bestOf:3,roundSeconds:60}}});
  }});
  const w=dom.window,d=w.document,q=s=>d.querySelector(s);
  await new Promise(r=>setTimeout(r,160));
  ok(q('#relayStatus').textContent.includes('NO RELAY'),'starts broken');
  mode='live';
  q('#relayInput').value=R;q('#relaySaveBtn').click();
  await new Promise(r=>setTimeout(r,120));
  ok(q('#relayStatus').textContent.includes('RELAY OK'),'USE button connects the relay');
  ok(q('#liveBadge').textContent.includes('LIVE SERVER'),'badge updates');
  await pickOnline(d);
  d.getElementById('startBtn').click();await new Promise(r=>setTimeout(r,120));
  ok(hits.some(h=>String(h.p)===R+'/api/room'),'CREATE ROOM now works');
  eq(errors.length,0,'no errors');dom.window.close();}

 console.log('\n'+(process.exitCode?'SOME RELAY CHECKS FAILED':'ALL RELAY CHECKS PASSED'));
 process.exit(process.exitCode||0);
})();
