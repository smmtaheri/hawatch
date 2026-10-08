import {useEffect,useLayoutEffect,useRef,useState} from 'react';
import {Link,useNavigate,useParams,useSearchParams} from 'react-router-dom';
import {NotFoundPage} from '../../pages/NotFoundPage';
import {Dialog} from '../../components/Dialog';
import {PageShell} from '../../components/PageShell';
import {usePageTitle} from '../../lib/pageTitle';
import brand from '../../components/brandMark.svg?raw';
import {createForecastRuntime} from './vendor/runtime';
import './forecast-v5.css';
import './agreed.css';

type Day={date:string;label:string;jalali:string};
type Subject={slug:string;name?:string;title?:string;elevation_m?:number;region?:string;distance_km?:number;ascent_m?:number;descent_m?:number;seo_indexable?:boolean};
export type Week={kind:'point'|'route';subject:Subject;days:Day[];range_start:string;range_end:string;last_generated_at:string|null;stale_after_hours:number;cache_max_age_seconds:number;related_routes?:Subject[];intervals?:Record<string,Array<Array<Record<string,unknown>>>>;points?:Array<{slug:string;name:string}>;timing_pending?:boolean};
const cache=new Map<string,{data:Week;expires:number}>();
export function clearWeekCache(){cache.clear();pending.clear();}
const pending=new Map<string,Promise<Week>>();
function tehranDate(){return new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tehran',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());}
export async function loadWeek(kind:string,slug:string):Promise<Week>{
 const key=`${kind}:${slug}:${tehranDate()}`, existing=cache.get(key);
 if(existing&&existing.expires>Date.now()) return existing.data;
 const loading=pending.get(key);if(loading)return loading;
 const request=fetch(`/api/v1/${kind==='point'?'points':'routes'}/${encodeURIComponent(slug)}/forecast/week/`,{credentials:'omit'}).then(async r=>{
  if(!r.ok)throw Object.assign(new Error(r.status===404?'نقطه یا مسیر پیدا نشد':'دریافت پیش‌بینی ممکن نشد'),{status:r.status});
  const data=await r.json() as Week;
  // Honor the response's age; a CDN hit must not restart a fresh two-minute window.
  const age=Number(r.headers.get('Age')||0),midnight=Date.parse(`${data.range_start}T00:00:00+03:30`)+86400000,ttl=Math.max(0,Math.min(data.cache_max_age_seconds-age,(midnight-Date.now())/1000));
  cache.set(key,{data,expires:Date.now()+ttl*1000});while(cache.size>3)cache.delete(cache.keys().next().value!);
  return data;
 }).finally(()=>pending.delete(key));pending.set(key,request);return request;
}
function adapted(data:Week){
 const days=data.days.map(d=>({name:d.label,date_fa:d.jalali,iso:d.date,id:d.date,available:['daily','6h','3h','1h']}));
 const points:any={};
 if(data.kind==='point') points[data.subject.slug]={days:days.map((d,i)=>({...d,intervals:Object.fromEntries([[24,'daily'],[6,'6h'],[3,'3h'],[1,'1h']].map(([n,name])=>[name,(data.intervals?.[String(n)][i]||[]).map(row=>({...row,hour:n===24?null:row.hour}))]))}))};
 return {api:data,days,points};
}
export function WeekForecastPage({kind}:{kind:'point'|'route'}){
 const {slug=''}=useParams(),navigate=useNavigate(),[params,setParams]=useSearchParams();
 const [data,setData]=useState<Week|null>(null),[error,setError]=useState(''),[retry,setRetry]=useState(0),[routesOpen,setRoutesOpen]=useState(false),[missing,setMissing]=useState(false);
 const root=useRef<HTMLDivElement>(null),runtime=useRef<ReturnType<typeof createForecastRuntime>|null>(null);
 const dataSubject=data?.subject.slug===slug?data.subject:undefined;
 usePageTitle(dataSubject?.name||dataSubject?.title,{robots:dataSubject?.seo_indexable===false?'noindex,follow':undefined,title:(dataSubject as any)?.seo_title,description:(dataSubject as any)?.seo_description});
 useLayoutEffect(()=>{document.body.classList.add('forecast-page');if(kind==='route')document.body.classList.add('route-page');return()=>{document.body.classList.remove('forecast-page','route-page');};},[kind]);
 useEffect(()=>{
  let active=true,timer:number;setData(null);setError('');setMissing(false);
  async function load(){if(document.hidden){window.clearTimeout(timer);timer=window.setTimeout(load,120000);return;}try{const d=await loadWeek(kind,slug);if(active){setData(d);setError('');window.clearTimeout(timer);const midnight=Date.parse(`${d.range_start}T00:00:00+03:30`)+86400000;timer=window.setTimeout(load,Math.max(1000,Math.min(d.cache_max_age_seconds*1000,midnight-Date.now())));}}catch(e){if(active){setError(e instanceof Error?e.message:'دریافت پیش‌بینی ممکن نشد');setMissing((e as {status?:number}).status===404);}}}
  void load();const focus=()=>{void load();};window.addEventListener('focus',focus);const visible=()=>{if(!document.hidden)void load();};document.addEventListener('visibilitychange',visible);
  return()=>{active=false;window.clearTimeout(timer);window.removeEventListener('focus',focus);document.removeEventListener('visibilitychange',visible);};
 },[kind,slug,retry]);
 useLayoutEffect(()=>{
  if(!data||data.subject.slug!==slug||!root.current)return;
  const W=adapted(data), record={...data.subject,name:data.subject.name||data.subject.title,elevation:data.subject.elevation_m,points:data.points?.map(p=>p.slug)||[]};
  const selected=params.get('date'),day=Math.max(0,data.days.findIndex(d=>d.date===selected));
  const raw=params.get('start_time')?.replace(/[۰-۹٠-٩]/g,c=>String('۰۱۲۳۴۵۶۷۸۹'.includes(c)?'۰۱۲۳۴۵۶۷۸۹'.indexOf(c):'٠١٢٣٤٥٦٧٨٩'.indexOf(c))),hour=raw&&/^\d{2}:\d{2}$/.test(raw)?Math.max(0,Math.min(23,Number(raw.slice(0,2)))):Number(new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Tehran',hour:'2-digit',hourCycle:'h23'}).format(new Date()));
  const requestedSpeed=params.get('speed'),speed=({slow:'slow',medium:'medium',fast:'fast','آرام':'slow','متوسط':'medium','سریع':'fast'} as Record<string,string>)[requestedSpeed||'']||'medium';
  const state={day,time:hour*60,speed,theme:document.documentElement.dataset.theme||'light'};
  const related=data.related_routes||[],pointRecords=data.points||[record];
  const engine=createForecastRuntime(W,pointRecords,related.map(r=>({...r,name:r.title,points:[data.subject.slug],distance:r.distance_km,ascent:r.ascent_m})),brand);runtime.current=engine;
  root.current.innerHTML=engine.html(kind,record,state);
  const selection=(s:any)=>{const q=new URLSearchParams(window.location.search);q.delete('past_program');q.set('date',data.days[s.day].date);q.set('start_time',`${String(s.time/60).padStart(2,'0')}:00`);q.set('speed',s.speed);setParams(q,{replace:true});};
  engine.mount({showRoutes:()=>setRoutesOpen(true),selection,createLink:async (_r:any,s:any)=>{
   const r=await fetch('/api/v1/shares/',{method:'POST',credentials:'omit',headers:{'Content-Type':'application/json'},body:JSON.stringify({route:slug,date:data.days[s.day].date,start_hour:s.time/60,speed:s.speed})});if(!r.ok)throw new Error('ساخت لینک کوتاه ممکن نشد');const p=await r.json();return new URL(p.path,window.location.origin).toString();
  }});
  const onNav=(e:MouseEvent)=>{const link=(e.target as Element).closest<HTMLAnchorElement>('a[data-nav]');if(link&&e.button===0&&!e.ctrlKey&&!e.metaKey&&!e.shiftKey){e.preventDefault();navigate(link.getAttribute('href')!);}};
  root.current.addEventListener('click',onNav);
  const observer=new MutationObserver(()=>{state.theme=document.documentElement.dataset.theme||'light';});observer.observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
  return()=>{observer.disconnect();root.current?.removeEventListener('click',onNav);engine.destroy();runtime.current=null;};
 // Selection URL changes do not remount the renderer or fetch weather.
 // eslint-disable-next-line react-hooks/exhaustive-deps
 },[data,kind,slug,navigate]);
 if(missing)return <NotFoundPage title={kind==='point'?'نقطه پیدا نشد':'مسیر پیدا نشد'}/>;
 const routeQuery=new URLSearchParams(params);routeQuery.delete('past_program');
 const stale=data?.last_generated_at&&Date.now()-Date.parse(data.last_generated_at)>data.stale_after_hours*3600000;
 return <PageShell className={kind==='route'?'route-page':'point-page'} back showInitialContent={!data}>
  {params.get('past_program')==='1'||(data&&params.get('date')&&params.get('date')!<data.range_start)?<p role="status">تاریخ این برنامه گذشته است؛ پیش‌بینی امروز نمایش داده می‌شود.</p>:null}
  {stale?<p role="status">دادهٔ پیش‌بینی قدیمی است؛ زمان انتشار داده را در نظر بگیرید.</p>:null}
  {data?.timing_pending?<p role="status">زمان‌بندی مسیر هنوز تأیید نشده است؛ زمان رسیدن و هوای آن نمایش داده نمی‌شود.</p>:null}
  {error?<p role="alert">{error} <button onClick={()=>setRetry(n=>n+1)}>تلاش دوباره</button></p>:null}
  {!data&&!error?<p role="status">در حال دریافت پیش‌بینی…</p>:null}
  <div ref={root}/>
  {routesOpen?<Dialog className="week-route-picker" title="انتخاب مسیر" onClose={()=>setRoutesOpen(false)}>{(data?.related_routes||[]).map(r=><Link key={r.slug} to={`/routes/${r.slug}${routeQuery.size?'?'+routeQuery.toString():''}`} onClick={()=>setRoutesOpen(false)}>{r.title}</Link>)}<Link to="/routes" onClick={()=>setRoutesOpen(false)}>همهٔ مسیرها</Link></Dialog>:null}
 </PageShell>;
}
