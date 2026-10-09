import {afterEach,expect,it,vi} from 'vitest';
import {createForecastRuntime} from '../src/features/week/vendor/runtime';
import {weekFixture} from './fixtures/week';

afterEach(()=>{document.body.innerHTML='';});

it('prepares route equipment only when opened and reuses it until the plan changes',()=>{
 const data=weekFixture('route','2026-10-09') as any;
 const item={id:'windstopper',name:'وینداستاپر',reason:'باد',evidence:[{point:1,at:'2026-10-09T08:00:00+03:30'}]};
 const reads=vi.fn(()=>[item]);
 Object.defineProperty(data,'equipment',{get:reads});
 for(const plan of Object.values(data.plans) as any[])plan.equipment=[0];
 const runtime=createForecastRuntime({api:data,days:data.days.map((d:any)=>({...d,name:d.label,date_fa:d.jalali})),points:{}},data.points,[],'');
 try{
  document.body.innerHTML=runtime.html('route',{...data.subject,name:data.subject.title},{day:0,time:480,speed:'medium',theme:'dark'});
  runtime.mount({});
  expect(reads).not.toHaveBeenCalled();
  document.querySelector<HTMLButtonElement>('[data-v4-gear]')!.click();
  expect(reads).toHaveBeenCalledTimes(1);
  expect(document.querySelector('.gear-list')?.textContent).toContain('وینداستاپر');
  document.querySelector<HTMLButtonElement>('[data-v4-menu]')!.click();
  expect(reads).toHaveBeenCalledTimes(1);
  document.querySelector<HTMLButtonElement>('[data-v4-speed="fast"]')!.click();
  expect(reads).toHaveBeenCalledTimes(2);
 }finally{runtime.destroy();}
});
