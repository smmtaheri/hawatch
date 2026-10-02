import { describe, expect, it } from "vitest";
import { shortDaySummary } from "../src/lib/shortDaySummary";
import type { WeatherWarning } from "../src/types";

const warning = (code: string, severity: WeatherWarning["severity"]): WeatherWarning => ({
  code, severity, label: "توضیح طولانی", metrics: [], reason: "توضیح بیشتر",
  start_at: "2026-10-02T10:00:00Z", end_at: "2026-10-02T11:00:00Z",
  scope: "weather", rule_version: "walking-v2",
});

describe("short day summary", () => {
  it("keeps ordinary weather without adding a warning", () => {
    expect(shortDaySummary("ابری")).toBe("ابری");
  });
  it("shows a single dominant red warning despite repeated hourly intervals", () => {
    expect(shortDaySummary("باران", [warning("wind", "change"), warning("wind", "critical"), warning("rain", "change")]))
      .toBe("باران، باد شدید");
  });
  it("uses a short yellow label and avoids repeating sky hazards", () => {
    expect(shortDaySummary("ابری", [warning("wind", "change")])).toBe("ابری، تندباد");
    expect(shortDaySummary("رعدوبرق", [warning("lightning", "critical")])).toBe("رعدوبرق");
  });
  it("limits the phrase to three words when the sky description is long", () => {
    expect(shortDaySummary("عمدتاً صاف", [warning("wind", "critical")])).toBe("باد شدید");
  });
});
