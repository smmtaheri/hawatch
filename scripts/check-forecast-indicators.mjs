// Native Chrome/CDP visual checks against a local API; never sends a write.
// Start Chrome with --remote-debugging-port=9416 and a separate temporary profile.
import fs from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import assert from 'node:assert/strict';
const base=process.env.HAWATCH_CHECK_ORIGIN||'http://127.0.0.1:5173';
assert(['127.0.0.1','localhost'].includes(new URL(base).hostname),'Use a local isolated stack');
const cdp=process.env.HAWATCH_CHECK_CDP||'http://127.0.0.1:9416';
const output='design/screens/forecast-indicators';
await fs.mkdir(output,{recursive:true});
const baseline='ba32388aae9748250d8ed05bb561b5c3a93bb493';
const previous=execFileSync('git',['show',baseline+':apps/web/src/features/week/vendor/charts.ts'],{encoding:'utf8'}).replace('export const charts','globalThis.previousCharts');
const week=await(await fetch(base+'/api/v1/points/tochal/forecast/week/')).json();
const results=[];
for(const device of ['desktop','mobile']){
 const width=device==='mobile'?430:1600,height=device==='mobile'?2250:1800;
 const target=await(await fetch(cdp+'/json/new?about:blank',{method:'PUT'})).json();
 const socket=new WebSocket(target.webSocketDebuggerUrl);
 await new Promise(resolve=>socket.addEventListener('open',resolve,{once:true}));
 let id=0,weatherGets=0,writesBlocked=0;const pending=new Map(),errors=[];
 const send=(method,params={})=>new Promise((resolve,reject)=>{const next=++id;pending.set(next,{resolve,reject});socket.send(JSON.stringify({id:next,method,params}));});
 socket.addEventListener('message',event=>{
  const v=JSON.parse(event.data);
  if(v.id){const p=pending.get(v.id);if(p){pending.delete(v.id);v.error?p.reject(new Error(v.error.message)):p.resolve(v.result);}}
  if(v.method==='Runtime.exceptionThrown')errors.push(v.params.exceptionDetails.text);
  if(v.method==='Fetch.requestPaused'){
   const {requestId,request}=v.params;
   const block=request.method!=='GET'||/google-analytics|googletagmanager|doubleclick|analytics\/pageview|forecast\/visit/.test(request.url);
   if(block)writesBlocked++;
   if(/forecast\/week/.test(request.url))weatherGets++;
   void send(block?'Fetch.fulfillRequest':'Fetch.continueRequest',block?{requestId,responseCode:204,body:''}:{requestId});
  }
 });
 const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
 const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
 const until=async expression=>{const end=Date.now()+30000;while(Date.now()<end){if(await evaluate(expression))return;await pause(100);}throw new Error('Timeout: '+expression);};
 await send('Page.enable');await send('Runtime.enable');await send('Fetch.enable',{patterns:[{urlPattern:'*',requestStage:'Request'}]});
 const win=await send('Browser.getWindowForTarget');
 const resize=async(w,h)=>{await send('Browser.setWindowBounds',{windowId:win.windowId,bounds:{width:w,height:h}});await send('Emulation.setDeviceMetricsOverride',{width:w,height:h,deviceScaleFactor:1,mobile:device==='mobile'});await send('Emulation.setVisibleSize',{width:w,height:h});await pause(200);};
 await resize(width,height);
 await send('Page.navigate',{url:base+'/points/tochal'});
 await until("Boolean(document.querySelector('[data-metric=\"felt\"]'))");
 assert.equal(weatherGets,1,'One initial weekly request');
 await evaluate(`globalThis.checkWeek=${JSON.stringify(week)};${previous}`);
 await evaluate("document.querySelector('[data-v4-expert]').click()");
 for(const step of [24,6,3,1]){
  if(step!==24)await evaluate("document.querySelector('[data-v4-expand=\"1\"]').click()");
  await pause(80);
  await evaluate(`(()=>{const s=document.querySelector('.timeline-scroll'),g=document.querySelectorAll('.day-group')[1];s.scrollLeft=${step}===24?s.scrollWidth-s.clientWidth:Number(g.dataset.left)+Number(g.dataset.width)/2-s.clientWidth/2;s.dispatchEvent(new Event('scroll'));window.scrollTo(0,0);document.activeElement?.blur()})()`);
  const evidence=await evaluate(`(()=>{
   const felt=document.querySelector('[data-metric="felt"]'),w=felt.viewBox.baseVal.width;
   const circles=[...felt.querySelectorAll('circle[data-point]')],xs=circles.map(e=>+e.getAttribute('cx'));
   const map={apparent_temperature_c:'felt',temperature_c:'actual',wind_speed_kmh:'wind',wind_gust_kmh:'gust',precipitation_mm:'rain',visibility_km:'visibility',heat_index_c:'heat_index_c'};
   const points=circles.map(e=>{const [,date,res,index]=e.dataset.point.match(/^(\\d{4}-\\d{2}-\\d{2})-(daily|6h|3h|1h)-(\\d+)$/),n={daily:24,'6h':6,'3h':3,'1h':1}[res],di=checkWeek.days.findIndex(d=>d.date===date),p=checkWeek.intervals[n][di][+index];return {...p,id:e.dataset.point,level:n===1?3:n===3?2:n===6?1:0,hazards:p.warnings.flatMap(a=>a.metrics.filter(k=>(a.metric_severities?.[k]||a.severity)==='critical').map(k=>map[k]).filter(Boolean))};});
   const old=document.createElement('div');old.innerHTML=previousCharts.rows(points,xs,w,true,false,{compact:true,mobileCompact:innerWidth<768,captionWidth:w/points.length-12});
   const normalized=(el)=>{el=el.cloneNode(true);el.querySelectorAll('.metric-caption').forEach(e=>e.removeAttribute('transform'));return el.outerHTML.replace(/([wc])\\d+/g,'$1gradient');};
   const unchanged=Object.fromEntries(['felt','wind','rain','gust','direction','humidity','visibility','freezing'].map(k=>[k,normalized(old.querySelector('[data-metric="'+k+'"]'))===normalized(document.querySelector('[data-metric="'+k+'"]'))]));
   const actual=document.querySelector('[data-metric="actual"]'),oldActual=old.querySelector('[data-metric="actual"]');
   oldActual.querySelectorAll('[data-range],.chart-value.range,.metric-label-sub').forEach(e=>e.remove());
   const newActual=actual.cloneNode(true);newActual.querySelectorAll('[data-temperature-range]').forEach(e=>e.remove());
   unchanged.actualCurve=normalized(oldActual)===normalized(newActual);
   const expectedPairs=points.filter(p=>p.level!==3).length;
   return {unchanged,expectedPairs,feltPairs:document.querySelectorAll('[data-metric="felt-range"] [data-temperature-range]').length,actualPairs:actual.querySelectorAll('[data-temperature-range]').length,overflow:document.documentElement.scrollWidth>innerWidth,metrics:[...document.querySelectorAll('[data-metric]')].map(e=>e.dataset.metric)};
  })()`);
  assert(Object.values(evidence.unchanged).every(Boolean),JSON.stringify(evidence.unchanged));
  assert.equal(evidence.feltPairs,evidence.expectedPairs);assert.equal(evidence.actualPairs,evidence.expectedPairs);
  assert(!evidence.overflow);assert.deepEqual(evidence.metrics.slice(-2),['uv_index','heat_index_c']);
  for(const theme of ['dark','light']){
   if(await evaluate('document.documentElement.dataset.theme')!==theme)await evaluate("document.querySelector('.theme-toggle').click()");
   await evaluate('document.fonts.ready.then(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))))');
   await pause(100);
   const cropHeight=await evaluate('Math.min(innerHeight,Math.ceil(document.querySelector(".forecast-attribution").getBoundingClientRect().bottom)+36)');
   const name=`${device}-${theme}-${step}h.png`;
   const capture=await send('Page.captureScreenshot',{format:'png',fromSurface:true,captureBeyondViewport:false,clip:{x:0,y:0,width,height:cropHeight,scale:1}});
   await fs.writeFile(output+'/'+name,Buffer.from(capture.data,'base64'));
   results.push({name,device,theme,step,...evidence});
  }
 }
 if(device==='mobile')for(const narrow of [320,360]){
  await resize(narrow,800);
  assert(!await evaluate('document.documentElement.scrollWidth>innerWidth'));
  results.push({device,width:narrow,overflow:false});
 }
 await resize(width,800);
 await evaluate('window.scrollTo(0,240)');
 const before=await evaluate('scrollY');
 await evaluate("document.querySelector('[data-v4-expand=\"2\"]').click()");await pause(100);
 assert(Math.abs(before-await evaluate('scrollY'))<=2,'Keep vertical scroll on expanding another day');
 assert.equal(weatherGets,1,'No weather request on expansion/theme/resize');
 assert.deepEqual(errors,[],'No uncaught browser exception');
 results.push({device,weatherGets,writesBlocked,verticalScrollPreserved:true});
 await send('Page.close');socket.close();
}
await fs.writeFile(output+'/verification.json',JSON.stringify({baseline,data:'Isolated synthetic local API; no provider request or production mutation',results},null,2)+'\n');
console.log('Passed: 16 theme/device/interval combinations, unchanged existing charts, narrow layouts, scroll and one weather request.');
