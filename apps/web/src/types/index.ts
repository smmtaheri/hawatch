export type Freshness = "ready" | "stale" | "partial";
export type Severity = "normal" | "change" | "critical";
export type PeriodId = "morning" | "afternoon" | "night";

export interface WindAlert {
  code: "windy" | "gale";
  label: string;
  severity: Severity;
}

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
  forecast_at?: string;
  hour: number;
  temperature_c: number;
  temperature_label: string;
  condition: string;
  icon: string;
  wind_speed_kmh: number;
  wind_label: string;
  wind_alert?: WindAlert | null;
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

export const SPECIALIST_METRIC_ICON_NAMES = [
  "wind-average",
  "wind-gust",
  "visibility",
  "freezing-level",
  "cloud-base",
  "uv-index",
  "precipitation",
  "sunrise-sunset",
] as const;

export type SpecialistMetricIconName = (typeof SPECIALIST_METRIC_ICON_NAMES)[number];

export interface Metric {
  /** Stable semantic icon name rendered from the specialist icon sprite. */
  icon: SpecialistMetricIconName | string;
  label: string;
  value: string;
  note: string;
  color: string;
}

export type PlaceKind = "destination" | "point";

export interface PlaceSubject {
  kind: PlaceKind;
  slug: string;
  weather_point_slug?: string;
  canonical_href: string;
  name: string;
  aliases?: string[];
  elevation_m: number | null;
  elevation_label: string;
  latitude: number;
  longitude: number;
  context_label: string;
  hero_image: string;
  hero_image_alt: string;
  region?: string;
  category?: string;
}

export interface PlannerPeriodInfo {
  id: PeriodId;
  label: string;
  range_label: string;
  headline: string;
  hours: number[];
  start_minutes?: number;
  end_minutes?: number;
  default_start?: number;
  planner_step_minutes?: number;
  planner_start_minutes?: number;
  planner_end_minutes?: number;
  planner_last_start_minutes?: number;
  planner_default_start_minutes?: number;
  planner_ticks?: string[];
  planner_slots?: number[];
}

/** First-class shared Forecast Place contract for destination and point endpoints. */
export interface PlaceForecastResponse {
  subject: PlaceSubject;
  hero: { status: string; alert: string };
  forecast: {
    days: DayInfo[];
    period: PlannerPeriodInfo;
    current: HourlyReading | null;
    hourly: HourlyReading[];
    meta: ApiMeta;
  };
  metrics: Metric[];
  decision: { chip: string; title: string; text: string };
  related_routes: RouteSummary[];
  related_routes_title?: string;
  empty: boolean;
  partial?: boolean;
  /** Temporary backend compatibility aliases — prefer `forecast.*`. */
  days?: DayInfo[];
  period?: PlannerPeriodInfo;
  current?: HourlyReading | null;
  weather?: HourlyReading | null;
  hourly?: HourlyReading[];
  meta?: ApiMeta;
  destination?: DestinationSummary & { routes?: RouteSummary[]; weather_point_slug?: string | null };
  point?: WeatherPointSummary & { canonical_href?: string };
  related_destinations?: DestinationSummary[];
  updated_label?: string;
}

export interface DestinationForecast extends PlaceForecastResponse {
  destination: DestinationSummary & { routes: RouteSummary[] };
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
  arrival_at?: string | null;
  forecast_at?: string | null;
  timing_pending?: boolean;
  timing_estimated?: boolean;
  timing_confidence?: string;
  timing_uncertainty_minutes?: number | null;
  weather_available?: boolean;
  latitude?: number | null;
  longitude?: number | null;
  elevation_m?: number | null;
  weather_point_slug?: string | null;
}

export interface RoutePointForecast {
  point: RoutePointView & {
    route_slug: string;
    route_title: string;
    route_href: string;
    destination: DestinationSummary;
    has_weather_point: boolean;
    has_forecast: boolean;
  };
  days: DayInfo[];
  period: { id: PeriodId; label: string; range_label: string; headline: string; hours: number[] };
  weather: HourlyReading | null;
  hourly: HourlyReading[];
  empty: boolean;
  partial: boolean;
  back_href: string;
  canonical_href?: string | null;
  weather_point_slug?: string | null;
  meta: ApiMeta;
}

export interface WeatherPointSummary {
  slug: string;
  name: string;
  aliases: string[];
  kind: string;
  elevation_m: number | null;
  elevation_label: string;
  latitude: number;
  longitude: number;
  status: string;
  provenance: string;
  href: string;
  canonical_href?: string;
  destination: DestinationSummary | null;
}

export interface PointForecast extends PlaceForecastResponse {
  point: WeatherPointSummary;
  related_destinations: DestinationSummary[];
}

export interface SearchSuggestion {
  type: "destination" | "point";
  slug: string;
  label: string;
  hint: string;
  href: string;
  match_kind: "name" | "alias";
}

export interface RouteFromState {
  slug: string;
  title: string;
  /** Full return URL including planner query params when present. */
  href: string;
  pathname: string;
  search: string;
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
  period: PlannerPeriodInfo;
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
  timing_confidence?: string;
  timing_uncertainty_minutes?: number | null;
  timing_version?: string;
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
