export type Freshness = "ready" | "stale" | "partial";
export type Severity = "normal" | "change" | "critical";
export type PeriodId = "midnight" | "morning" | "noon" | "night";

export interface CatalogCounts {
  points: number;
  routes: number;
}

export interface WeatherWarning {
  code: string;
  label: string;
  severity: Severity;
  metrics: string[];
  metric_severities?: Record<string, Severity>;
  reason: string;
  start_at: string;
  end_at: string;
  scope: "weather";
  rule_version: string;
}

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
  catalog_counts?: CatalogCounts;
}

export interface PointSummary {
  slug: string;
  tile_name: string;
  name: string;
  short_category: string;
  category: string;
  category_key: string;
  place_type?: string;
  region: string;
  elevation_m: number | null;
  elevation_label: string;
  image: string;
  image_alt: string;
  href: string;
  is_popular: boolean;
  seo_indexable?: boolean;
}

export interface DestinationPage {
  destinations: PointSummary[];
  pagination: {
    page: number;
    page_size: number;
    total: number;
    has_next: boolean;
    next_page: number | null;
    next_href: string | null;
    previous_href: string | null;
  };
}

export interface RoutePage {
  routes: RouteSummary[];
  empty: boolean;
  pagination?: {
    page: number;
    page_size: number;
    total: number;
    has_next: boolean;
    next_page: number | null;
    next_href: string | null;
    previous_href: string | null;
  };
}

export interface RouteSummary {
  slug: string;
  title: string;
  trail_label: string;
  origin: string;
  target_label: string;
  distance_km: number | null;
  distance_label: string;
  ascent_m: number | null;
  ascent_label: string;
  featured: boolean;
  href: string;
  timing_pending?: boolean;
  timing_status?: "curated" | "estimated" | "pending" | string;
}

export interface SimilarDestinationSummary {
  slug: string;
  name: string;
  short_label: string;
  short_category: string;
  category: string;
  place_type: string;
  category_key: string;
  region: string;
  elevation_m: number | null;
  elevation_label: string;
  href: string;
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
  access?: "available" | "login_required" | "plan_required";
}

export interface ForecastAccess {
  viewer: "anonymous" | "member";
  plan_title: string | null;
  display_day_count: number;
  visible_days_from_yesterday: number;
  available_through: string;
}

export interface ForecastPlanSummary {
  code: string;
  title: string;
  tier: "free" | "paid" | string;
  duration_months: number | null;
  visible_days_from_yesterday: number;
  is_default?: boolean;
}

export interface HourlyReading {
  time: string;
  forecast_at?: string;
  hour: number;
  temperature_c: number;
  temperature_label: string;
  apparent_temperature_c?: number | null;
  apparent_temperature_label?: string;
  condition: string;
  icon: string;
  wind_speed_kmh: number | null;
  wind_label: string;
  wind_alert?: WindAlert | null;
  warnings?: WeatherWarning[];
  data_quality?: "complete" | "partial" | "unavailable";
  missing_inputs?: string[];
  wind_chill_c?: number | null;
  heat_index_c?: number | null;
  relative_humidity_pct?: number | null;
  policy_version?: string;
  severity: Severity;
  state: Severity;
  precipitation_probability?: number | null;
  precipitation_mm?: number | null;
  rain_mm?: number | null;
  snowfall_cm?: number | null;
  visibility_km?: number | null;
  freezing_level_m?: number | null;
  cloud_cover_pct?: number | null;
  uv_index?: number | null;
  fields_unavailable?: string[];
  weather_code?: string | number | null;
  is_day?: boolean | null;
  wind_gust_kmh?: number | null;
  wind_direction_label?: string;
  cloud_base_m?: number | null;
  is_yesterday: boolean;
  is_today: boolean;
  is_past: boolean;
  is_current: boolean;
  is_future: boolean;
}

export const SPECIALIST_METRIC_ICON_NAMES = [
  "temperature",
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

export type PlaceKind = "point";

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
  seo_title?: string;
  seo_description?: string;
  seo_subtitle?: string;
  seo_h1?: string;
  seo_indexable?: boolean;
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

/** Shared forecast contract for point pages. */
export interface PlaceForecastResponse {
  subject: PlaceSubject;
  hero: { status: string; alert: string | null };
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
  related_destinations?: SimilarDestinationSummary[];
  related_destinations_title?: string;
  empty: boolean;
  partial?: boolean;
  forecast_access?: ForecastAccess;
  /** Temporary backend compatibility aliases — prefer `forecast.*`. */
  days?: DayInfo[];
  period?: PlannerPeriodInfo;
  current?: HourlyReading | null;
  weather?: HourlyReading | null;
  hourly?: HourlyReading[];
  meta?: ApiMeta;
  point?: WeatherPointSummary & { canonical_href?: string };
  updated_label?: string;
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
  temp_absolute?: number | null;
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
  warnings?: WeatherWarning[];
  data_quality?: "complete" | "partial" | "unavailable";
  latitude?: number | null;
  longitude?: number | null;
  elevation_m?: number | null;
  weather_point_slug?: string | null;
  weather_code?: string | number | null;
  is_day?: boolean | null;
}

export interface WeatherPointSummary {
  slug: string;
  name: string;
  kind: string;
  elevation_m: number | null;
  elevation_label: string;
  latitude: number;
  longitude: number;
  status: string;
  provenance: string;
  href: string;
  canonical_href?: string;
  page_name?: string;
  short_label?: string;
  place_type?: string;
  identity_summary?: string;
  importance?: string;
  name_status?: string;
  source_urls?: string[];
  aliases: string[];
  tile_name?: string;
  category?: string;
  category_key?: string;
  region?: string;
  image?: string;
  image_alt?: string;
  seo_indexable?: boolean;
}

export interface PointForecast extends PlaceForecastResponse {
  point: WeatherPointSummary;
}

export interface SearchSuggestion {
  type: "point" | "route";
  slug: string;
  label: string;
  hint: string;
  href: string;
  match_kind: "name" | "alias";
  category_key?: string;
  place_type?: string;
}

export interface CatalogSearchIndex {
  revision: string;
  points: Array<{
    slug: string;
    label: string;
    terms: string[];
    hint: string;
    href: string;
    category_key: string;
    place_type: string;
    primary: boolean;
  }>;
  routes: Array<{
    slug: string;
    label: string;
    terms: string[];
    hint: string;
    href: string;
  }>;
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
    seo_title?: string;
    seo_description?: string;
    origin: string;
    target_label: string;
    distance_label: string;
    ascent_label: string;
    default_start_minutes: number;
    target_point: PointSummary | null;
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
  hero: { status: string | null };
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
    hero_status: string | null;
    critical_name: string;
    critical_time: string;
    critical_note: string;
    recommendations: string[];
    /** Stable equipment icon keys for the share/decision card. */
    gear?: string[];
    start: string;
    finish: string;
    speed: string;
    timing_pending?: boolean;
  };
  empty: boolean;
  meta: ApiMeta;
  forecast_access?: ForecastAccess;
}

export interface PointDayBundle extends PlaceForecastResponse {
  periods: Record<PeriodId, Pick<PlaceForecastResponse["forecast"], "period" | "hourly" | "current"> & { empty: boolean; partial: boolean }>;
  daily_summary: {
    apparent_min_c: number | null;
    apparent_max_c: number | null;
    condition: string;
    severity: Severity;
    weather_code: string | null;
    forecast_at: string | null;
    complete: boolean;
    wind_alert?: WindAlert | null;
    warnings?: WeatherWarning[];
    policy_version?: string;
  };
  data_revision: string;
  cache_max_age_seconds: number;
  cache_expires_at?: string | null;
}

export interface RouteDayBundle extends RouteForecast {
  periods: Record<PeriodId, PlannerPeriodInfo>;
  plans: Record<string, { points: Partial<RoutePointView>[]; decision: RouteForecast["decision"]; stats: RouteForecast["stats"]; hero: RouteForecast["hero"] }>;
  data_revision: string;
  cache_max_age_seconds: number;
  cache_expires_at?: string | null;
  coverage: { from: string; to: string; access_through: string };
}
