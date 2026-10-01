import type { PointDayBundle, RouteDayBundle } from "../types";

type Bundle = PointDayBundle | RouteDayBundle;
type Entry = { data: Bundle; expires: number; epoch: number };
const entries = new Map<string, Entry>();
const pending = new Map<string, Promise<Bundle>>();
let epoch = 0;

export function clearDayCache() {
  epoch += 1;
  entries.clear();
  pending.clear();
}
if (typeof window !== "undefined")
  window.addEventListener("hawatch-auth-changed", clearDayCache);

export function dayCacheKey(kind: string, slug: string, date?: string) {
  return JSON.stringify([epoch, kind, slug, date || "default"]);
}
export function readDayCache<T extends Bundle>(key: string): T | null {
  const entry = entries.get(key);
  return entry && entry.epoch === epoch && entry.expires > Date.now()
    ? (entry.data as T)
    : null;
}
function metaOf(data: Bundle) {
  return "forecast" in data ? data.forecast.meta : data.meta;
}
function revisionOf(data: Bundle) {
  return JSON.stringify([
    metaOf(data).last_generated_time,
    data.forecast_access,
    data.cache_expires_at,
  ]);
}
export function fetchDayCache<T extends Bundle>(
  key: string,
  load: () => Promise<T>,
  kind: string,
  slug: string,
): Promise<T> {
  const cached = readDayCache<T>(key);
  if (cached) return Promise.resolve(cached);
  const existing = pending.get(key);
  if (existing) return existing as Promise<T>;
  const requestEpoch = epoch;
  const request = load()
    .then((data) => {
      if (epoch !== requestEpoch) return data;
      const revision = revisionOf(data);
      for (const [oldKey, entry] of entries) {
        if (revisionOf(entry.data) !== revision) entries.delete(oldKey);
      }
      const meta = metaOf(data);
      const serverMs = Date.parse(meta.current_local_time);
      const nextHour = 3600000 - ((serverMs + 3.5 * 3600000) % 3600000);
      const expires =
        Date.now() +
        Math.min(
          data.cache_max_age_seconds * 1000,
          nextHour,
          data.cache_expires_at
            ? Math.max(0, Date.parse(data.cache_expires_at) - serverMs)
            : Infinity,
        );
      const entry = { data, expires, epoch };
      entries.set(key, entry);
      entries.set(dayCacheKey(kind, slug, meta.selected_date), entry);
      while (entries.size > 40) entries.delete(entries.keys().next().value!);
      return data;
    })
    .finally(() => {
      if (pending.get(key) === request) pending.delete(key);
    });
  pending.set(key, request);
  return request;
}
export function expireDayCache(key: string) {
  const entry = entries.get(key);
  for (const [alias, value] of entries)
    if (alias === key || (entry && value === entry)) entries.delete(alias);
}
