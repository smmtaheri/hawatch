import {afterEach,expect,it,vi} from 'vitest';
import {createForecastRuntime} from '../src/features/week/vendor/runtime';
import {weekFixture} from './fixtures/week';

afterEach(()=>{document.body.innerHTML='';});

it('prepares route equipment only when opened and reuses it until the plan changes',()=>{
 const data=weekFixture('route','2026-10-09') as any;
 const item={id:'windstopper',name:'وینداستاپر',reason:'باد',evidence:[{point:1,at:'2026-10-09T08:00:00+03:30'}]};
 const reads=vi.fn(()=>[item]);
 Object.defineProperty(data,'equipment',{get:reads});
 const runtime=createForecastRuntime({api:data,days:data.days.map((d:any)=>({...d,name:d.label,date_fa:d.jalali})),points:{}},data.points,[],'');
 try{
  document.body.innerHTML=runtime.html('route',{...data.subject,name:data.subject.title},{day:0,time:480,speed:'medium',theme:'dark'});
  runtime.mount({});
  expect(reads).not.toHaveBeenCalled();
  document.querySelector<HTMLButtonElement>('[data-v4-gear]')!.click();
  expect(reads).toHaveBeenCalledTimes(2);
  expect(document.querySelector('.gear-list')?.textContent).toContain('وینداستاپر');
  document.querySelector<HTMLButtonElement>('[data-v4-menu]')!.click();
  expect(reads).toHaveBeenCalledTimes(2);
  document.querySelector<HTMLButtonElement>('[data-v4-speed="fast"]')!.click();
  expect(reads).toHaveBeenCalledTimes(4);
 }finally{runtime.destroy();}
});

it('keeps the route chart mounted for menu/equipment toggles and reuses recent planner snapshots',()=>{
 const data=weekFixture('route','2026-10-09') as any;
 const state={day:0,time:480,speed:'medium',theme:'dark'};
 const runtime=createForecastRuntime({api:data,days:data.days.map((d:any)=>({...d,name:d.label,date_fa:d.jalali})),points:{}},data.points,[],'');
 try{
  document.body.innerHTML=runtime.html('route',{...data.subject,name:data.subject.title},state);
  runtime.mount({});
  const first=runtime.routeValues();
  state.speed='fast';const second=runtime.routeValues();
  state.speed='medium';expect(runtime.routeValues()).toBe(first);
  expect(second).not.toBe(first);
  const graph=document.querySelector('.main-graphs');
  document.querySelector<HTMLButtonElement>('[data-v4-gear]')!.click();
  expect(document.querySelector('.main-graphs')).toBe(graph);
  document.querySelector<HTMLButtonElement>('[data-v4-menu]')!.click();
  expect(document.querySelector('.main-graphs')).toBe(graph);
  document.querySelector<HTMLButtonElement>('[data-v4-start="600"]')!.click();
  expect(document.querySelector('.main-graphs')).not.toBe(graph);
 }finally{runtime.destroy();}
});

it('keeps first and last route labels inside the mobile timeline viewport',()=>{
 const originalInnerWidth=window.innerWidth;
 window.innerWidth=390;
 const data=weekFixture('route','2026-10-09') as any;
 const runtime=createForecastRuntime({api:data,days:data.days.map((d:any)=>({...d,name:d.label,date_fa:d.jalali})),points:{}},data.points,[],'');
 try{
  document.body.innerHTML=runtime.html('route',{...data.subject,name:data.subject.title},{day:0,time:480,speed:'medium',theme:'dark'});
  runtime.mount({});
  const content=document.querySelector<HTMLElement>('.timeline-content')!;
  const width=Number.parseFloat(content.style.width);
  const centers=[...document.querySelectorAll<HTMLElement>('.point-header')].map(header=>Number.parseFloat(header.style.left));
  expect(centers[0]).toBe(width-60);
  expect(centers.at(-1)).toBe(60);
  expect(centers[0]+60).toBeLessThanOrEqual(width);
  expect(centers.at(-1)!-60).toBeGreaterThanOrEqual(0);
 }finally{
  runtime.destroy();
  window.innerWidth=originalInnerWidth;
 }
});

it.each([
 ['mobile',390,300],
 ['desktop',1440,900],
])('keeps destination day labels anchored to their columns while the chart scrolls (%s)',(_device,width,panelWidth)=>{
 const originalInnerWidth=window.innerWidth;
 window.innerWidth=width;
 const data=weekFixture('point','2026-10-09') as any;
 const days=data.days.map((day:any,index:number)=>({
  ...day,
  available:['daily','6h','3h','1h'],
  intervals:{daily:[{id:day.date,day:index,hour:null,felt:2.4,actual:2.4,min:2.4,max:2.4,wind:1.6,gust:0,rain:.4,weather:'clear',weatherLabel:'صاف',hazards:[]}]},
 }));
 const runtime=createForecastRuntime({api:data,days:data.days.map((day:any)=>({...day,name:day.label,date_fa:day.jalali})),points:{[data.subject.slug]:{days}},},[],[],'');
 try{
  document.body.innerHTML=runtime.html('point',{...data.subject,name:data.subject.name}, {day:0,time:480,speed:'medium',theme:'dark'});
  const panel=document.querySelector<HTMLElement>('.forecast-panel')!;
  Object.defineProperty(panel,'clientWidth',{configurable:true,value:panelWidth});
  runtime.mount({});
  const scroller=document.querySelector<HTMLElement>('.timeline-scroll')!;
  Object.defineProperty(scroller,'clientWidth',{configurable:true,value:panelWidth});
  Object.defineProperty(scroller,'scrollWidth',{configurable:true,value:panelWidth*2});
  const group=[...document.querySelectorAll<HTMLElement>('.day-group')].sort((a,b)=>Number(a.dataset.left)-Number(b.dataset.left))[0];
  const label=group.querySelector<HTMLElement>('.day-name')!;
  const date=group.querySelector<HTMLElement>('.day-date')!;
  const initialLabelLeft=label.style.left;
  const initialDateLeft=date.style.left;
  const groupWidth=Number(group.dataset.width);
  scroller.scrollLeft=groupWidth/3;
  scroller.dispatchEvent(new Event('scroll'));
  expect(label.style.left).toBe(initialLabelLeft);
  expect(date.style.left).toBe(initialDateLeft);
  expect(group.style.visibility).toBe('visible');
 }finally{
  runtime.destroy();
  window.innerWidth=originalInnerWidth;
 }
});

it.each([
 ['mobile',390,300],
 ['desktop',1440,880],
])('positions newly opened specialist captions immediately without requiring a horizontal scroll (%s)',(_device,width,panelWidth)=>{
 const originalInnerWidth=window.innerWidth;
 window.innerWidth=width;
 const data=weekFixture('point','2026-10-09') as any;
 const days=data.days.map((day:any,index:number)=>({
  ...day,
  available:['daily','6h','3h','1h'],
  intervals:{daily:[{...data.intervals['24'][index][0],id:`${day.date}-daily-0`,day:index,hour:null}]},
 }));
 const runtime=createForecastRuntime({api:data,days:data.days.map((day:any)=>({...day,name:day.label,date_fa:day.jalali})),points:{[data.subject.slug]:{days}},},[],[],'');
 try{
  document.body.innerHTML=runtime.html('point',{...data.subject,name:data.subject.name},{day:0,time:480,speed:'medium',theme:'dark',scroll:0} as any);
  const panel=document.querySelector<HTMLElement>('.forecast-panel')!;
  Object.defineProperty(panel,'clientWidth',{configurable:true,value:panelWidth});
  runtime.mount({});
  const scroller=document.querySelector<HTMLElement>('.timeline-scroll')!;
  Object.defineProperty(scroller,'clientWidth',{configurable:true,value:panelWidth});
  Object.defineProperty(scroller,'scrollWidth',{configurable:true,value:Number.parseFloat(document.querySelector<HTMLElement>('.timeline-content')!.style.width)});
  scroller.scrollLeft=0;
  scroller.dispatchEvent(new Event('scroll'));
  const before=scroller.scrollLeft;
  document.querySelector<HTMLButtonElement>('[data-v4-expert]')!.click();
  expect(scroller.scrollLeft).toBe(before);
  const captions=[...document.querySelectorAll<SVGGElement>('#v4-experts .metric-caption')];
  expect(captions.length).toBeGreaterThan(0);
  expect(captions.every(caption=>caption.getAttribute('transform')?.startsWith('translate('))).toBe(true);
 }finally{
  runtime.destroy();
  window.innerWidth=originalInnerWidth;
 }
});
