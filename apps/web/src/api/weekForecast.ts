import type { SimilarDestinationSummary } from '../types';
import { takeInitialPageRequest } from '../lib/pageLoad';

type Day = { date: string; label: string; jalali: string };
type Subject = { slug: string; name?: string; title?: string; elevation_m?: number; region?: string; distance_km?: number; ascent_m?: number; descent_m?: number; seo_indexable?: boolean };
export type HeatIndexStatus = 'available' | 'not_applicable' | 'missing';
export type WeekInterval = {
  from: string; to: string; hour: number;
  felt: number | null; felt_min: number | null; felt_max: number | null;
  actual: number | null; min: number | null; max: number | null;
  wind: number | null; gust: number | null; rain: number | null;
  direction: number | null; humidity: number | null; visibility: number | null; freezing: number | null;
  uv_index: number | null; heat_index_c: number | null; heat_index_status: HeatIndexStatus;
  weather: string; condition: string; weather_at: string | null;
  warnings: Array<{ severity: string; metrics: string[]; metric_severities?: Record<string, string> }>;
  complete: boolean;
};
export type Week = { kind: 'point' | 'route'; subject: Subject; days: Day[]; range_start: string; range_end: string; last_generated_at: string | null; stale_after_hours: number; cache_max_age_seconds: number; related_routes?: Subject[]; related_routes_title?: string; related_destinations?: SimilarDestinationSummary[]; related_destinations_title?: string; intervals?: Record<string, WeekInterval[][]>; points?: Array<{ slug: string; name: string }>; timing_pending?: boolean };

const cache = new Map<string, { data: Week; expires: number }>();
const pending = new Map<string, Promise<Week>>();
let prepared: { key: string; request: Promise<Week>; succeeded: boolean } | null = null;
export function clearWeekCache() { cache.clear(); pending.clear(); prepared = null; }

function tehranDate() {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Tehran', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());
}

export function loadWeek(kind: string, slug: string): Promise<Week> {
  const key = `${kind}:${slug}:${tehranDate()}`;
  if (prepared?.key === key) {
    const initial = prepared;
    queueMicrotask(() => { if (prepared === initial) prepared = null; });
    if (initial.succeeded && (!cache.has(key) || cache.get(key)!.expires <= Date.now())) return requestWeek(kind, slug);
    return initial.request;
  }
  return requestWeek(kind, slug);
}

function requestWeek(kind: string, slug: string): Promise<Week> {
  const key = `${kind}:${slug}:${tehranDate()}`, existing = cache.get(key);
  if (existing && existing.expires > Date.now()) return Promise.resolve(existing.data);
  const loading = pending.get(key);
  if (loading) return loading;
  const url = `/api/v1/${kind === 'point' ? 'points' : 'routes'}/${encodeURIComponent(slug)}/forecast/week/`;
  const response = takeInitialPageRequest(url, 'omit') ?? fetch(url, { credentials: 'omit', cache: 'no-cache' });
  const request = response.then(async r => {
    if (!r.ok) throw Object.assign(new Error(r.status === 404 ? 'نقطه یا مسیر پیدا نشد' : 'دریافت پیش‌بینی ممکن نشد'), { status: r.status });
    const data = await r.json() as Week;
    const age = Number(r.headers.get('Age') || 0);
    const midnight = Date.parse(`${data.range_start}T00:00:00+03:30`) + 86400000;
    const ttl = Math.max(0, Math.min(data.cache_max_age_seconds - age, (midnight - Date.now()) / 1000));
    cache.set(key, { data, expires: Date.now() + ttl * 1000 });
    while (cache.size > 3) cache.delete(cache.keys().next().value!);
    return data;
  }).finally(() => { if (pending.get(key) === request) pending.delete(key); });
  pending.set(key, request);
  return request;
}

/** Runs outside lazy components so CSS/download delays never postpone weather. */
export function prepareForecastPage(pathname: string) {
  const match = pathname.match(/^\/(points|routes)\/([a-z0-9-]+)\/?$/);
  if (!match) { prepared = null; return; }
  const kind = match[1] === 'points' ? 'point' : 'route', key = `${kind}:${match[2]}:${tehranDate()}`;
  if (prepared?.key === key) return;
  const request = requestWeek(kind, match[2]);
  const initial = { key, request, succeeded: false };
  prepared = initial;
  // Preserve a failed initial read for the page too. Mounting must not silently retry it.
  void request.then(() => { initial.succeeded = true; }, () => {});
}
