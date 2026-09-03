import type { PeriodId, PlannerPeriodInfo } from "../types";
import {
  parseClockToMinutes,
  PERIOD_RANGES,
  periodLastStartMinutes,
  resolvePlannerBounds,
} from "./periods";
import { addTehranCalendarDays, compareTehranInstants, tehranClockMinutes, tehranLocalIso } from "./tehranTime";

export type PeriodPhase = "past" | "current" | "future";

function periodBoundsIso(selectedDate: string, period: PeriodId): { start: string; end: string } {
  const range = PERIOD_RANGES[period];
  const startHour = Math.floor(range.min / 60);
  const endDay = range.max >= 1440 ? addTehranCalendarDays(selectedDate, 1) : selectedDate;
  const endHour = (range.max % 1440) / 60;
  return {
    start: tehranLocalIso(selectedDate, startHour),
    end: tehranLocalIso(endDay, endHour),
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
    midnight: classifyPeriod("midnight", selectedDate, currentLocalTime),
    morning: classifyPeriod("morning", selectedDate, currentLocalTime),
    noon: classifyPeriod("noon", selectedDate, currentLocalTime),
    night: classifyPeriod("night", selectedDate, currentLocalTime),
  };
}

/** Tehran wall-clock minutes used by the route gauge. Each period is a same-day window. */
export function tehranMinutesInPeriod(currentLocalTime: string, period: PeriodId): number {
  return tehranClockMinutes(currentLocalTime);
}

export function gaugeCurrentMinutes(
  selectedDate: string,
  period: PeriodId,
  currentLocalTime: string | undefined,
  apiPeriod?: PlannerPeriodInfo | null,
): number | undefined {
  if (!currentLocalTime) return undefined;
  if (classifyPeriod(period, selectedDate, currentLocalTime) !== "current") return undefined;
  const minutes = tehranMinutesInPeriod(currentLocalTime, period);
  const bounds = resolvePlannerBounds(period, apiPeriod);
  const floored = Math.floor(minutes / bounds.stepMinutes) * bounds.stepMinutes;
  return Math.max(bounds.min, Math.min(bounds.lastStart, floored));
}

/** Canonical route start: explicit clock, live floored time, or period default. */
export function resolveRouteStartMinutes(
  selectedDate: string,
  period: PeriodId,
  currentLocalTime: string | undefined,
  explicitStart?: string,
  apiPeriod?: PlannerPeriodInfo | null,
): number {
  if (explicitStart) {
    return parseClockToMinutes(explicitStart, period, apiPeriod);
  }
  if (currentLocalTime && classifyPeriod(period, selectedDate, currentLocalTime) === "current") {
    const live = gaugeCurrentMinutes(selectedDate, period, currentLocalTime, apiPeriod);
    if (live !== undefined) return live;
  }
  return resolvePlannerBounds(period, apiPeriod).defaultStartMinutes;
}

export { periodLastStartMinutes, PERIOD_RANGES };
