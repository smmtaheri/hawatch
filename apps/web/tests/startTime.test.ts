import { describe, expect, it } from "vitest";
import { buildRouteShareUrl, buildRouteTelegramShareUrl } from "../src/lib/routeShare";
import { parseStartTimeInput, parseClockToMinutes, toClock } from "../src/lib/periods";
import type { RouteForecast } from "../src/types";

const sampleForecast = {
  route: { href: "/routes/tochal-darband", title: "دربند تا توچال" },
  meta: { selected_date: "2026-08-26" },
  period: { id: "morning" },
  start_minutes: 600,
  speed: "متوسط",
  decision: { status: "حرکت مناسب" },
} as RouteForecast;

describe("start time parsing", () => {
  it("accepts ASCII, Persian, and Arabic digit clocks", () => {
    expect(parseStartTimeInput("06:30")).toEqual({ ok: true, wallMinutes: 390 });
    expect(parseStartTimeInput("۰۶:۳۰")).toEqual({ ok: true, wallMinutes: 390 });
    expect(parseStartTimeInput("٠٦:٣٠")).toEqual({ ok: true, wallMinutes: 390 });
  });

  it("accepts legacy bare numeric minutes", () => {
    expect(parseStartTimeInput("360")).toEqual({ ok: true, wallMinutes: 360 });
  });

  it("rejects malformed and out-of-range clocks", () => {
    expect(parseStartTimeInput("12:xx").ok).toBe(false);
    expect(parseStartTimeInput("12:00:00").ok).toBe(false);
    expect(parseStartTimeInput("25:00").ok).toBe(false);
    expect(parseStartTimeInput("12:60").ok).toBe(false);
  });

  it("floors off-step values consistently with backend policy", () => {
    expect(parseClockToMinutes("10:15", "morning")).toBe(600);
    expect(toClock(parseClockToMinutes("۱۰:۱۵", "morning"))).toBe("10:00");
  });
});

describe("route share URLs", () => {
  it("builds canonical ASCII planner URLs", () => {
    const url = buildRouteShareUrl(sampleForecast, "https://hawatch.test");
    expect(url).toBe(
      "https://hawatch.test/routes/tochal-darband?date=2026-08-26&period=morning&start_time=10%3A00&speed=%D9%85%D8%AA%D9%88%D8%B3%D8%B7",
    );
    expect(url).toMatch(/start_time=10(%3A|:)00/);
    expect(url).not.toMatch(/start_time=%D[89ABab]/);
  });

  it("uses the canonical share URL for Telegram", () => {
    const telegram = buildRouteTelegramShareUrl(sampleForecast, "https://hawatch.test");
    const shared = new URL(telegram).searchParams.get("url");
    expect(shared).toBeTruthy();
    expect(decodeURIComponent(shared!)).toContain("/routes/tochal-darband");
    expect(decodeURIComponent(shared!)).toContain("start_time=10:00");
    expect(telegram).not.toContain("window.location");
  });
});
