/* Single-file static build: starts clean with NO server, solo play works,
   and TWO PHONES explains how to attach a relay instead of silently failing. */
const fs=require('fs'); const {JSDOM,VirtualConsole}=require('jsdom');
const html=fs.readFileSync('/home/user/couch-clash/CouchClash-static.html','utf8');
function c(){return new Proxy({},{get(o,k){if(k in o)return o[k];
 if(['createLinearGradient','createRadialGradient','createPattern'].includes(k))return()=>({addColorStop(){}});
 if(k==='measureText')return()=>({width:10});return()=>{};},set(o,k,v){o[k]=v;return true;}})}
const errors=[];
const vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(String(e.stack||e.message)));
const dom=new JSDOM(html,{runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc,
 url:'https://example.com/',beforeParse(w){
  w.HTMLCanvasElement.prototype.getContext=()=>c();
  w.HTMLElement.prototype.getBoundingClientRect=function(){
   if(this.id==='steerWheel')return{width:120,height:120,left:20,top:400,right:140,bottom:520};
   return{width:900,height:600,left:0,top:0,right:900,bottom:600};};
  w.matchMedia=()=>({matches:false,addEventListener(){}});
  w.AudioContext=class{constructor(){this.currentTime=0;this.destination={};}createGain(){return{gain:{value:0,setValueAtTime(){}}};}createOscillator(){return{frequency:{value:0,setValueAtTime(){}},connect(){},start(){},stop(){}};}resume(){}};
  w.EventSource=class{constructor(){this.onmessage=null;}close(){}};
  w.fetch=()=>Promise.reject(new Error('no relay on a static host'));
  w.requestAnimationFrame=cb=>{w.__raf=cb;return 1;};w.cancelAnimationFrame=()=>{};
  w.HTMLElement.prototype.requestFullscreen=()=>Promise.resolve();
  w.document.exitFullscreen=()=>Promise.resolve();
 }});
function ok(c,m){if(!c){console.error('FAIL:',m);process.exitCode=1;}else console.log('  ok',m);}
(async()=>{
 await new Promise(r=>setTimeout(r,180));
 const w=dom.window,d=w.document,q=id=>d.getElementById(id);
 ok(errors.length===0,'startup clean with no server ('+errors.length+' errors)');
 ok(q('fatal').style.display==='none','no fatal banner');
 ok(q('liveBadge').textContent.includes('NO RELAY'),'badge says NO RELAY');
 ok(!q('relayRow').classList.contains('collapsed'),'relay panel auto-opens');
 ok(d.querySelector('#modeSeg .mode-card[data-mode="online"]'),'TWO PHONES still available via relay');
 ok(q('relayHelp').textContent.includes('no /api/* relay'),'explains the missing relay');
 ok(!!d.querySelector('.static-note'),'single-file note visible');
 q('startBtn').click();
 let t=1000;for(let i=0;i<600;i++){w.__raf(t);t+=16;}
 ok(parseFloat(q('timer').textContent)<60,'SOLO match runs, timer counts down');
 q('gasBtn').dispatchEvent(new w.Event('click',{bubbles:true}));
 ok(q('gasBtn').classList.contains('held'),'controls respond without a server');
 ok(errors.length===0,'no runtime errors after 600 frames');
 console.log(process.exitCode?'STATIC CHECKS FAILED':'ALL STATIC BUILD CHECKS PASSED');
 dom.window.close();process.exit(process.exitCode||0);
})();
