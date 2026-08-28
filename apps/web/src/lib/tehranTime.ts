const TEHRAN_TZ = "Asia/Tehran";

const wallClockFormatter = new Intl.DateTimeFormat("en-GB", {
  timeZone: TEHRAN_TZ,
  hour: "numeric",
  minute: "numeric",
  second: "numeric",
  hour12: false,
  hourCycle: "h23",
});

function readPart(parts: Intl.DateTimeFormatPart[], type: Intl.DateTimeFormatPartTypes) {
  return Number(parts.find((part) => part.type === type)?.value ?? 0);
}

/** Tehran wall-clock fields for an API timestamp (independent of browser timezone). */
export function tehranWallClock(iso: string): { hour: number; minute: number; second: number; epochMs: number } {
  const epochMs = Date.parse(iso);
  const parts = wallClockFormatter.formatToParts(new Date(epochMs));
  return {
    hour: readPart(parts, "hour"),
    minute: readPart(parts, "minute"),
    second: readPart(parts, "second"),
    epochMs,
  };
}

export function tehranClockMinutes(iso: string): number {
  const { hour, minute } = tehranWallClock(iso);
  return hour * 60 + minute;
}

export function compareTehranInstants(aIso: string, bIso: string): number {
  return Date.parse(aIso) - Date.parse(bIso);
}

/** ISO-8601 with Asia/Tehran offset for period boundary comparisons. */
export function tehranLocalIso(dateIso: string, hour: number, minute = 0, second = 0): string {
  const hh = String(hour).padStart(2, "0");
  const mm = String(minute).padStart(2, "0");
  const ss = String(second).padStart(2, "0");
  return `${dateIso}T${hh}:${mm}:${ss}+03:30`;
}

export function addTehranCalendarDays(dateIso: string, days: number): string {
  const [y, m, d] = dateIso.split("-").map(Number);
  const date = new Date(Date.UTC(y, m - 1, d + days));
  return date.toISOString().slice(0, 10);
}
