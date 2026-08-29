import { describe, expect, it } from "vitest";
import { periodLastStartMinutes } from "../src/lib/periods";
import {
  classifyPeriod,
  gaugeCurrentMinutes,
  tehranMinutesInPeriod,
} from "../src/lib/periodState";

describe("periodState", () => {
  it("classifies Tehran period boundaries without a hardcoded sample hour", () => {
    const at1030 = "2026-08-28T10:30:00+03:30";
    expect(classifyPeriod("morning", "2026-08-28", at1030)).toBe("current");
    expect(classifyPeriod("afternoon", "2026-08-28", at1030)).toBe("future");
    expect(classifyPeriod("night", "2026-08-27", at1030)).toBe("past");

    const at0130 = "2026-08-28T01:30:00+03:30";
    expect(classifyPeriod("night", "2026-08-27", at0130)).toBe("current");
    expect(classifyPeriod("morning", "2026-08-28", at0130)).toBe("future");
  });

  it("uses Tehran wall clock for extended night minutes", () => {
    expect(tehranMinutesInPeriod("2026-08-28T01:30:00+03:30", "night")).toBe(1530);
  });

  it("caps gauge minutes at the last valid start slot with configured hourly flooring", () => {
    expect(gaugeCurrentMinutes("2026-08-28", "morning", "2026-08-28T10:45:00+03:30")).toBe(600);
    expect(periodLastStartMinutes("morning")).toBe(600);
    expect(gaugeCurrentMinutes("2026-08-28", "morning", "2026-08-28T10:29:00+03:30")).toBe(600);
  });
});
