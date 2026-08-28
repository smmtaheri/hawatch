import type { PeriodId } from "../types";

export const PERIOD_OPTIONS: Array<{ id: PeriodId; label: string; rangeLabel: string }> = [
  { id: "morning", label: "صبح", rangeLabel: "۰۲ تا ۱۰" },
  { id: "afternoon", label: "بعدازظهر", rangeLabel: "۱۰ تا ۱۸" },
  { id: "night", label: "شب", rangeLabel: "۱۸ تا ۰۲" },
];

export const PERIOD_RANGES: Record<PeriodId, { min: number; max: number; label: string; defaultStart: string }> = {
  morning: { min: 120, max: 600, label: "۰۲ تا ۱۰", defaultStart: "06:00" },
  afternoon: { min: 600, max: 1080, label: "۱۰ تا ۱۸", defaultStart: "12:00" },
  night: { min: 1080, max: 1560, label: "۱۸ تا ۰۲", defaultStart: "20:00" },
};

const PERIOD_TICKS: Record<PeriodId, string[]> = {
  morning: ["۰۲:۰۰", "۰۴:۰۰", "۰۶:۰۰", "۰۸:۰۰", "۱۰:۰۰"],
  afternoon: ["۱۰:۰۰", "۱۲:۰۰", "۱۴:۰۰", "۱۶:۰۰", "۱۸:۰۰"],
  night: ["۱۸:۰۰", "۲۰:۰۰", "۲۲:۰۰", "۰۰:۰۰", "۰۲:۰۰"],
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
