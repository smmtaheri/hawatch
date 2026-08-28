import type { PeriodId } from "../types";

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
  night: { min: 1140, max: 1590, label: "۱۹ تا ۰۳", defaultStart: "20:00", defaultStartMinutes: 1200 },
};

const PERIOD_TICKS: Record<PeriodId, string[]> = {
  morning: ["۰۳:۰۰", "۰۵:۰۰", "۰۷:۰۰", "۰۹:۰۰", "۱۱:۰۰"],
  afternoon: ["۱۱:۰۰", "۱۳:۰۰", "۱۵:۰۰", "۱۷:۰۰", "۱۹:۰۰"],
  night: ["۱۹:۰۰", "۲۱:۰۰", "۲۳:۰۰", "۰۱:۰۰", "۰۳:۰۰"],
};

export function periodTicks(period: PeriodId) {
  return PERIOD_TICKS[period];
}

export function toClock(minutes: number) {
  const clock = minutes % 1440;
  const hour = Math.floor(clock / 60);
  const minute = clock % 60;
  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

export function parseClockToMinutes(clock: string, period: PeriodId) {
  const [hours, minutes] = clock.split(":").map(Number);
  let value = hours * 60 + minutes;
  if (period === "night" && value <= 180) {
    value += 1440;
  }
  const range = PERIOD_RANGES[period];
  return Math.max(range.min, Math.min(range.max, value));
}

export function formatClockDisplay(minutes: number) {
  const fa = "۰۱۲۳۴۵۶۷۸۹";
  const clock = minutes % 1440;
  const hour = Math.floor(clock / 60);
  const minute = clock % 60;
  const hh = String(hour).padStart(2, "0").replace(/\d/g, (d) => fa[Number(d)]);
  const mm = String(minute).padStart(2, "0").replace(/\d/g, (d) => fa[Number(d)]);
  return `${hh}:${mm}`;
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
