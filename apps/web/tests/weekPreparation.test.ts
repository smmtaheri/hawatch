import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { clearWeekCache, loadWeek, prepareForecastPage } from '../src/api/weekForecast';
import { api } from '../src/api/client';
import { weekFixture } from './fixtures/week';

const day = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Tehran', year:'numeric', month:'2-digit', day:'2-digit' }).format(new Date());
beforeEach(() => { clearWeekCache(); delete window.__hawatchInitialPageRequest; });
afterEach(() => { vi.unstubAllGlobals(); delete window.__hawatchInitialPageRequest; });

it('adopts the HTML request and shares it across preparation, lazy mount, and StrictMode', async () => {
  const fetch = vi.fn();vi.stubGlobal('fetch',fetch);
  const response = Promise.resolve(new Response(JSON.stringify(weekFixture('point',day)), {status:200}));
  window.__hawatchInitialPageRequest={url:new URL('/api/v1/points/tochal/forecast/week/',window.location.origin).href,credentials:'omit',response};
  prepareForecastPage('/points/tochal');
  const first=loadWeek('point','tochal'),second=loadWeek('point','tochal');
  expect(first).toBe(second);
  expect((await first).subject.slug).toBe('tochal');
  expect(fetch).not.toHaveBeenCalled();
  expect(window.__hawatchInitialPageRequest).toBeUndefined();
});

it('keeps a failed preparation for the delayed page mount instead of silently retrying', async () => {
  const fetch=vi.fn().mockResolvedValue(new Response('{}',{status:503}));vi.stubGlobal('fetch',fetch);
  prepareForecastPage('/points/tochal');
  await new Promise(resolve=>setTimeout(resolve,0));
  await expect(loadWeek('point','tochal')).rejects.toThrow('دریافت پیش‌بینی ممکن نشد');
  expect(fetch).toHaveBeenCalledTimes(1);
});

it('does not prepare weather for hubs or turn planner changes into extra fetches', async () => {
  const fetch=vi.fn().mockImplementation(()=>Promise.resolve(new Response(JSON.stringify(weekFixture('route',day)))));vi.stubGlobal('fetch',fetch);
  prepareForecastPage('/routes');prepareForecastPage('/routes/page/2');
  expect(fetch).not.toHaveBeenCalled();
  prepareForecastPage('/routes/tochal-darband');prepareForecastPage('/routes/tochal-darband');
  await loadWeek('route','tochal-darband');
  expect(fetch).toHaveBeenCalledTimes(1);
});

it('consumes the initial catalog read once even with simultaneous page effects', async()=>{
  const fetch=vi.fn();vi.stubGlobal('fetch',fetch);
  const payload={destinations:[],pagination:{page:1}};
  window.__hawatchInitialPageRequest={url:new URL('/api/v1/destinations/?page=1',window.location.origin).href,credentials:'same-origin',response:Promise.resolve(new Response(JSON.stringify(payload)))};
  const [first,second]=await Promise.all([api.destinations(),api.destinations()]);
  expect(first).toEqual(payload);expect(second).toEqual(payload);
  expect(fetch).not.toHaveBeenCalled();
});
