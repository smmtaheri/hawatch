import { describe, expect, it } from "vitest";
import { tehranClockMinutes, tehranWallClock } from "../src/lib/tehranTime";

const TEHRAN_MORNING = "2026-08-28T10:30:00+03:30";

describe("tehranTime", () => {
  it("extracts Asia/Tehran wall clock from offset timestamps", () => {
    const clock = tehranWallClock(TEHRAN_MORNING);
    expect(clock.hour).toBe(10);
    expect(clock.minute).toBe(30);
    expect(tehranClockMinutes(TEHRAN_MORNING)).toBe(630);
  });

  it("does not rely on the browser local timezone getters", () => {
    const iso = TEHRAN_MORNING;
    const localHour = new Date(iso).getHours();
    const localMinute = new Date(iso).getMinutes();
    const wall = tehranWallClock(iso);

    expect(wall.hour).toBe(10);
    expect(wall.minute).toBe(30);

    if (localHour !== 10 || localMinute !== 30) {
      expect(localHour * 60 + localMinute).not.toBe(630);
    }
    expect(wall.hour * 60 + wall.minute).toBe(630);
  });
});
