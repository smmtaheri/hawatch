import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { clearWeekCache, loadWeek, prepareForecastPage } from '../src/api/weekForecast';
import { api } from '../src/api/client';
import { weekFixture } from './fixtures/week';

const day = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Tehran', year:'numeric', month:'2-digit', day:'2-digit' }).format(new Date());
beforeEach(() => { clearWeekCache(); delete window.__hawatchInitialPageRequest; document.getElementById('forecast-initial-data')?.remove(); });
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); delete window.__hawatchInitialPageRequest; document.getElementById('forecast-initial-data')?.remove(); });

function embed(payload: ReturnType<typeof weekFixture>, age = 0) {
  const script = document.createElement('script');
  script.id = 'forecast-initial-data'; script.type = 'application/json';
  script.textContent = JSON.stringify({payload,rendered_at:new Date(Date.now()-age*1000).toISOString()});
  document.body.append(script);
}

it('renders the anonymous HTML forecast without an additional initial API read', async () => {
  const fetch = vi.fn(); vi.stubGlobal('fetch',fetch);
  const payload = weekFixture('point',day); embed(payload);
  prepareForecastPage('/points/tochal');
  const [first,second] = await Promise.all([loadWeek('point','tochal'),loadWeek('point','tochal')]);
  expect(first).toEqual(payload); expect(second).toEqual(payload);
  expect(fetch).not.toHaveBeenCalled();
  expect(document.getElementById('forecast-initial-data')).toBeNull();
});

it('subtracts time spent in the HTML cache from the ordinary forecast TTL', async () => {
  vi.useFakeTimers(); const payload=weekFixture('point',day); embed(payload,90);
  const fetch=vi.fn().mockResolvedValue(new Response(JSON.stringify(payload))); vi.stubGlobal('fetch',fetch);
  expect(await loadWeek('point','tochal')).toEqual(payload);
  vi.advanceTimersByTime(31000);
  await loadWeek('point','tochal');
  expect(fetch).toHaveBeenCalledTimes(1);
});

it.each(['expired','wrong-subject','previous-day','malformed'])('does not adopt %s HTML data', async mode => {
  const payload=weekFixture('point',day), initial=structuredClone(payload);
  if(mode==='wrong-subject')initial.subject.slug='another-point';
  if(mode==='previous-day')initial.range_start='2000-01-01';
  embed(initial,mode==='expired'?121:0);
  if(mode==='malformed')document.getElementById('forecast-initial-data')!.textContent='bad JSON';
  const fetch=vi.fn().mockResolvedValue(new Response(JSON.stringify(payload))); vi.stubGlobal('fetch',fetch);
  expect(await loadWeek('point','tochal')).toEqual(payload);
  expect(fetch).toHaveBeenCalledTimes(1);
});

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
  expect(fetch).toHaveBeenCalledWith('/api/v1/routes/tochal-darband/forecast/week/',{credentials:'omit',cache:'no-cache'});
});

it('consumes the initial catalog read once even with simultaneous page effects', async()=>{
  const fetch=vi.fn();vi.stubGlobal('fetch',fetch);
  const payload={destinations:[],pagination:{page:1}};
  window.__hawatchInitialPageRequest={url:new URL('/api/v1/destinations/?page=1',window.location.origin).href,credentials:'same-origin',response:Promise.resolve(new Response(JSON.stringify(payload)))};
  const [first,second]=await Promise.all([api.destinations(),api.destinations()]);
  expect(first).toEqual(payload);expect(second).toEqual(payload);
  expect(fetch).not.toHaveBeenCalled();
});
