import type { PeriodId, PlannerPeriodInfo } from "../types";

/** Fallback only when route API has not yet provided planner bounds/step. */
export const PLANNER_TIME_STEP_MINUTES = 60;

export const PERIOD_OPTIONS: Array<{ id: PeriodId; label: string; rangeLabel: string }> = [
  { id: "morning", label: "صبح", rangeLabel: "۰۳ تا ۱۱" },
  { id: "afternoon", label: "بعدازظهر", rangeLabel: "۱۱ تا ۱۹" },
  { id: "night", label: "شب", rangeLabel: "۱۹ تا ۰۳" },
];

export function asPeriodId(value: string | null | undefined): PeriodId | undefined {
  return PERIOD_OPTIONS.some((option) => option.id === value) ? (value as PeriodId) : undefined;
}

export const PERIOD_RANGES: Record<
  PeriodId,
  { min: number; max: number; label: string; defaultStart: string; defaultStartMinutes: number }
> = {
  morning: { min: 180, max: 660, label: "۰۳ تا ۱۱", defaultStart: "06:00", defaultStartMinutes: 360 },
  afternoon: { min: 660, max: 1140, label: "۱۱ تا ۱۹", defaultStart: "12:00", defaultStartMinutes: 720 },
  night: { min: 1140, max: 1620, label: "۱۹ تا ۰۳", defaultStart: "20:00", defaultStartMinutes: 1200 },
};

export type PlannerBounds = {
  stepMinutes: number;
  min: number;
  maxExclusive: number;
  lastStart: number;
  defaultStartMinutes: number;
  ticks: string[];
  slots: number[];
  label: string;
};

export function formatClockDisplay(minutes: number) {
  const fa = "۰۱۲۳۴۵۶۷۸۹";
  const clock = minutes % 1440;
  const hour = Math.floor(clock / 60);
  const minute = clock % 60;
  const hh = String(hour).padStart(2, "0").replace(/\d/g, (d) => fa[Number(d)]);
  const mm = String(minute).padStart(2, "0").replace(/\d/g, (d) => fa[Number(d)]);
  return `${hh}:${mm}`;
}

export function buildPlannerSlots(min: number, lastStart: number, step: number): number[] {
  const slots: number[] = [];
  for (let value = min; value <= lastStart; value += step) {
    slots.push(value);
  }
  return slots;
}

/** Prefer API period planner fields; fall back to local PERIOD_RANGES + step. */
export function resolvePlannerBounds(period: PeriodId, apiPeriod?: PlannerPeriodInfo | null): PlannerBounds {
  const fallback = PERIOD_RANGES[period];
  const step = apiPeriod?.planner_step_minutes ?? PLANNER_TIME_STEP_MINUTES;
  const min = apiPeriod?.planner_start_minutes ?? fallback.min;
  const maxExclusive = apiPeriod?.planner_end_minutes ?? fallback.max;
  const lastStart = apiPeriod?.planner_last_start_minutes ?? maxExclusive - step;
  const defaultStartMinutes = apiPeriod?.planner_default_start_minutes ?? fallback.defaultStartMinutes;
  const slots =
    apiPeriod?.planner_slots && apiPeriod.planner_slots.length
      ? apiPeriod.planner_slots
      : buildPlannerSlots(min, lastStart, step);
  const ticks =
    apiPeriod?.planner_ticks && apiPeriod.planner_ticks.length
      ? apiPeriod.planner_ticks
      : slots.map((slot) => formatClockDisplay(slot));
  return {
    stepMinutes: step,
    min,
    maxExclusive,
    lastStart,
    defaultStartMinutes,
    ticks,
    slots,
    label: apiPeriod?.range_label ?? fallback.label,
  };
}

/** Last valid planner start slot; period ends are exclusive at `max`. */
export function periodLastStartMinutes(period: PeriodId, apiPeriod?: PlannerPeriodInfo | null): number {
  return resolvePlannerBounds(period, apiPeriod).lastStart;
}

export function clampStartMinutes(minutes: number, period: PeriodId, apiPeriod?: PlannerPeriodInfo | null) {
  const bounds = resolvePlannerBounds(period, apiPeriod);
  return Math.max(bounds.min, Math.min(bounds.lastStart, minutes));
}

/** Generate hourly (or step) ticks from period bounds — no hard-coded two-hour arrays. */
export function periodTicks(period: PeriodId, apiPeriod?: PlannerPeriodInfo | null) {
  return resolvePlannerBounds(period, apiPeriod).ticks;
}

export function toClock(minutes: number) {
  const clock = minutes % 1440;
  const hour = Math.floor(clock / 60);
  const minute = clock % 60;
  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

function normalizeAsciiClock(clock: string) {
  const fa = "۰۱۲۳۴۵۶۷۸۹";
  const ar = "٠١٢٣٤٥٦٧٨٩";
  return clock
    .trim()
    .replace(/[۰-۹]/g, (digit) => String(fa.indexOf(digit)))
    .replace(/[٠-٩]/g, (digit) => String(ar.indexOf(digit)));
}

export type StartTimeParseResult =
  | { ok: true; wallMinutes: number }
  | { ok: false; reason: "empty" | "malformed" | "range" };

/** Parse start_time query input; mirrors backend parse_start_time_value. */
export function parseStartTimeInput(raw: string): StartTimeParseResult {
  const cleaned = normalizeAsciiClock(raw);
  if (!cleaned) return { ok: false, reason: "empty" };

  if (cleaned.includes(":")) {
    if (cleaned.split(":").length !== 2) return { ok: false, reason: "malformed" };
    const [hoursRaw, minutesRaw] = cleaned.split(":");
    if (!/^\d{1,2}$/.test(hoursRaw) || !/^\d{2}$/.test(minutesRaw)) {
      return { ok: false, reason: "malformed" };
    }
    const hours = Number(hoursRaw);
    const minutes = Number(minutesRaw);
    if (hours > 23 || minutes > 59) return { ok: false, reason: "range" };
    return { ok: true, wallMinutes: hours * 60 + minutes };
  }

  if (/^\d+$/.test(cleaned)) {
    return { ok: true, wallMinutes: Number(cleaned) };
  }

  return { ok: false, reason: "malformed" };
}

export function parseClockToMinutes(clock: string, period: PeriodId, apiPeriod?: PlannerPeriodInfo | null) {
  const bounds = resolvePlannerBounds(period, apiPeriod);
  const parsed = parseStartTimeInput(clock);
  if (!parsed.ok) {
    return bounds.defaultStartMinutes;
  }
  let value = parsed.wallMinutes;
  if (period === "night" && value <= 180) {
    value += 1440;
  }
  value = Math.floor(value / bounds.stepMinutes) * bounds.stepMinutes;
  return clampStartMinutes(value, period, apiPeriod);
}

export function isValidStartTimeInput(raw: string) {
  return parseStartTimeInput(raw).ok;
}

export function appendRouteContext(href: string, params: URLSearchParams) {
  const url = new URL(href, "http://local");
  for (const key of ["date", "period", "start_time", "speed"]) {
    const value = params.get(key);
    if (value) url.searchParams.set(key, value);
  }
  return `${url.pathname}${url.search}`;
}

export function buildForecastParams(options: {
  date?: string;
  period?: string;
  start_time?: string;
  speed?: string;
  includeDate?: boolean;
  includePeriod?: boolean;
}) {
  const params: Record<string, string | undefined> = {};
  if (options.includeDate && options.date) params.date = options.date;
  if (options.includePeriod && options.period) params.period = options.period;
  if (options.start_time) params.start_time = options.start_time;
  if (options.speed) params.speed = options.speed;
  return params;
}
