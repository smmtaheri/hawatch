import {expect, it} from 'vitest';
import {charts} from '../src/features/week/vendor/charts';

const layout={compact:true,captionWidth:100};
const slot={felt:2,actual:3,min:-2.5,max:8,felt_min:-3.5,felt_max:9,level:0,uv_index:0,heat_index_c:39.9,heat_index_status:'available'};
function render(points:any[],experts=true){const root=document.createElement('div');root.innerHTML=charts.rows(points,points.map((_,i)=>120+i*120),120*points.length,experts,false,layout);return root;}

it('shows LTR min/max pairs for daily/6h/3h columns and reserves their rows at 1h',()=>{
 const root=render([0,1,2,3].map(level=>({...slot,level})));
 for(const key of ['felt-range','actual']){
  const row=root.querySelector(`[data-metric="${key}"]`)!;
  expect(row.querySelectorAll('[data-temperature-range]')).toHaveLength(3);
  expect(row.querySelector('[data-temperature-range]')?.getAttribute('direction')).toBe('ltr');
 }
 expect(root.querySelector('[data-metric="felt-range"]')?.textContent).toContain('−۴°/۹°');
 expect(root.querySelector('[data-metric="actual"]')?.textContent).toContain('−۳°/۸°');
 expect(root.querySelectorAll('[data-range]')).toHaveLength(0);
 expect(root.querySelector('.metric-label-sub')).toBeNull();
 expect(root.querySelector('[data-metric="felt-range"]')?.getAttribute('style')).toBe('height:27px');
});

it('appends only UV and heat rows, keeping fixed visual scales and zero distinct from unavailable',()=>{
 const root=render([{...slot,uv_index:0},{...slot,uv_index:null},{...slot,uv_index:8},{...slot,uv_index:11}]);
 const metrics=[...root.querySelectorAll('[data-metric]')].map(row=>row.getAttribute('data-metric'));
 expect(metrics).toEqual(['felt-range','felt','wind','rain','actual','gust','direction','humidity','visibility','freezing','uv_index','heat_index_c']);
 const uv=root.querySelector('[data-metric="uv_index"]')!;
 expect(uv.querySelectorAll('g:not(.metric-caption) circle[opacity="0.9"]')).toHaveLength(9);
 expect(uv.textContent).toContain('۰');
 expect(uv.querySelectorAll('.no-data')).toHaveLength(1);
 expect(uv.querySelectorAll('path')).toHaveLength(0);
 const alone=render([slot]).querySelector('[data-heat-value]')!;
 const mixed=render([slot,{...slot,heat_index_c:60}]).querySelector('[data-heat-value]')!;
 expect(alone.getAttribute('height')).toBe(mixed.getAttribute('height'));
 expect(root.querySelector('[data-metric="heat_index_c"]')?.textContent).toContain('۳۹٫۹°');
});

it('explains unavailable heat, never substitutes temperature, and uses the shared critical metric',()=>{
 const root=render([{...slot,heat_index_c:null,heat_index_status:'not_applicable'},{...slot,heat_index_c:null,heat_index_status:'missing'},{...slot,heat_index_c:40,hazards:['heat_index_c']}]);
 const row=root.querySelector('[data-metric="heat_index_c"]')!;
 expect(row.querySelectorAll('.no-data')).toHaveLength(2);
 expect(row.textContent).toContain('خارج از دامنه');
 expect(row.textContent).toContain('دادهٔ کافی');
 expect(row.querySelector('[data-heat-value="40"]')?.getAttribute('fill')).toBe('var(--red)');
});

it('does not add indicator rows or change actual-temperature whiskers in route/share charts',()=>{
 const root=document.createElement('div');root.innerHTML=charts.rows([slot],[100],200,true,true);
 expect(root.querySelector('[data-metric="uv_index"]')).toBeNull();
 expect(root.querySelector('[data-metric="heat_index_c"]')).toBeNull();
 expect(root.querySelector('[data-metric="felt-range"]')).toBeNull();
 expect(root.querySelector('[data-range]')).not.toBeNull();
});
