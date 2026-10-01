import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { buildRouteBackState, buildRoutePointLink, initialPointPlanner } from "../src/lib/routeNavigation";
import { MemoryRouter, Route, Routes, createMemoryRouter, RouterProvider, useSearchParams } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ThemeProvider } from "../src/app/theme";
import { PointDetailPage as PointPage } from "../src/pages/PointDetailPage";
import { RoutePage } from "../src/pages/RoutePage";
import { PointDetailPage } from "../src/pages/PointDetailPage";
import { PERIOD_OPTIONS, PERIOD_RANGES, parseClockToMinutes, periodTicks, toClock } from "../src/lib/periods";
import { classifyAllPeriods, resolveRouteStartMinutes } from "../src/lib/periodState";
import { StartTimeControl } from "../src/components/StartTimeControl";

const pointDays = [
  { date: "2026-08-27", label: "دیروز", jalali: "۶ شهریور", offset: -1, is_yesterday: true, is_today: false, is_past: false, is_future: false, is_current: false },
  { date: "2026-08-28", label: "امروز", jalali: "۷ شهریور", offset: 0, is_yesterday: false, is_today: true, is_past: false, is_future: false, is_current: true },
  { date: "2026-08-29", label: "فردا", jalali: "۸ شهریور", offset: 1, is_yesterday: false, is_today: false, is_past: false, is_future: true, is_current: false },
];

const pointCurrent = {
  time: "۰۰:۰۰",
  hour: 1,
  forecast_at: "2026-08-28T01:00:00+03:30",
  temperature_c: 5,
  temperature_label: "۵°",
  condition: "صاف",
  icon: "☼",
  wind_speed_kmh: 4,
  wind_label: "باد ۴ km/h",
  severity: "normal",
  state: "normal",
  is_yesterday: false,
  is_today: true,
  is_past: false,
  is_current: true,
  is_future: false,
};

const pointMeta = {
  freshness: "ready",
  generated_at: "2026-08-28T00:30:00+03:30",
  current_local_time: "2026-08-28T01:00:00+03:30",
  selected_date: "2026-08-27",
  selected_period: "night",
};

const primaryPointForecast = {
  subject: {
    kind: "point" as const,
    slug: "tochal",
    weather_point_slug: "tochal",
    canonical_href: "/points/tochal",
    name: "قلهٔ توچال",
    elevation_m: 3964,
    elevation_label: "۳۹۶۴ متر",
    latitude: 35.88,
    longitude: 51.42,
    context_label: "کوه",
    hero_image: "/images/touchal-banner-clean.png",
    hero_image_alt: "توچال",
    region: "تهران",
    category: "کوه",
  },
  point: {
    slug: "tochal",
    tile_name: "توچال",
    name: "قلهٔ توچال",
    short_category: "کوه",
    category: "کوه",
    category_key: "mountain",
    region: "تهران",
    elevation_m: 3964,
    elevation_label: "۳۹۶۴ متر",
    image: "/images/touchal-banner-clean.png",
    image_alt: "توچال",
    href: "/points/tochal",
    is_popular: true,
    routes: [],
    weather_point_slug: "tochal",
  },
  hero: { status: "☼　۵°", alert: null },
  forecast: {
    days: pointDays,
    period: { id: "night", label: "شب", range_label: "۱۸ تا ۲۴", headline: "تغییرات شب · هر دو ساعت", hours: [18, 20, 22] },
    current: pointCurrent,
    hourly: [] as typeof pointCurrent[],
    meta: pointMeta,
  },
  metrics: [],
  decision: { chip: "دیروز · جمع‌بندی هواچ", title: "صبح", text: "آرام" },
  related_routes: [],
  related_routes_title: "مسیرهای متصل به توچال",
  updated_label: "امروز",
  empty: false,
  days: pointDays,
  period: { id: "night", label: "شب", range_label: "۱۸ تا ۲۴", headline: "تغییرات شب · هر دو ساعت", hours: [18, 20, 22] },
  current: pointCurrent,
  hourly: [] as typeof pointCurrent[],
  meta: pointMeta,
};

const routeForecast = {
  route: {
    slug: "tochal-darband",
    title: "دربند تا توچال",
    subtitle: "",
    origin: "دربند",
    target_label: "قلهٔ توچال",
    distance_label: "۱۶٫۲ km",
    ascent_label: "۲۲۶۰ m",
    default_start_minutes: 360,
    href: "/routes/tochal-darband",
    target_point: primaryPointForecast.point,
    points: [],
    siblings: [],
  },
  days: primaryPointForecast.forecast.days,
  period: {
    id: "morning",
    label: "صبح",
    range_label: "۰۶ تا ۱۲",
    headline: "تغییرات صبح · هر دو ساعت",
    hours: [6, 8, 10],
    planner_step_minutes: 60,
    planner_start_minutes: 360,
    planner_end_minutes: 720,
    planner_last_start_minutes: 660,
    planner_default_start_minutes: 480,
    planner_slots: [360, 420, 480, 540, 600, 660],
    planner_ticks: ["۰۶:۰۰", "۰۷:۰۰", "۰۸:۰۰", "۰۹:۰۰", "۱۰:۰۰", "۱۱:۰۰"],
  },
  start_minutes: 360,
  start_time: "۰۶:۰۰",
  speed: "متوسط",
  speed_options: ["آرام", "متوسط", "سریع"],
  timing_pending: false,
  points: [
    {
      slug: "tochal-shirpala-shelter",
      name: "شیرپلا",
      elevation_label: "۲۴۵۰ m",
      href: "/points/tochal-shirpala-shelter",
      axis_x: 10,
      axis_y: 50,
      time: "۰۸:۰۰",
      temp: 8,
      wind: 6,
      icon: "☼",
      condition: "صاف",
      state: "normal",
      note: "",
      arrival_minutes: 480,
      weather_available: true,
    },
  ],
  hourly: [
    { time: "۰۳:۰۰", hour: 3, forecast_at: "2026-08-26T03:00:00+03:30", temperature_c: 7, temperature_label: "۷°", condition: "صاف", icon: "☼", wind_speed_kmh: 7, wind_label: "باد ۷ km/h", severity: "normal", state: "normal", is_yesterday: false, is_today: true, is_past: true, is_current: false, is_future: false },
  ],
  hero: { status: "شرایط آرام" },
  stats: [],
  decision: {
    chip: "امروز",
    title: "حرکت",
    status: "مناسب",
    state: "normal",
    summary: "آرام",
    hero_status: "آرام",
    critical_name: "",
    critical_time: "",
    critical_note: "",
    recommendations: [],
    start: "۰۶:۰۰",
    finish: "۱۳:۰۰",
    speed: "متوسط",
  },
  empty: false,
  meta: { freshness: "ready", generated_at: "2026-08-26T05:45:00+03:30", current_local_time: "2026-08-26T06:00:00+03:30", selected_date: "2026-08-26", selected_period: "morning" },
};

const pointForecast = {
  subject: {
    kind: "point" as const,
    slug: "tochal-shirpala-shelter",
    weather_point_slug: "tochal-shirpala-shelter",
    canonical_href: "/points/tochal-shirpala-shelter",
    name: "شیرپلا",
    elevation_m: 2750,
    elevation_label: "۲۴۵۰ متر",
    latitude: 35.855,
    longitude: 51.429,
    context_label: "تهران",
    hero_image: "/images/touchal-banner-clean.png",
    hero_image_alt: "توچال",
    region: "تهران",
    category: "کوه",
  },
  point: {
    slug: "tochal-shirpala-shelter",
    name: "شیرپلا",
    aliases: [],
    kind: "shared",
    elevation_m: 2750,
    elevation_label: "۲۴۵۰ m",
    latitude: 35.855,
    longitude: 51.429,
    status: "approved",
    provenance: "curated",
    href: "/points/tochal-shirpala-shelter",
    canonical_href: "/points/tochal-shirpala-shelter",
  },
  related_routes: [
    {
      slug: "tochal-darband",
      title: "دربند تا توچال",
      trail_label: "مسیر",
      origin: "دربند",
      target_label: "قلهٔ توچال",
      distance_km: 16.2,
      distance_label: "۱۶٫۲ km",
      ascent_m: 2260,
      ascent_label: "۲۲۶۰ m",
      featured: true,
      href: "/routes/tochal-darband",
    },
  ],
  related_routes_title: "مسیرهای عبوری از این نقطه",
  hero: { status: "☼　۷°", alert: null },
  forecast: {
    days: routeForecast.days,
    period: routeForecast.period,
    current: routeForecast.hourly[0],
    hourly: routeForecast.hourly,
    meta: routeForecast.meta,
  },
  metrics: [{ icon: "wind-average", label: "باد میانگین", value: "۷ km/h", note: "", color: "teal" }],
  decision: { chip: "امروز · جمع‌بندی هواچ", title: "صبح مناسب است", text: "آرام" },
  updated_label: "امروز",
  empty: false,
  partial: false,
  days: routeForecast.days,
  period: routeForecast.period,
  current: routeForecast.hourly[0],
  weather: routeForecast.hourly[0],
  hourly: routeForecast.hourly,
  meta: routeForecast.meta,
};

const sarbandForecast = {
  ...pointForecast,
  subject: {
    ...pointForecast.subject,
    slug: "tochal-sarband-square",
    weather_point_slug: "tochal-sarband-square",
    canonical_href: "/points/tochal-sarband-square",
    name: "سربند",
  },
  point: {
    ...pointForecast.point,
    slug: "tochal-sarband-square",
    name: "سربند",
    href: "/points/tochal-sarband-square",
    canonical_href: "/points/tochal-sarband-square",
  },
};

function jsonResponse(data: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: async () => data });
}

function forecastUrl(input: RequestInfo) {
  return String(input);
}

function pointCalls(calls: unknown[][]) {
  return calls.map((call) => forecastUrl(call[0] as RequestInfo)).filter((url) => url.includes("/points/tochal/forecast"));
}

describe("clock and route navigation contracts", () => {
  it("exposes hourly planner ticks for each Iran-time period", () => {
    expect(PERIOD_OPTIONS.map((option) => option.rangeLabel)).toEqual(["۰۰ تا ۰۶", "۰۶ تا ۱۲", "۱۲ تا ۱۸", "۱۸ تا ۲۴"]);
    expect(PERIOD_RANGES.midnight).toMatchObject({ min: 0, max: 360 });
    expect(PERIOD_RANGES.morning).toMatchObject({ min: 360, max: 720 });
    expect(PERIOD_RANGES.noon).toMatchObject({ min: 720, max: 1080 });
    expect(PERIOD_RANGES.night).toMatchObject({ min: 1080, max: 1440 });
    expect(periodTicks("midnight")).toEqual(["۰۰:۰۰", "۰۱:۰۰", "۰۲:۰۰", "۰۳:۰۰", "۰۴:۰۰", "۰۵:۰۰"]);
    expect(periodTicks("morning")).toEqual(["۰۶:۰۰", "۰۷:۰۰", "۰۸:۰۰", "۰۹:۰۰", "۱۰:۰۰", "۱۱:۰۰"]);
    expect(periodTicks("noon")).toEqual(["۱۲:۰۰", "۱۳:۰۰", "۱۴:۰۰", "۱۵:۰۰", "۱۶:۰۰", "۱۷:۰۰"]);
    expect(periodTicks("night")).toEqual(["۱۸:۰۰", "۱۹:۰۰", "۲۰:۰۰", "۲۱:۰۰", "۲۲:۰۰", "۲۳:۰۰"]);
  });

  it("builds route back target with planner params for point links", () => {
    const params = new URLSearchParams("date=2026-08-26&period=morning&start_time=06:00&speed=متوسط");
    const fromRoute = buildRouteBackState(
      { slug: "tochal-darband", title: "دربند تا توچال", href: "/routes/tochal-darband" },
      params,
    );
    const link = buildRoutePointLink("/points/tochal-shirpala-shelter", fromRoute);
    expect(link.pathname).toBe("/points/tochal-shirpala-shelter");
    expect(link.state?.fromRoute.pathname).toBe("/routes/tochal-darband");
    expect(link.state?.fromRoute.search).toContain("start_time=06");
    expect(link.state?.fromRoute.search).toContain("speed=");
  });

  it("does not seed place planner from fromRoute — only explicit URL date/period", () => {
    const planner = initialPointPlanner(
      new URLSearchParams(""),
      {
        slug: "tochal-darband",
        title: "دربند تا توچال",
        pathname: "/routes/tochal-darband",
        search: "?date=2026-08-26&period=noon&start_time=12:00&speed=متوسط",
        href: "/routes/tochal-darband?date=2026-08-26&period=noon&start_time=12:00&speed=متوسط",
      },
    );
    expect(planner).toEqual({ date: undefined, period: undefined });
    expect(
      initialPointPlanner(new URLSearchParams("date=2026-08-26&period=noon"), undefined),
    ).toEqual({ date: "2026-08-26", period: "noon" });
  });

  it("floors off-step and Persian-digit start times", () => {
    expect(parseClockToMinutes("10:15", "morning")).toBe(600);
    expect(parseClockToMinutes("۱۰:۱۵", "morning")).toBe(600);
    expect(parseClockToMinutes("٠٦:٣٠", "morning")).toBe(360);
  });

  it("resolves route start from period default when switching away from current period", () => {
    const at1030 = "2026-08-28T10:30:00+03:30";
    expect(resolveRouteStartMinutes("2026-08-28", "morning", at1030)).toBe(600);
    expect(resolveRouteStartMinutes("2026-08-28", "noon", at1030)).toBe(840);
    expect(resolveRouteStartMinutes("2026-08-28", "night", at1030)).toBe(1200);
  });

  it("keeps the route gauge inside the selected period when input is out of bounds", () => {
    render(
      <StartTimeControl
        minutes={1440}
        min={1080}
        max={1440}
        period="night"
        ticks={["۱۸:۰۰", "۱۹:۰۰", "۲۰:۰۰", "۲۱:۰۰", "۲۲:۰۰", "۲۳:۰۰"]}
        rangeLabel="۱۸ تا ۲۴"
        display="۲۳:۰۰"
        currentMinutes={1380}
        stepMinutes={60}
        onChange={vi.fn()}
        onCommit={vi.fn()}
      />,
    );

    const slider = screen.getByRole("slider", { name: "ساعت شروع حرکت" });
    expect(slider).toHaveAttribute("max", "1380");
    expect(slider).toHaveAttribute("step", "60");
    expect(slider).toHaveValue("1380");
    expect(document.querySelector(".gauge-fill")).toHaveStyle({ width: "100%" });
    expect(document.querySelector(".gauge-dot")).toHaveStyle({ right: "100%" });
  });

  it("builds one-hour planner ticks from period bounds", () => {
    expect(periodTicks("morning")).toEqual([
      "۰۶:۰۰",
      "۰۷:۰۰",
      "۰۸:۰۰",
      "۰۹:۰۰",
      "۱۰:۰۰",
      "۱۱:۰۰",
    ]);
    expect(periodTicks("noon")).toEqual([
      "۱۲:۰۰",
      "۱۳:۰۰",
      "۱۴:۰۰",
      "۱۵:۰۰",
      "۱۶:۰۰",
      "۱۷:۰۰",
    ]);
    expect(periodTicks("night")).toEqual([
      "۱۸:۰۰",
      "۱۹:۰۰",
      "۲۰:۰۰",
      "۲۱:۰۰",
      "۲۲:۰۰",
      "۲۳:۰۰",
    ]);
  });

});
