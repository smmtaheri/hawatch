import type { PeriodId } from "../types";
import { parseClockToMinutes, PERIOD_RANGES, periodLastStartMinutes } from "./periods";
import { addTehranCalendarDays, compareTehranInstants, tehranClockMinutes, tehranLocalIso } from "./tehranTime";

export type PeriodPhase = "past" | "current" | "future";

function periodBoundsIso(selectedDate: string, period: PeriodId): { start: string; end: string } {
  if (period === "morning") {
    return {
      start: tehranLocalIso(selectedDate, 3),
      end: tehranLocalIso(selectedDate, 11),
    };
  }
  if (period === "afternoon") {
    return {
      start: tehranLocalIso(selectedDate, 11),
      end: tehranLocalIso(selectedDate, 19),
    };
  }
  return {
    start: tehranLocalIso(selectedDate, 19),
    end: tehranLocalIso(addTehranCalendarDays(selectedDate, 1), 3),
  };
}

export function classifyPeriod(period: PeriodId, selectedDate: string, currentLocalTime: string): PeriodPhase {
  const { start, end } = periodBoundsIso(selectedDate, period);
  if (compareTehranInstants(currentLocalTime, end) >= 0) return "past";
  if (compareTehranInstants(currentLocalTime, start) >= 0 && compareTehranInstants(currentLocalTime, end) < 0) {
    return "current";
  }
  return "future";
}

export function classifyAllPeriods(
  selectedDate: string,
  currentLocalTime: string,
): Record<PeriodId, PeriodPhase> {
  return {
    morning: classifyPeriod("morning", selectedDate, currentLocalTime),
    afternoon: classifyPeriod("afternoon", selectedDate, currentLocalTime),
    night: classifyPeriod("night", selectedDate, currentLocalTime),
  };
}

/** Extended minutes within the period window (night wraps past midnight). Uses Asia/Tehran wall clock. */
export function tehranMinutesInPeriod(currentLocalTime: string, period: PeriodId): number {
  let minutes = tehranClockMinutes(currentLocalTime);
  if (period === "night" && minutes <= 180) {
    minutes += 1440;
  }
  return minutes;
}

export function gaugeCurrentMinutes(
  selectedDate: string,
  period: PeriodId,
  currentLocalTime: string | undefined,
): number | undefined {
  if (!currentLocalTime) return undefined;
  if (classifyPeriod(period, selectedDate, currentLocalTime) !== "current") return undefined;
  const minutes = tehranMinutesInPeriod(currentLocalTime, period);
  const range = PERIOD_RANGES[period];
  const maxStart = periodLastStartMinutes(period);
  const floored = Math.floor(minutes / 30) * 30;
  return Math.max(range.min, Math.min(maxStart, floored));
}

/** Canonical route start: explicit clock, live floored time, or period default. */
export function resolveRouteStartMinutes(
  selectedDate: string,
  period: PeriodId,
  currentLocalTime: string | undefined,
  explicitStart?: string,
): number {
  if (explicitStart) {
    return parseClockToMinutes(explicitStart, period);
  }
  if (currentLocalTime && classifyPeriod(period, selectedDate, currentLocalTime) === "current") {
    const live = gaugeCurrentMinutes(selectedDate, period, currentLocalTime);
    if (live !== undefined) return live;
  }
  return PERIOD_RANGES[period].defaultStartMinutes;
}
