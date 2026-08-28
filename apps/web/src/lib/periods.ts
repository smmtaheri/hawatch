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

/** Last valid 30-minute start slot; period ends are exclusive at `max`. */
export function periodLastStartMinutes(period: PeriodId): number {
  if (period === "night") return PERIOD_RANGES.night.max;
  return PERIOD_RANGES[period].max - 30;
}

export function clampStartMinutes(minutes: number, period: PeriodId) {
  const range = PERIOD_RANGES[period];
  return Math.max(range.min, Math.min(periodLastStartMinutes(period), minutes));
}

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

export function parseClockToMinutes(clock: string, period: PeriodId) {
  const parsed = parseStartTimeInput(clock);
  if (!parsed.ok) {
    return PERIOD_RANGES[period].defaultStartMinutes;
  }
  let value = parsed.wallMinutes;
  if (period === "night" && value <= 180) {
    value += 1440;
  }
  value = Math.floor(value / 30) * 30;
  return clampStartMinutes(value, period);
}

export function isValidStartTimeInput(raw: string) {
  return parseStartTimeInput(raw).ok;
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
