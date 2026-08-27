export type Freshness = "ready" | "stale" | "partial";
export type Severity = "normal" | "change" | "critical";
export type PeriodId = "morning" | "afternoon";

export interface ApiMeta {
  schema_version: string;
  timezone: string;
  current_local_time: string;
  current_local_hour: number;
  selected_date: string;
  selected_period: PeriodId | string;
  data_mode: string;
  provider: string;
  source: string;
  seed_version: string;
  freshness: Freshness;
  generated_at: string;
  last_generated_time: string | null;
  forecast_validity?: { valid_from: string | null; valid_to: string | null };
  selected_start_time?: string;
  selected_speed?: string;
  timing_pending?: boolean;
  timing_status?: "curated" | "estimated" | "pending" | string;
}

export interface DestinationSummary {
  slug: string;
  tile_name: string;
  name: string;
  short_category: string;
  category: string;
  category_key: string;
  region: string;
  elevation_m: number;
  elevation_label: string;
  image: string;
  image_alt: string;
  href: string;
  is_popular: boolean;
}

export interface RouteSummary {
  slug: string;
  title: string;
  trail_label: string;
  origin: string;
  destination_label: string;
  distance_km: number | null;
  distance_label: string;
  ascent_m: number | null;
  ascent_label: string;
  featured: boolean;
  href: string;
  timing_pending?: boolean;
  timing_status?: "curated" | "estimated" | "pending" | string;
}

export interface DayInfo {
  date: string;
  label: string;
  jalali: string;
  offset: number;
  is_yesterday: boolean;
  is_today: boolean;
  is_past: boolean;
  is_future: boolean;
  is_current: boolean;
}

export interface HourlyReading {
  time: string;
  hour: number;
  temperature_c: number;
  temperature_label: string;
  condition: string;
  icon: string;
  wind_speed_kmh: number;
  wind_label: string;
  severity: Severity;
  state: Severity;
  snowfall_cm?: number | null;
  cloud_cover_pct?: number | null;
  uv_index?: number | null;
  fields_unavailable?: string[];
  is_yesterday: boolean;
  is_today: boolean;
  is_past: boolean;
  is_current: boolean;
  is_future: boolean;
}

export interface Metric {
  icon: string;
  label: string;
  value: string;
  note: string;
  color: string;
}

export interface DestinationForecast {
  destination: DestinationSummary & { routes: RouteSummary[] };
  days: DayInfo[];
  period: { id: PeriodId; label: string; range_label: string; headline: string; hours: number[] };
  current: HourlyReading | null;
  hourly: HourlyReading[];
  metrics: Metric[];
  hero: { status: string; alert: string };
  decision: { chip: string; title: string; text: string };
  updated_label: string;
  empty: boolean;
  meta: ApiMeta;
}

export interface RoutePointView {
  slug: string;
  name: string;
  elevation_label: string;
  href: string;
  axis_x: number;
  axis_y: number;
  time: string;
  temp: number | null;
  wind: number | null;
  icon: string;
  condition: string;
  state: Severity;
  note: string;
  arrival_minutes: number | null;
  timing_pending?: boolean;
  timing_estimated?: boolean;
}

export interface RouteForecast {
  route: {
    slug: string;
    title: string;
    subtitle: string;
    origin: string;
    destination_label: string;
    distance_label: string;
    ascent_label: string;
    default_start_minutes: number;
    parent: DestinationSummary;
    points: RoutePointView[];
    siblings: RouteSummary[];
    href: string;
  };
  days: DayInfo[];
  period: { id: PeriodId; label: string; range_label: string; hours: number[] };
  start_minutes: number;
  start_time: string;
  speed: string;
  speed_options: string[];
  points: RoutePointView[];
  hourly: HourlyReading[];
  hero: { status: string };
  stats: { label: string; value: string }[];
  timing_pending?: boolean;
  timing_status?: "curated" | "estimated" | "pending" | string;
  decision: {
    chip: string;
    title: string;
    status: string;
    state: Severity;
    summary: string;
    hero_status: string;
    critical_name: string;
    critical_time: string;
    critical_note: string;
    recommendations: string[];
    start: string;
    finish: string;
    speed: string;
    timing_pending?: boolean;
  };
  empty: boolean;
  meta: ApiMeta;
}
