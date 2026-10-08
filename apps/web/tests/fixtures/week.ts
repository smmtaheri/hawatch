// Small synthetic API fixtures, never imported by the application.
import {Week} from '../../src/features/week/WeekForecastPage';
export function weekFixture(kind:'point'|'route',day:string,options:{pending?:boolean;stale?:boolean}={}):Week{
 const days=Array.from({length:8},(_,i)=>({date:new Date(Date.parse(day+'T00:00:00Z')+i*86400000).toISOString().slice(0,10),label:i===0?'امروز':i===1?'فردا':['شنبه','یکشنبه','دوشنبه','سه‌شنبه','چهارشنبه','پنجشنبه'][i-2],jalali:'۱۷ مهر'}));
 const reading={felt:-7,actual:91,min:90,max:92,wind:20,gust:30,rain:0,humidity:50,visibility:10,freezing:3000,direction:0,weather:'clear',weather_at:day+'T12:00:00+03:30',warnings:[],complete:true};
 const base:Week={kind,subject:{slug:kind==='point'?'tochal':'tochal-darband',name:kind==='point'?'قلهٔ توچال':undefined,title:kind==='route'?'دربند تا توچال':undefined,elevation_m:3964,distance_km:10.3,ascent_m:2150,descent_m:50},days,range_start:day,range_end:days[7].date,last_generated_at:options.stale?'2020-01-01T00:00:00Z':new Date().toISOString(),stale_after_hours:7,cache_max_age_seconds:120,related_routes:[{slug:'tochal-darband',title:'دربند تا توچال'},{slug:'tochal-kolakchal',title:'جمشیدیه تا توچال'}]};
 if(kind==='point')base.intervals=Object.fromEntries([24,6,3,1].map(step=>[String(step),days.map(()=>Array.from({length:24/step},(_,i)=>({...reading,hour:i*step})))]));
 else{
  const api=base as any;api.timing_pending=!!options.pending;api.points=[{slug:'tochal-sarband-square',name:'میدان سربند',weather_point_id:1,distance_km:0},{slug:'tochal',name:'قلهٔ توچال',weather_point_id:2,distance_km:10.3}];
  api.offsets=options.pending?{slow:[],medium:[],fast:[]}:{slow:[0,395],medium:[0,315],fast:[0,250]};
  api.records=[{apparent_temperature_c:-7,temperature_c:91,wind_speed_kmh:20,wind_gust_kmh:30,precipitation_mm:0,weather_code:'clear',forecast_at:day+'T08:00:00+03:30',warnings:[]}];
  api.plans=Object.fromEntries(days.flatMap((_,i)=>['slow','medium','fast'].flatMap(speed=>Array.from({length:24},(_,hour)=>[`${i}:${speed}:${hour}`,{records:options.pending?[]:[0,0],equipment:[]}]))));api.equipment=[];
 }
 return base;
}
