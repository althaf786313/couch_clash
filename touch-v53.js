/* v5.3: real touch paths (direct element Touch Events) + click pulse. */
const fs=require('fs'); const {JSDOM,VirtualConsole}=require('jsdom');
const html=fs.readFileSync('/home/user/couch-clash/index.html','utf8');
function c(){return new Proxy({},{get(o,k){if(k in o)return o[k];
 if(['createLinearGradient','createRadialGradient','createPattern'].includes(k))return()=>({addColorStop(){}});
 if(k==='measureText')return()=>({width:10});return()=>{};},set(o,k,v){o[k]=v;return true;}})}
class ES{constructor(){this.onmessage=null;ES.last=this;}emit(o){if(this.onmessage)this.onmessage({data:JSON.stringify(o)});}close(){}}
function run(opts){opts=opts||{};const errors=[],hits=[];
 const vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(String(e.stack||e.message)));
 vc.on('error',(...a)=>errors.push('console.error: '+a.join(' ')));
 const RECT=opts.rect||{width:900,height:600,left:0,top:0,right:900,bottom:600};
 const dom=new JSDOM(html,{runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc,
  url:'https://x.e2b.app/',beforeParse(w){
   w.HTMLCanvasElement.prototype.getContext=()=>c();
   w.HTMLElement.prototype.getBoundingClientRect=function(){
    if(this.id==='steerWheel')return{width:120,height:120,left:20,top:400,right:140,bottom:520};
    return RECT;};
   w.matchMedia=()=>({matches:false,addEventListener(){}});
   w.AudioContext=class{constructor(){this.currentTime=0;this.destination={};}createGain(){return{gain:{value:0,setValueAtTime(){}}};}createOscillator(){return{frequency:{value:0,setValueAtTime(){}},connect(){},start(){},stop(){}};}resume(){}};
   w.EventSource=ES;
   w.fetch=(p,cfg)=>{const b=cfg&&cfg.body?JSON.parse(cfg.body):{};hits.push({p,b});
    return Promise.resolve({json:async()=>String(p).endsWith('/api/room')?{code:'K7R2',token:'t',role:'host',options:{bestOf:3,roundSeconds:60}}:{ok:true},ok:true});};
   w.requestAnimationFrame=cb=>{w.__raf=cb;return 1;};w.cancelAnimationFrame=()=>{};
   w.HTMLElement.prototype.requestFullscreen=()=>Promise.resolve();
   w.document.exitFullscreen=()=>Promise.resolve();
   w.document.elementFromPoint=()=>{throw new Error('elementFromPoint must NOT be used');};
   if(opts.noPointer)Object.defineProperty(w,'PointerEvent',{value:undefined,configurable:true});
   if(opts.blockStorage)Object.defineProperty(w,'localStorage',{configurable:true,
     get(){throw new w.DOMException('insecure','SecurityError');}});
  }});return {dom,errors,hits};}
function ok(c,m){if(!c){console.error('FAIL:',m);process.exitCode=1;}else console.log('  ok',m);}
function eq(a,b,m){ok(a===b,m+' | got '+JSON.stringify(a));}
function ev(win,type,props){const e=new win.Event(type,{bubbles:true,cancelable:true});
 for(const k in props)Object.defineProperty(e,k,{value:props[k]});return e;}
function touch(win,el,type,list){el.dispatchEvent(ev(win,type,{changedTouches:list}));}
function ptr(win,el,type,x,id){el.dispatchEvent(ev(win,type,{pointerId:id||7,clientX:x||0}));}
async function online(win,doc){[...doc.querySelectorAll('#modeSeg .mode-card')].find(c=>c.dataset.mode==='online').click();
 doc.getElementById('startBtn').click();await new Promise(r=>setTimeout(r,80));
 ES.last.emit({type:'hello',code:'K7R2',role:'host',both:true,peerConnected:true,started:true,
  options:{bestOf:3,roundSeconds:60},skins:['silver84','redfang'],layout:'woven',sync:null});}

(async()=>{
 for(const blocked of [false,true]){
  const {dom,errors}=run({blockStorage:blocked});
  await new Promise(r=>setTimeout(r,150));
  eq(errors.length,0,(blocked?'SANDBOXED':'NORMAL')+' startup clean');
  eq(dom.window.document.getElementById('fatal').style.display,'none','no fatal banner');
  dom.window.close();
 }

 console.log('\n=== DIRECT TOUCH ON PEDALS ===');
 {
  const {dom,errors,hits}=run({noPointer:true});
  const win=dom.window,doc=win.document,q=id=>doc.getElementById(id);
  await online(win,doc);hits.length=0;
  const T=id=>({identifier:id,clientX:300,clientY:470});
  touch(win,q('gasBtn'),'touchstart',[T(1)]);
  ok(hits.some(h=>String(h.p).endsWith('/api/input')&&h.b.input.throttle===1),'touchstart on GAS = throttle 1');
  ok(q('gasBtn').classList.contains('held'),'GAS shows held state');
  touch(win,q('gasBtn'),'touchend',[T(1)]);
  ok(hits.some(h=>String(h.p).endsWith('/api/input')&&h.b.input.throttle===0),'touchend releases GAS');
  eq(errors.length,0,'no errors (elementFromPoint never called)');
  dom.window.close();
 }

 console.log('\n=== DIRECT TOUCH DRAG ON WHEEL ===');
 {
  const {dom,errors,hits}=run({noPointer:true});
  const win=dom.window,doc=win.document,q=id=>doc.getElementById(id);
  await online(win,doc);hits.length=0;
  const T=(id,x)=>({identifier:id,clientX:x,clientY:460});
  touch(win,q('wheelRing'),'touchstart',[T(2,140)]);   // starts on the INNER RING
  eq(q('game').dataset.steer,'1.00','touch on inner ring steers right');
  touch(win,q('steerWheel'),'touchmove',[T(2,32)]);    // finger moves off the ring
  eq(q('game').dataset.steer,'-1.00','touchmove outside wheel still steers left');
  touch(win,q('steerWheel'),'touchend',[T(2,32)]);
  ok(hits.some(h=>String(h.p).endsWith('/api/input')&&h.b.input.steer===-1),'steer was POSTed');
  eq(errors.length,0,'no errors in wheel touch drag');
  dom.window.close();
 }

 console.log('\n=== CLICK PULSE (pointer + touch both broken) ===');
 {
  const {dom,errors,hits}=run({noPointer:true});
  const win=dom.window,doc=win.document,q=id=>doc.getElementById(id);
  await online(win,doc);hits.length=0;
  q('gasBtn').click();
  ok(hits.some(h=>String(h.p).endsWith('/api/input')&&h.b.input.throttle===1),'plain click gives a GAS pulse');
  await new Promise(r=>setTimeout(r,380));
  ok(hits.some(h=>String(h.p).endsWith('/api/input')&&h.b.input.throttle===0),'pulse auto-releases');
  hits.length=0;
  q('steerWheel').click();
  ok(Math.abs(parseFloat(q('game').dataset.steer))>0.5,'plain click on wheel steers');
  eq(errors.length,0,'no errors in click fallback');
  dom.window.close();
 }

 console.log('\n=== POINTER PATH + PORTRAIT + FULLSCREEN REGRESSION ===');
 {
  const {dom,errors,hits}=run({rect:{width:400,height:820,left:0,top:0,right:400,bottom:820}});
  const win=dom.window,doc=win.document,q=id=>doc.getElementById(id);
  await new Promise(r=>setTimeout(r,150));
  ok(!q('rotateGate').classList.contains('hidden'),'chooser shown in portrait');
  q('startBtn').click();
  ok(q('rotateGate').classList.contains('hidden'),'chooser hidden once match starts');
  let t=1000;for(let i=0;i<600;i++){win.__raf(t);t+=16;}
  ok(parseFloat(q('timer').textContent)<60,'timer counts down in portrait');
  ptr(win,q('steerWheel'),'pointerdown',140,9);
  eq(q('game').dataset.steer,'1.00','pointer wheel still works');
  ptr(win,win,'pointerup',140,9);
  ptr(win,q('gasBtn'),'pointerdown',0,10);
  ok(q('gasBtn').classList.contains('held'),'pointer GAS still works');
  ptr(win,q('gasBtn'),'pointerup',0,10);
  q('chooseFullscreen').click();
  ok(!doc.body.classList.contains('world-rotated'),'rotation OFF by default in fullscreen');
  q('rotateHudBtn').click();
  ok(doc.body.classList.contains('world-rotated'),'rotation toggle works');
  eq(errors.length,0,'no errors in portrait regression');
  dom.window.close();
 }

 console.log('\n=== v5 FEATURES REGRESSION ===');
 {
  const {dom,errors,hits}=run({});const win=dom.window,doc=win.document,q=id=>doc.getElementById(id);
  await new Promise(r=>setTimeout(r,150));
  q('couchBtn').click();eq(q('couchGrid').querySelectorAll('.couch-card').length,4,'four couches');
  q('couchBackBtn').click();q('garageBtn').click();
  eq(q('garageGrid').querySelectorAll('.car-card').length,6,'six cars');
  q('garageBackBtn').click();
  [...doc.querySelectorAll('#modeSeg .mode-card')].find(c=>c.dataset.mode==='online').click();
  q('startBtn').click();await new Promise(r=>setTimeout(r,80));
  const room=hits.find(h=>String(h.p).endsWith('/api/room'));
  ok(room&&room.b.layoutId&&room.b.carId,'room carries layout + car');
  eq(errors.length,0,'no errors in feature regression');
  dom.window.close();
 }

 console.log('\n'+(process.exitCode?'SOME V5.3 CHECKS FAILED':'ALL V5.3 CHECKS PASSED'));
 process.exit(process.exitCode||0);
})();
