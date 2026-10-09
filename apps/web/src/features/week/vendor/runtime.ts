// @ts-nocheck
// Adapted approved v5 renderer; calculations and equipment come only from internal API.
import {charts} from "./charts";
import {weatherIcons} from "./weatherIcons";
import {uiIcons,equipmentIcons} from "./icons";
/* Hawatch v4. All controls read the same preloaded eight-day response. */
export function createForecastRuntime(W, HW_POINTS, HW_ROUTES, HW_BRAND){
 'use strict';
 const C=charts,resolutions=['daily','6h','3h','1h'];
 const fa=C.fa,num=C.num,mobile=()=>innerWidth<768;
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const ui=(key,cls='')=>`<svg class="icon ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${uiIcons[key]||equipmentIcons[gearIcon(key)]||''}</svg>`;
 const sky=(code,at)=>{const hour=at?Number(at.slice(11,13)):12,night=hour<6||hour>=19,suffix=night?'night':'day';return ({clear:'clear-'+suffix,'mainly-clear':'mostly-clear-'+suffix,'partly-cloudy':'partly-cloudy-'+suffix,overcast:'cloudy',fog:'fog-'+suffix,shower:night?'showers-night':'showers',thunder:'thunderstorm','freezing-drizzle':'freezing-rain',wind:'wind'})[code]||code||'unknown';};
 const weather=(key,cls='')=>`<svg class="icon ${cls}" viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${weatherIcons[key]||weatherIcons.unknown}</svg>`;
 const weatherName=code=>({clear:'صاف','mainly-clear':'عمدتاً صاف','partly-cloudy':'نیمه‌ابری',overcast:'ابری',fog:'مه',drizzle:'نم‌نم باران','freezing-drizzle':'نم‌نم یخ‌زده',rain:'باران','freezing-rain':'باران یخ‌زده',snow:'برف',shower:'رگبار',thunder:'رعدوبرق'})[code]||'نامشخص';
 const weatherLabel=label=>`<span class="weather-label">${esc(label)}</span>`;
 const warning=()=>weather('warning','point-warning');
 const routeBadge=()=>`<span class="route-icon">${weather('hike')}</span>`;
 const routeChevron=()=>weather('chevron-left','route-chevron');
 const changeRoute=cls=>`<button class="change-route ${cls}" data-v4-routes>${routeBadge()}تغییر مسیر ${routeChevron()}</button>`;
 const speeds={slow:'آرام',medium:'متوسط',fast:'سریع'};
 const cache=new Map();let ctx=null,layout=null,callbacks={},modal=null,shareFile=null,shareURL=null,shareToken=0,returnFocus=null,resizeTimer;
 const dates=()=>W.days;
 function viewState(kind,id){const key=kind+':'+id;if(!cache.has(key))cache.set(key,{levels:Array(8).fill(0),expert:false,gear:false,menu:false,scroll:null,dateScroll:null});return cache.get(key);}
 const clock=n=>String(Math.floor(n/60)%24).padStart(2,'0')+':'+String(n%60).padStart(2,'0');
 const track=()=>'<div class="scroll-track" role="scrollbar" aria-label="پیمایش افقی پیش‌بینی" aria-orientation="horizontal" tabindex="0" aria-valuemin="0" aria-valuemax="100" aria-valuenow="100"><span class="scroll-thumb"></span></div>';
 function slots(){return W.points[ctx.record.slug].days.flatMap((d,day)=>{const level=ctx.v.levels[day];return d.intervals[resolutions[level]].map((p,i)=>({...d,...p,weatherLabel:p.condition||weatherName(p.weather),weather:sky(p.weather,p.weather_at),hazards:criticalMetrics(p.warnings||[]),day,level,id:d.id+'-'+resolutions[level]+'-'+i}));});}
 function positions(points,width,distance=false,exporting=false){
  if(!distance)return points.map((_,i)=>width-(i+.5)*width/points.length);
  // A readable column for each stop; distance remains in the point label.
  const pad=exporting?64:mobile()?32:55,span=width-pad*2;
  if(points.length===1)return [width/2];
  return points.map((_,i)=>width-pad-i*span/(points.length-1));
 }
 function routeValues(record=ctx.record,state=ctx.state){
  const data=W.api, di=state.day, hour=Math.floor(state.time/60), offsets=data.offsets[state.speed]||[], plan=data.plans[`${di}:${state.speed}:${hour}`]||{records:[],equipment:[]};
  const points=data.points.map((p,i)=>{const row=data.records[plan.records[i]], total=state.time+(offsets[i]??0);return {...chartReading(row), id:p.slug, name:p.name, label:p.name, arrival:data.timing_pending?'—':clock(total), nextDay:data.timing_pending?0:Math.floor(total/1440), distance:p.distance_km, warnings:row?.warnings||[], forecastAt:row?.forecast_at};});
  const gear=new Map();for(const index of plan.equipment){const item=data.equipment[index],existing=gear.get(item.id);if(existing){for(const e of item.evidence)if(!existing.evidence.some(a=>a.point===e.point&&a.at===e.at))existing.evidence.push(e);}else gear.set(item.id,{...item,evidence:[...item.evidence]});}if(gear.has('hardshell')){gear.delete('poncho');gear.delete('windstopper');}
  return {name:record.name,date:dates()[di],points,equipment:[...gear.values()],summary:{start:clock(state.time),speed_label:speeds[state.speed],arrival:points.at(-1)?.arrival||'—',nextDay:points.at(-1)?.nextDay||0,duration_minutes:offsets.at(-1)??null,distance_km:data.subject.distance_km,ascent_m:data.subject.ascent_m,descent_m:data.subject.descent_m}};
 }
 function chartReading(row){
  const keys={apparent_temperature_c:'felt',temperature_c:'actual',wind_speed_kmh:'wind',wind_gust_kmh:'gust',precipitation_mm:'rain',wind_direction_deg:'direction',relative_humidity_pct:'humidity',visibility_km:'visibility',freezing_level_m:'freezing'};
  const result={weather:sky(row?.weather_code,row?.forecast_at),weatherLabel:row?.condition||weatherName(row?.weather_code),hazards:[]};
  for(const [field,key] of Object.entries(keys)) result[key]=row?.[field]??null;
  result.min=result.max=result.actual;
  result.hazards=criticalMetrics(row?.warnings||[]);
  return result;
 }
 function criticalMetrics(warnings){const map={apparent_temperature_c:'felt',temperature_c:'actual',wind_speed_kmh:'wind',wind_gust_kmh:'gust',precipitation_mm:'rain',visibility_km:'visibility'};return [...new Set(warnings.flatMap(w=>w.metrics?.filter(k=>(w.metric_severities?.[k]||w.severity)==='critical').map(k=>map[k]).filter(Boolean)||[]))];}
 function warningsHTML(data){const list=data.points.flatMap(p=>p.warnings.map(w=>`<p class="${w.severity==='critical'?'risk-red':''}">${esc(p.name)} · ${fa(p.arrival)}: ${esc(w.label)}؛ ${esc(w.reason)}</p>`));return [...new Set(list)].join('');}
 function gearIcon(key){return ({'insulated-jacket':'down-jacket','warm-gloves':'insulated-gloves','windstopper':'windbreaker','hardshell':'rain-jacket','poncho':'rain-jacket','balaclava':'neck-gaiter','uv-glasses':'sunglasses'})[key]||key;}

 function summary(data,exporting=false){const s=data.summary,duration=s.duration_minutes==null?'—':fa(Math.floor(s.duration_minutes/60))+' ساعت'+(s.duration_minutes%60?' و '+fa(s.duration_minutes%60)+' دقیقه':''),fields=[['clock','ساعت شروع',`<bdi dir="ltr">${fa(s.start)}</bdi>`],['gauge','سرعت حرکت',s.speed_label],['flag','زمان رسیدن',`<bdi dir="ltr">${fa(s.arrival)}</bdi>${s.nextDay?`<small>${s.nextDay===1?'روز بعد':fa(s.nextDay)+' روز بعد'}</small>`:''}`],['stopwatch','مدت مسیر',duration],['distance','مسافت',(s.distance_km==null?'—':num(s.distance_km)+' کیلومتر')],['ascent-descent',exporting?'صعود / فرود':'صعود / فرود (متر)',`<span class="elevations"><span class="elevation-ascent">↑ <b>${(s.ascent_m==null?'—':fa(s.ascent_m))}</b>${exporting?' <small>متر</small>':''}</span><span class="elevation-descent">↓ <b>${(s.descent_m==null?'—':fa(s.descent_m))}</b>${exporting?' <small>متر</small>':''}</span></span>`]];
  return `<section class="route-summary" aria-label="خلاصهٔ مسیر">${fields.map(([key,title,val])=>`<div class="summary-item" data-summary="${key}">${ui(key)}<div><small>${title}</small><strong${key==='stopwatch'?' class="duration-value"':''}>${val}</strong></div></div>`).join('')}</section>`;
 }
 function related(){const p=ctx.record,list=HW_ROUTES.filter(r=>r.points.includes(p.slug));if(!list.length)return '';
  return `<aside class="routes"><h2>مسیرهای متصل به ${esc(p.short||p.name)}</h2>${list.slice(0,3).map(r=>`<a class="route-link" href="/routes/${r.slug}" data-nav>${routeBadge()}<span class="copy"><strong>${esc(r.name)}</strong><small>${fa(r.distance)} کیلومتر · ${fa(r.ascent)} متر صعود</small></span>${routeChevron()}</a>`).join('')}<button class="all-routes" data-v4-routes>همهٔ مسیرها ${ui('arrow-right')}</button></aside>`;
 }
 function gearList(){const items=routeValues().equipment;return `<div class="gear-list" id="v4-gear-body">${items.length?items.map(a=>`<div class="gear-item">${ui(a.id)}<div><strong>${esc(a.name)}</strong><small>${esc(a.reason)} · ${a.evidence.map(e=>{const p=W.api.points.find(p=>p.weather_point_id===e.point);return esc(p?.name||'')+' '+fa(e.at.slice(11,16));}).join('، ')}</small></div></div>`).join(''):'<p>تجهیزات اضافهٔ مشخصی از داده‌های موجود پیشنهاد نمی‌شود.</p>'}</div>`;}

 function controls(){return `<div class="v4-date-scroll" tabindex="0" aria-label="انتخاب روز برنامه"><div class="route-day-row">${dates().map((d,i)=>`<button class="route-date ${i===ctx.state.day?'active':''}" data-v4-date="${i}" aria-pressed="${i===ctx.state.day}"><strong>${d.name}</strong><small>${fa(d.date_fa)}</small></button>`).join('')}</div></div><div class="v4-date-track">${track()}</div><div class="route-tools"><div class="tool"><label id="v4-time-label">ساعت شروع</label><button class="input-button" data-v4-menu aria-labelledby="v4-time-label" aria-haspopup="listbox" aria-expanded="${ctx.v.menu}">${ui('clock')}<span class="ltr">${fa(clock(ctx.state.time))}</span>${ui('chevron-down')}</button>${ctx.v.menu?`<div class="tool-popover" role="listbox" aria-label="ساعت شروع">${Array.from({length:24},(_,i)=>i*60).map(t=>`<button role="option" data-v4-start="${t}" aria-selected="${t===ctx.state.time}"><span class="ltr">${fa(clock(t))}</span></button>`).join('')}</div>`:''}</div><div class="tool speed-tool"><label>سرعت حرکت</label><div class="speed-segmented" role="group" aria-label="سرعت حرکت">${Object.entries(speeds).map(([s,n])=>`<button data-v4-speed="${s}" aria-pressed="${s===ctx.state.speed}">${n}</button>`).join('')}</div></div></div>`;}
 function inner(){
  const r=ctx.record;
  if(ctx.kind==='point')return `<section class="hero"><h1>آب‌وهوای ${esc(r.name)}</h1><p>${r.elevation!=null?'ارتفاع '+fa(r.elevation)+' متر':esc(r.region)}</p><h2 class="forecast-title v4-mobile-forecast-title">پیش‌بینی ۷ روزه</h2></section><div class="destination-grid ${HW_ROUTES.some(a=>a.points.includes(r.slug))?'':'v4-no-routes'}"><section class="forecast" aria-label="پیش‌بینی مقصد"><h2 class="forecast-title v4-desktop-forecast-title">پیش‌بینی ۷ روزه</h2><div class="forecast-panel" id="v4-forecast-panel"></div></section>${related()}</div>`;
  const data=routeValues();return `<section class="hero"><h1>${esc(r.name)}</h1><p>${data.summary.distance_km==null?'—':num(data.summary.distance_km)} کیلومتر · <span class="elevation-values"><span class="elevation-ascent">↑ ${(data.summary.ascent_m==null?'—':fa(data.summary.ascent_m))}</span><span class="elevation-descent">↓ ${(data.summary.descent_m==null?'—':fa(data.summary.descent_m))}</span></span> متر</p>${changeRoute('v4-mobile-change-route')}<h2 class="forecast-title v4-mobile-forecast-title">پیش‌بینی ۷ روزه</h2></section><section class="forecast" aria-label="پیش‌بینی مسیر"><div class="v4-route-layout"><div class="v4-route-main"><div class="v4-route-controls"><div class="v4-route-heading"><h2 class="forecast-title">پیش‌بینی ۷ روزه</h2></div>${controls()}</div><div class="forecast-panel" id="v4-forecast-panel"></div></div><div class="v4-route-side">${changeRoute('v4-desktop-change-route')}<aside class="v4-route-support" aria-label="خلاصه و تجهیزات مسیر"><h2 class="v4-route-support-title">خلاصهٔ مسیر</h2>${summary(data)}<div class="route-weather-warnings">${warningsHTML(data)}</div><section class="gear-section"><button class="gear-trigger" data-v4-gear aria-expanded="${ctx.v.gear}" aria-controls="v4-gear-body">${ui(ctx.v.gear?'chevron-up':'chevron-down')}تجهیزات پیشنهادی</button>${ctx.v.gear?gearList(data.points):''}</section><div class="share-row"><button class="primary-button" data-v4-share>${ui('share')}اشتراک‌گذاری</button></div></aside></div></div></section>`;
 }
 function html(kind,record,state){ctx={kind,record,state,v:viewState(kind,record.slug)};return `<div class="forecast-v4" id="forecast-v4">${inner()}</div>`;}
 function dayHeaders(points,xs,width){let out='',cw=width/points.length;
  W.points[ctx.record.slug].days.forEach((d,day)=>{const ids=points.map((p,i)=>p.day===day?i:-1).filter(i=>i>=0),left=xs[ids.at(-1)]-cw/2,w=ids.length*cw,lev=ctx.v.levels[day],expand=lev<3&&d.available.includes(resolutions[lev+1]);
   out+=`<div class="day-group" style="left:${left}px;width:${w}px" data-left="${left}" data-width="${w}">${expand?`<button class="day-button expand" data-v4-expand="${day}" aria-label="نمایش بازهٔ ${[24,6,3,1][lev+1]} ساعتهٔ ${d.name}">${ui('day-expand')}</button>`:''}${lev>0?`<button class="day-button collapse" data-v4-collapse="${day}" aria-label="جمع کردن یک مرحلهٔ ${d.name}">${ui('day-collapse')}</button>`:''}<strong class="day-name" style="left:${w/2}px">${points.some(p=>p.day===day&&p.hazards?.length)?weather('warning','day-warning'):''}${d.name}</strong><span class="day-date" style="left:${w/2}px">${fa(d.date_fa)}</span>${ids.map(i=>points[i].hour==null?'':`<span class="stamp" style="left:${xs[i]-left}px">${fa(clock(points[i].hour*60))}</span>`).join('')}</div>`;
  });return `<div class="day-headers ${ctx.v.levels.some(Boolean)?'has-expanded':''}">${out}</div>`;
 }
 const weatherStrip=(p,x)=>`<div class="weather-strip">${p.map((a,i)=>`<div class="weather-slot" style="left:${x[i]}px" aria-label="${esc(a.name)} ${a.hour==null?'':fa(clock(a.hour*60))}">${a.hour!=null&&a.hazards?.length?warning():''}${weather(a.weather)}${weatherLabel(a.weatherLabel)}</div>`).join('')}</div>`;
 function pointHeaders(p,x,exporting=false){return `<div class="point-headers">${p.map((a,i)=>`<div class="point-header" style="left:${x[i]}px" data-point-id="${a.id}">${exporting?'<strong>':`<a href="/points/${a.id}" data-nav aria-label="${esc(a.name)}"><strong title="${esc(a.name)}">`}${a.hazards?.length?warning():''}${esc(a.label)}${exporting?'</strong>':'</strong></a>'}<small><span class="arrival-clock ltr">${fa(a.arrival)}</span>${a.nextDay?' · روز بعد':''}</small><small>${a.distance==null?'—':num(a.distance)+' km'}</small>${weather(a.weather,'weather')}${weatherLabel(a.weatherLabel)}</div>`).join('')}</div>`;}
 function drawPanel(anchor){
  const panel=document.getElementById('v4-forecast-panel');if(!panel)return;
  const destination=ctx.kind==='point',vw=Math.max(260,panel.clientWidth-(destination?0:mobile()?10:20)),points=destination?slots():routeValues().points;
  const cw=mobile()?Math.max(96,vw/4):Math.max(vw/(ctx.v.levels.some(Boolean)?8:8),110);
  const width=destination?Math.max(vw,points.length*cw):Math.max(vw,(mobile()?64:110)+(points.length-1)*(mobile()?126:155));
  const xs=positions(points,width,!destination),chartLayout=destination?{compact:true,mobileCompact:mobile(),captionWidth:width/points.length-12}:undefined;
  panel.innerHTML=`<div class="timeline-scroll" tabindex="0" aria-label="${destination?'پیش‌بینی پیوستهٔ روزها':'پیش‌بینی پیوستهٔ نقاط مسیر'}"><div class="timeline-content" style="width:${width}px">${destination?dayHeaders(points,xs,width)+weatherStrip(points,xs):pointHeaders(points,xs)}<div class="main-graphs">${C.rows(points,xs,width,false,false,chartLayout)}</div>${destination?`<div style="height:40px"></div><div class="specialist-body" id="v4-experts">${ctx.v.expert?C.expertRows(points,xs,width,chartLayout):''}</div>`:''}</div></div>${destination?`<button class="specialist-trigger" data-v4-expert aria-expanded="${ctx.v.expert}" aria-controls="v4-experts">${ui(ctx.v.expert?'chevron-up':'chevron-down')}جزئیات تخصصی</button>`:''}${track()}`;
  if(destination){const graphs=panel.querySelector('.main-graphs');panel.querySelector('.specialist-trigger').style.top=`${graphs.offsetTop+graphs.offsetHeight}px`;}
  const scroller=panel.querySelector('.timeline-scroll');layout={points,xs,width,vw,scroller};bindScroll(scroller,panel.querySelector('.scroll-track'),()=>syncScroll());
  if(anchor){let i=points.findIndex(a=>a.day===anchor.day&&a.hour===anchor.hour);if(i<0)i=points.findIndex(a=>a.day===anchor.day);scroller.scrollLeft=xs[i]-anchor.screenX;}
  else scroller.scrollLeft=ctx.v.scroll==null?width-vw:Math.min(width-vw,ctx.v.scroll);
  syncScroll();
 }
 function syncScroll(){if(!layout)return;const {scroller,width,vw,xs}=layout,l=scroller.scrollLeft,r=l+vw,first=xs.filter(x=>x>=l&&x<=r).sort((a,b)=>b-a)[0],captionX=first==null?r-5:Math.min(r-5,first+(ctx.kind==='point'?width/xs.length/2-6:Math.min(width/xs.length/2-5,37)));ctx.v.scroll=l;
  scroller.querySelectorAll('.metric-caption').forEach(g=>g.setAttribute('transform',`translate(${captionX} 0)`));
  scroller.querySelectorAll('.day-group').forEach(g=>{const gl=+g.dataset.left,gw=+g.dataset.width,a=Math.max(l,gl),b=Math.min(r,gl+gw),span=b-a,title=(a+b)/2-gl,inset=Math.min(32,gw/2);
   g.querySelectorAll('.day-name,.day-date').forEach(t=>t.style.left=`${Math.max(inset,Math.min(gw-inset,title))}px`);
   const ex=g.querySelector('.expand'),co=g.querySelector('.collapse');if(ex){ex.style.left=`${Math.max(0,a-gl)}px`;ex.style.visibility=span>=44&&(!co||span>=88)?'visible':'hidden';}if(co){co.style.right=`${Math.max(0,gl+gw-b)}px`;co.style.visibility=span>=44?'visible':'hidden';}g.style.visibility=span<35?'hidden':'visible';
  });syncTrack(scroller,scroller.closest('.forecast-panel').querySelector('.scroll-track'));
 }
 function syncTrack(s,t){if(!s||!t)return;const max=s.scrollWidth-s.clientWidth;t.hidden=max<2;const ratio=Math.max(.08,s.clientWidth/Math.max(s.clientWidth,s.scrollWidth)),l=Math.max(0,s.scrollLeft),thumb=t.firstElementChild;thumb.style.width=ratio*100+'%';thumb.style.left=(max?l/max*(1-ratio):0)*100+'%';t.setAttribute('aria-valuenow',Math.round(max?l/max*100:0));}
 function bindScroll(s,t,onScroll){
  s.addEventListener('scroll',onScroll,{passive:true});
  const keys=e=>{if(e.target!==e.currentTarget||!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;e.preventDefault();s.scrollLeft=e.key==='Home'?s.scrollWidth:e.key==='End'?0:s.scrollLeft+(e.key==='ArrowLeft'?-1:1)*s.clientWidth*.5;onScroll();};s.addEventListener('keydown',keys);t.addEventListener('keydown',keys);
  t.onpointerdown=e=>{e.preventDefault();t.setPointerCapture(e.pointerId);const move=e=>{const b=t.getBoundingClientRect(),ratio=Math.max(.08,s.clientWidth/s.scrollWidth);s.scrollLeft=Math.max(0,Math.min(1,(e.clientX-b.left-b.width*ratio/2)/(b.width*(1-ratio))))*(s.scrollWidth-s.clientWidth);onScroll();};move(e);t.onpointermove=move;t.onpointerup=t.onpointercancel=()=>{t.onpointermove=null;};};
  let down=false,drag=false,sx=0,sl=0;
  s.addEventListener('pointerdown',e=>{if(e.pointerType!=='mouse'||e.button!==0||e.target.closest('button'))return;down=true;drag=false;sx=e.clientX;sl=s.scrollLeft;});
  s.addEventListener('pointermove',e=>{if(!down)return;if(Math.abs(e.clientX-sx)>5){drag=true;s.classList.add('dragging');s.setPointerCapture(e.pointerId);s.scrollLeft=sl+sx-e.clientX;e.preventDefault();onScroll();}});
  const end=()=>{down=false;s.classList.remove('dragging');};s.addEventListener('pointerup',end);s.addEventListener('pointercancel',end);s.addEventListener('lostpointercapture',end);
  s.addEventListener('click',e=>{if(drag){e.preventDefault();e.stopPropagation();drag=false;}},true);s.addEventListener('dragstart',e=>e.preventDefault());
 }
 function bindDates(){const s=document.querySelector('.v4-date-scroll'),t=document.querySelector('.v4-date-track .scroll-track');if(!s)return;const max=s.scrollWidth-s.clientWidth;s.scrollLeft=ctx.v.dateScroll==null?max:ctx.v.dateScroll;const sync=()=>{ctx.v.dateScroll=s.scrollLeft;syncTrack(s,t);};bindScroll(s,t,sync);sync();}
 function rerender(focus){const root=document.getElementById('forecast-v4');if(!root)return;root.innerHTML=inner();mount(callbacks);if(focus)root.querySelector(focus)?.focus({preventScroll:true});}
 function changeLevel(day,dir){const old=layout,d=W.points[ctx.record.slug].days[day],next=ctx.v.levels[day]+dir;if(next<0||next>3||!d.available.includes(resolutions[next]))return;const candidates=old.points.map((p,i)=>({p,i,x:old.xs[i]-old.scroller.scrollLeft})).filter(a=>a.p.day===day).sort((a,b)=>Math.abs(a.x-old.vw/2)-Math.abs(b.x-old.vw/2)),chosen=candidates[0],step=[24,6,3,1][next],hour=next===0?null:Math.floor((chosen.p.hour||0)/step)*step;ctx.v.levels[day]=next;drawPanel({day,hour,screenX:chosen.x});document.querySelector(`[data-v4-${dir>0?'expand':'collapse'}="${day}"]`)?.focus({preventScroll:true});}
 function mount(cb){callbacks=cb||callbacks;const root=document.getElementById('forecast-v4');if(!root){layout=null;return;}drawPanel();bindDates();
  root.onclick=e=>{const b=e.target.closest('button[data-v4-expand],button[data-v4-collapse],button[data-v4-expert],button[data-v4-gear],button[data-v4-menu],button[data-v4-start],button[data-v4-speed],button[data-v4-date],button[data-v4-routes],button[data-v4-share]');if(!b)return;e.stopPropagation();const d=b.dataset;
   if(d.v4Expand!=null)changeLevel(+d.v4Expand,1);
   else if(d.v4Collapse!=null)changeLevel(+d.v4Collapse,-1);
   else if(d.v4Expert!=null){ctx.v.expert=!ctx.v.expert;drawPanel();root.querySelector('[data-v4-expert]').focus({preventScroll:true});}
   else if(d.v4Gear!=null){ctx.v.gear=!ctx.v.gear;rerender('[data-v4-gear]');}
   else if(d.v4Menu!=null){ctx.v.menu=!ctx.v.menu;rerender('[data-v4-menu]');if(ctx.v.menu)root.querySelector('[data-v4-start][aria-selected=true]')?.focus({preventScroll:true});}
   else if(d.v4Start!=null){ctx.state.time=+d.v4Start;ctx.v.menu=false;rerender('[data-v4-menu]');callbacks.selection?.(ctx.state);}
   else if(d.v4Speed!=null){ctx.state.speed=d.v4Speed;rerender(`[data-v4-speed="${d.v4Speed}"]`);callbacks.selection?.(ctx.state);}
   else if(d.v4Date!=null){ctx.state.day=+d.v4Date;rerender(`[data-v4-date="${d.v4Date}"]`);callbacks.selection?.(ctx.state);}
   else if(d.v4Routes!=null)callbacks.showRoutes?.();
   else if(d.v4Share!=null)showShare();
  };
  root.onkeydown=e=>{const options=[...root.querySelectorAll('[data-v4-start]')];if(ctx.v.menu&&e.key==='Escape'){e.stopPropagation();ctx.v.menu=false;rerender('[data-v4-menu]');}else if(e.target.matches('[data-v4-start]')&&['ArrowDown','ArrowUp','Home','End'].includes(e.key)){e.preventDefault();const i=options.indexOf(e.target),n=e.key==='Home'?0:e.key==='End'?options.length-1:Math.max(0,Math.min(options.length-1,i+(e.key==='ArrowDown'?1:-1)));options[n].focus();}};
 }
 function exportHTML(data,width){const cw=width-116,x=positions(data.points,cw,true,true),captions=cw-20;return `<article class="export-shell" dir="rtl"><header class="export-heading"><div><h1>${esc(data.name)}</h1><p>${data.date.name} · ${fa(data.date.date_fa)} ${new Intl.DateTimeFormat('fa-IR',{calendar:'persian',year:'numeric',timeZone:'Asia/Tehran'}).format(new Date(data.date.iso+'T12:00:00+03:30'))}</p></div><div class="brand">${HW_BRAND}</div></header><div class="forecast-panel"><div class="timeline-content" style="width:${cw}px">${pointHeaders(data.points,x,true)}${C.rows(data.points,x,cw,false,true).replace(/class="metric-caption"/g,`class="metric-caption" transform="translate(${captions} 0)"`)}</div></div>${summary(data,true)}</article>`;}
 const imageLoad=src=>new Promise((resolve,reject)=>{const i=new Image();i.onload=()=>resolve(i);i.onerror=()=>reject(new Error('Image unavailable'));i.src=src;});
 function roundRect(c,x,y,w,h,r){c.beginPath();c.moveTo(x+r,y);c.arcTo(x+w,y,x+w,y+h,r);c.arcTo(x+w,y+h,x,y+h,r);c.arcTo(x,y+h,x,y,r);c.arcTo(x,y,x+w,y,r);c.closePath();}
 function colorResolved(el,value){if(!value)return '';return value.replace(/var\((--[\w-]+)\)/g,(_,k)=>getComputedStyle(el).getPropertyValue(k).trim()).replace(/currentColor/g,getComputedStyle(el).color);}
 async function drawSvg(canvas,element,bounds){
  const clone=element.cloneNode(true);clone.querySelectorAll('text,title').forEach(e=>e.remove());
  const source=[element,...element.querySelectorAll('*')].filter(e=>!['text','title','tspan'].includes(e.localName));
  const copies=[clone,...clone.querySelectorAll('*')];copies.forEach((e,i)=>{const original=source[i]||element;for(const a of [...e.attributes])if(/var\(|currentColor/.test(a.value))e.setAttribute(a.name,colorResolved(original,a.value));if(e===clone)e.setAttribute('color',getComputedStyle(element).color);});
  clone.setAttribute('xmlns','http://www.w3.org/2000/svg');const box=element.getBoundingClientRect();clone.setAttribute('width',box.width);clone.setAttribute('height',box.height);
  const img=await imageLoad('data:image/svg+xml;charset=utf-8,'+encodeURIComponent(new XMLSerializer().serializeToString(clone)));
  canvas.drawImage(img,box.left-bounds.left,box.top-bounds.top,box.width,box.height);
  const vb=element.viewBox.baseVal,sx=box.width/(vb.width||box.width),sy=box.height/(vb.height||box.height);
  for(const t of element.querySelectorAll('text')){const style=getComputedStyle(t),m=t.getCTM(),tx=+t.getAttribute('x')||0,ty=+t.getAttribute('y')||0;canvas.save();canvas.fillStyle=colorResolved(t,t.getAttribute('fill')||style.fill||style.color);canvas.font=style.font||`${style.fontWeight} ${style.fontSize} Vazirmatn`;canvas.direction=style.direction;canvas.textAlign={middle:'center',start:style.direction==='rtl'?'right':'left',end:style.direction==='rtl'?'left':'right'}[t.getAttribute('text-anchor')||'start'];canvas.textBaseline='alphabetic';const x=m?m.a*tx+m.c*ty+m.e:tx*sx,y=m?m.b*tx+m.d*ty+m.f:ty*sy;canvas.fillText(t.textContent,box.left-bounds.left+x,box.top-bounds.top+y);canvas.restore();}
 }
 async function makeImage(data,theme){
  if(document.fonts)await document.fonts.ready;const width=Math.max(1200,256+data.points.length*128),host=document.createElement('div');host.className='forecast-v4 v4-render-host';host.style.width=width+'px';host.innerHTML=exportHTML(data,width);document.body.append(host);
  try{const card=host.firstElementChild,bounds=card.getBoundingClientRect(),height=Math.ceil(bounds.height),canvas=document.createElement('canvas');canvas.width=width*2;canvas.height=height*2;const c=canvas.getContext('2d');c.scale(2,2);
   const bg=await imageLoad(`/new-design/share-backgrounds/${theme}.webp`),scale=Math.max(width/bg.width,height/bg.height);c.drawImage(bg,(width-bg.width*scale)/2,(height-bg.height*scale)/2,bg.width*scale,bg.height*scale);c.fillStyle=theme==='dark'?'rgba(1,21,37,.26)':'rgba(232,242,245,.12)';c.fillRect(0,0,width,height);
   const panel=card.querySelector('.forecast-panel'),pb=panel.getBoundingClientRect(),ps=getComputedStyle(panel);roundRect(c,pb.left-bounds.left,pb.top-bounds.top,pb.width,pb.height,14);c.fillStyle=ps.backgroundColor;c.fill();c.strokeStyle=ps.borderTopColor;c.lineWidth=1;c.stroke();
   for(const svg of card.querySelectorAll('svg'))await drawSvg(c,svg,bounds);
   // Preserve the actual line layout for long canonical names in PNG exports.
   // A single fillText on the union rectangle would overlap adjacent columns.
   const walker=document.createTreeWalker(card,NodeFilter.SHOW_TEXT);let node;
   while((node=walker.nextNode())){
    if(!node.textContent.trim()||node.parentElement.closest('svg'))continue;
    const range=document.createRange();range.selectNodeContents(node);const style=getComputedStyle(node.parentElement);
    const paint=(text,box)=>{if(!box.width)return;c.save();c.fillStyle=style.color;c.font=style.font||`${style.fontWeight} ${style.fontSize} Vazirmatn`;c.direction=style.direction;c.textAlign=style.direction==='rtl'?'right':'left';c.textBaseline='alphabetic';const descent=c.measureText(text).fontBoundingBoxDescent??parseFloat(style.fontSize)*.22;c.fillText(text,style.direction==='rtl'?box.right-bounds.left:box.left-bounds.left,box.bottom-bounds.top-descent);c.restore();};
    const rects=[...range.getClientRects()];
    if(new Set(rects.map(r=>Math.round(r.top))).size<=1)paint(node.textContent,range.getBoundingClientRect());
    else for(const match of node.textContent.matchAll(/\S+/gu)){range.setStart(node,match.index);range.setEnd(node,match.index+match[0].length);paint(match[0],range.getBoundingClientRect());}
   }

   const blob=await new Promise((resolve,reject)=>canvas.toBlob(b=>b?resolve(b):reject(new Error('Image generation failed')),'image/png'));return new File([blob],`hawatch-${ctx.record.slug}-${data.date.iso}-${data.summary.start.replace(':','')}.png`,{type:'image/png'});
  }finally{host.remove();}
 }
 function closeFull(){modal?.querySelector('.full-image-overlay')?.remove();modal?.querySelector('[data-v4-enlarge]')?.focus();}
 function closeShare(){shareToken++;if(!modal)return;modal.remove();modal=null;document.getElementById('root').inert=false;document.body.classList.remove('dialog-open');document.body.style.overflow='';if(shareURL)URL.revokeObjectURL(shareURL);shareURL=null;shareFile=null;returnFocus?.focus({preventScroll:true});}
 function modalFrame(content){return `<div class="modal-overlay"><section class="share-modal" role="dialog" aria-modal="true" aria-labelledby="v4-share-title" tabindex="-1"><div class="sheet-handle" aria-hidden="true"></div><div class="modal-heading"><h2 id="v4-share-title">اشتراک‌گذاری مسیر</h2><button class="close-button" data-v4-close aria-label="بستن">${ui('close')}</button></div>${content}</section></div>`;}
 function saveImage(){if(!shareFile||!shareURL)return;const a=document.createElement('a');a.href=shareURL;a.download=shareFile.name;a.click();}
 async function showShare(){
  closeShare();returnFocus=document.activeElement;const data=routeValues(),theme=ctx.state.theme,token=++shareToken;let link='';
  modal=document.createElement('div');modal.className='forecast-v4';modal.innerHTML=modalFrame('<p class="share-message" role="status">در حال آماده‌سازی تصویر…</p>');document.body.append(modal);document.getElementById('root').inert=true;document.body.style.overflow='hidden';modal.querySelector('.share-modal').focus();
  modal.addEventListener('click',async e=>{const button=e.target.closest('button');if(e.target.classList.contains('modal-overlay')||button?.hasAttribute('data-v4-close')){closeShare();return;}if(button?.hasAttribute('data-v4-close-full')){closeFull();return;}if(button?.hasAttribute('data-v4-save'))saveImage();if(button?.hasAttribute('data-v4-retry')){closeShare();showShare();}
   if(button?.hasAttribute('data-v4-enlarge')){const viewer=document.createElement('div');viewer.className='full-image-overlay';viewer.innerHTML=`<button class="close-button" data-v4-close-full aria-label="بستن تصویر کامل">${ui('close')}</button><img src="${shareURL}" alt="تصویر کامل همهٔ نقاط مسیر" style="--natural-width:${Math.max(1200,256+data.points.length*128)}px">`;modal.append(viewer);viewer.querySelector('button').focus();}
   if(button?.hasAttribute('data-v4-send')){if(!navigator.canShare?.({files:[shareFile]})){callbacks.toast?.('اشتراک مستقیم در این مرورگر فعال نیست؛ تصویر را ذخیره کن.');return;}try{await navigator.share({files:[shareFile],text:data.name+'\n'+link});}catch(err){if(err.name!=='AbortError')callbacks.toast?.('ارسال ممکن نشد؛ می‌توانی تصویر را ذخیره کنی.');}}
  });
  try{link=await callbacks.createLink(ctx.record,ctx.state);const file=await makeImage(data,theme);if(token!==shareToken||!modal)return;shareFile=file;shareURL=URL.createObjectURL(file);modal.innerHTML=modalFrame(`<button class="preview-button" data-v4-enlarge aria-label="دیدن تصویر در اندازهٔ کامل"><img class="preview-image" src="${shareURL}" alt="تمام نقاط و خلاصهٔ ${esc(data.name)}"></button><p class="preview-hint">برای دیدن تصویر کامل لمس کن</p><p class="share-message">${esc(data.name)}<a class="v4-short-link" href="${esc(link)}" target="_blank" rel="noopener">${esc(link)}</a></p><div class="modal-actions">${mobile()?`<button class="primary-button" data-v4-send>${ui('share')}اشتراک‌گذاری</button>`:''}<button class="${mobile()?'secondary':'primary'}-button" data-v4-save>${ui('download')}ذخیرهٔ عکس</button></div>`);modal.querySelector('[data-v4-close]').focus();}
  catch(err){console.error('Route image:',err);if(token===shareToken&&modal){modal.innerHTML=modalFrame(`<p class="share-error" role="alert">تصویر آماده نشد.<button data-v4-retry>تلاش دوباره</button></p>`);modal.querySelector('[data-v4-close]').focus();}}
 }
 const onDocumentKey=e=>{if(!modal)return;if(e.key==='Escape'){e.preventDefault();e.stopImmediatePropagation();if(modal.querySelector('.full-image-overlay'))closeFull();else closeShare();}else if(e.key==='Tab'){const active=modal.querySelector('.full-image-overlay')||modal.querySelector('.share-modal'),all=[...active.querySelectorAll('button,a[href]')].filter(e=>!e.disabled&&!e.hidden);if(!all.length){e.preventDefault();return;}if(e.shiftKey&&document.activeElement===all[0]){e.preventDefault();all.at(-1).focus();}else if(!e.shiftKey&&document.activeElement===all.at(-1)){e.preventDefault();all[0].focus();}}};document.addEventListener('keydown',onDocumentKey,true);
 const onResize=()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>{if(document.getElementById('forecast-v4')){const anchor=layout?{day:layout.points.find(p=>p.day!=null)?.day,hour:null,screenX:layout.vw/2}:null;drawPanel();bindDates();}},120);};window.addEventListener('resize',onResize);
 return {html,mount,routeValues,slots,destroy(){closeShare();clearTimeout(resizeTimer);document.removeEventListener('keydown',onDocumentKey,true);window.removeEventListener('resize',onResize);}};
}
