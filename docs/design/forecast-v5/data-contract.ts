/** Integration model: adapter to the existing Hawatch API; not a deployed endpoint. */
export type Theme = 'light' | 'dark';
export type Resolution = 'daily' | '6h' | '3h' | '1h';
export type Speed = 'slow' | 'medium' | 'fast';
export type Metric = 'felt' | 'actual' | 'wind' | 'gust' | 'rain' | 'direction' | 'humidity' | 'visibility' | 'freezing';
export interface SnapshotMeta {
  schema_version: number; snapshot_id: string; issued_at: string;
  expires_at?: string; time_zone: string; forecast_revision?: string;
  units: { temperature: 'C'; wind: 'km/h'; rain: 'mm per interval'; visibility: 'km'; freezing: 'm AMSL' };
  demo_only?: boolean;
}
export interface ForecastValues {
  felt: number | null; actual: number | null; min: number | null; max: number | null;
  wind: number | null; gust: number | null; rain: number | null;
  direction: number | null; humidity: number | null; visibility: number | null;
  freezing: number | null; weather: string; hazards: Metric[];
}
export interface ForecastInterval extends ForecastValues {
  hour: number | null; // local 0..23, null for daily
  start_at?: string; end_at?: string; // recommended offset-aware product timestamps
}
export interface ForecastDay {
  id: string; name: string; date_fa: string; iso: string;
  available: Resolution[];
  intervals: Partial<Record<Resolution, ForecastInterval[]>>;
}
export interface PointWeekResponse extends SnapshotMeta {
  point_id: string; days: ForecastDay[]; // eight local dates, including today
}
export interface RoutePointMeta {
  id: string; name: string; short_label?: string;
  latitude?: number; longitude?: number; elevation_m?: number;
  cumulative_distance_km: number;
}
export interface RouteWeekDay {
  local_date: string; hourly_points: ForecastValues[][]; // [24][point_order.length]
}
export interface RouteWeekResponse extends SnapshotMeta {
  route_id: string; route_name: string; geometry_revision: string;
  point_order: string[]; points: RoutePointMeta[]; days: RouteWeekDay[];
  distance_km: number; ascent_m: number; descent_m: number;
  itinerary: { offsets_minutes_by_speed: Record<Speed, number[]> };
}
export interface RouteSelection {
  route_id: string; departure_date: string; departure_time: string;
  time_zone: string; speed: Speed;
}
export interface RouteSummary {
  start_at: string; arrival_at: string; speed_label_fa: string;
  duration_minutes: number; distance_km: number; ascent_m: number; descent_m: number;
}
export interface RouteSnapshot {
  snapshot_id: string; selection: RouteSelection; route_name: string;
  forecast_revision: string; geometry_revision: string; expires_at?: string;
  points: (RoutePointMeta & ForecastValues & { arrival_at: string })[];
  summary: RouteSummary;
}
export interface RouteShareRequest { snapshot: RouteSnapshot; }
export interface RouteShareResponse {
  share_id: string; short_url: string; snapshot_id: string; expires_at?: string;
}
export interface TimelineState {
  resolution_by_day: Record<string, Resolution>; expert_open: boolean;
  anchor: { day_id: string; hour: number | null; screen_x: number } | null;
}
export interface EquipmentRecommendation {
  equipment_id: string; name_fa: string; reason_fa: string; condition_ids: string[];
}
/** Fixture JSON shape; the production adapter may return only the requested record. */
export interface DemoWeekResponse extends SnapshotMeta {
  points: Record<string, { days: ForecastDay[] }>;
  routes: Record<string, {
    distance_km: number; ascent_m: number; descent_m: number;
    distances_km: number[]; demo_distances: boolean; days: RouteWeekDay[];
  }>;
}
