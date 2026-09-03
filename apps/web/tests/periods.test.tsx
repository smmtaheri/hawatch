import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { buildRouteBackState, buildRoutePointLink, initialDestinationPlanner } from "../src/lib/routeNavigation";
import { MemoryRouter, Route, Routes, createMemoryRouter, RouterProvider, useSearchParams } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ThemeProvider } from "../src/app/theme";
import { DestinationPage } from "../src/pages/DestinationPage";
import { RoutePage } from "../src/pages/RoutePage";
import { PointDetailPage } from "../src/pages/PointDetailPage";
import { PERIOD_OPTIONS, PERIOD_RANGES, parseClockToMinutes, periodTicks, toClock } from "../src/lib/periods";
import { classifyAllPeriods, resolveRouteStartMinutes } from "../src/lib/periodState";
import { StartTimeControl } from "../src/components/StartTimeControl";

const destinationDays = [
  { date: "2026-08-27", label: "دیروز", jalali: "۶ شهریور", offset: -1, is_yesterday: true, is_today: false, is_past: false, is_future: false, is_current: false },
  { date: "2026-08-28", label: "امروز", jalali: "۷ شهریور", offset: 0, is_yesterday: false, is_today: true, is_past: false, is_future: false, is_current: true },
  { date: "2026-08-29", label: "فردا", jalali: "۸ شهریور", offset: 1, is_yesterday: false, is_today: false, is_past: false, is_future: true, is_current: false },
];

const destinationCurrent = {
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

const destinationMeta = {
  freshness: "ready",
  generated_at: "2026-08-28T00:30:00+03:30",
  current_local_time: "2026-08-28T01:00:00+03:30",
  selected_date: "2026-08-27",
  selected_period: "night",
};

const destinationForecast = {
  subject: {
    kind: "destination" as const,
    slug: "tochal",
    weather_point_slug: "tochal_summit",
    canonical_href: "/destination/tochal",
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
  destination: {
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
    href: "/destination/tochal",
    is_popular: true,
    routes: [],
    weather_point_slug: "tochal_summit",
  },
  hero: { status: "☼　الان در توچال　۵°　·　صاف", alert: "آرام" },
  forecast: {
    days: destinationDays,
    period: { id: "night", label: "شب", range_label: "۱۸ تا ۲۴", headline: "تغییرات شب · هر دو ساعت", hours: [18, 20, 22] },
    current: destinationCurrent,
    hourly: [] as typeof destinationCurrent[],
    meta: destinationMeta,
  },
  metrics: [],
  decision: { chip: "دیروز · جمع‌بندی هواچ", title: "صبح", text: "آرام" },
  related_routes: [],
  related_routes_title: "مسیرهای منتهی به توچال",
  updated_label: "امروز",
  empty: false,
  days: destinationDays,
  period: { id: "night", label: "شب", range_label: "۱۸ تا ۲۴", headline: "تغییرات شب · هر دو ساعت", hours: [18, 20, 22] },
  current: destinationCurrent,
  hourly: [] as typeof destinationCurrent[],
  meta: destinationMeta,
};

const routeForecast = {
  route: {
    slug: "tochal-darband",
    title: "دربند تا توچال",
    subtitle: "",
    origin: "دربند",
    destination_label: "قلهٔ توچال",
    distance_label: "۱۶٫۲ km",
    ascent_label: "۲۲۶۰ m",
    default_start_minutes: 360,
    href: "/routes/tochal-darband",
    parent: destinationForecast.destination,
    points: [],
    siblings: [],
  },
  days: destinationForecast.forecast.days,
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
    destination: routeForecast.route.parent,
  },
  related_destinations: [routeForecast.route.parent],
  related_routes: [
    {
      slug: "tochal-darband",
      title: "دربند تا توچال",
      trail_label: "مسیر",
      origin: "دربند",
      destination_label: "قلهٔ توچال",
      distance_km: 16.2,
      distance_label: "۱۶٫۲ km",
      ascent_m: 2260,
      ascent_label: "۲۲۶۰ m",
      featured: true,
      href: "/routes/tochal-darband",
    },
  ],
  related_routes_title: "مسیرهای عبوری از این نقطه",
  hero: { status: "☼　در شیرپلا　۷°　·　صاف", alert: "✓　شرایط فعلاً آرام‌تر است" },
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

function destinationCalls(calls: unknown[][]) {
  return calls.map((call) => forecastUrl(call[0] as RequestInfo)).filter((url) => url.includes("/destinations/tochal/forecast"));
}

describe("periods and route planner", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    fetchMock.mockImplementation((input: RequestInfo) => {
      const url = forecastUrl(input);
      if (url.includes("/destinations/tochal/forecast")) return jsonResponse(destinationForecast);
      if (url.includes("/routes/tochal-darband/forecast")) return jsonResponse(routeForecast);
      if (url.includes("/points/tochal-shirpala-shelter/forecast")) return jsonResponse(pointForecast);
      if (url.includes("/points/tochal-sarband-square/forecast")) return jsonResponse(sarbandForecast);
      if (url.includes("/points/tochal_summit/forecast")) {
        return jsonResponse({
          ...pointForecast,
          subject: {
            ...pointForecast.subject,
            kind: "point",
            slug: "tochal_summit",
            canonical_href: "/destination/tochal",
            name: "قلهٔ توچال",
          },
          point: {
            ...pointForecast.point,
            slug: "tochal_summit",
            name: "قلهٔ توچال",
            kind: "destination",
            href: "/destination/tochal",
            canonical_href: "/destination/tochal",
          },
        });
      }
      return jsonResponse({}, false, 404);
    });
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders four period buttons", async () => {
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/routes/tochal-darband?date=2026-08-26&period=morning"]}>
          <Routes>
            <Route path="/routes/:slug" element={<RoutePage />} />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>,
    );
    await screen.findByRole("heading", { name: "دربند تا توچال" });
    expect(PERIOD_OPTIONS).toHaveLength(4);
    expect(screen.getByRole("button", { name: /^شب/ })).toBeInTheDocument();
    expect(document.querySelectorAll(".daypart-toggle small")).toHaveLength(0);
  });

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

  it("does not send period=morning on no-query initial destination load", async () => {
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/destination/tochal"]}>
          <Routes>
            <Route path="/destination/:slug" element={<DestinationPage />} />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>,
    );
    await screen.findByRole("heading", { name: "قلهٔ توچال" });
    const destinationRequest = destinationCalls(fetchMock.mock.calls)[0];
    expect(destinationRequest).toBeDefined();
    expect(destinationRequest).not.toContain("period=morning");
    expect(destinationRequest).not.toContain("period=");
    expect(destinationCalls(fetchMock.mock.calls)).toHaveLength(1);
  });

  it("renders night selected from backend default", async () => {
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/destination/tochal"]}>
          <Routes>
            <Route path="/destination/:slug" element={<DestinationPage />} />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>,
    );
    await screen.findByRole("heading", { name: "قلهٔ توچال" });
    expect(screen.getByRole("button", { name: /^شب/ })).toHaveAttribute("aria-pressed", "true");
  });

  it("keeps explicit query period on destination load", async () => {
    fetchMock.mockImplementation((input: RequestInfo) => {
      const url = forecastUrl(input);
      if (url.includes("period=noon")) {
        return jsonResponse({
          ...destinationForecast,
          meta: { ...destinationForecast.meta, selected_period: "noon" },
          period: { id: "noon", label: "ظهر", range_label: "۱۲ تا ۱۸", headline: "ظهر", hours: [12, 14, 16] },
          forecast: {
            ...destinationForecast.forecast,
            period: { id: "noon", label: "ظهر", range_label: "۱۲ تا ۱۸", headline: "ظهر", hours: [12, 14, 16] },
            meta: { ...destinationForecast.forecast.meta, selected_period: "noon" },
          },
        });
      }
      return jsonResponse(destinationForecast);
    });
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/destination/tochal?period=noon"]}>
          <Routes>
            <Route path="/destination/:slug" element={<DestinationPage />} />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>,
    );
    await screen.findByRole("heading", { name: "قلهٔ توچال" });
    const destinationRequest = destinationCalls(fetchMock.mock.calls).find((url) => url.includes("period=noon"));
    expect(destinationRequest).toBeDefined();
    expect(screen.getByRole("button", { name: /^ظهر/ })).toHaveAttribute("aria-pressed", "true");
  });

  it("does not fade the active overnight day tab", async () => {
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/destination/tochal"]}>
          <Routes>
            <Route path="/destination/:slug" element={<DestinationPage />} />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>,
    );
    await screen.findByRole("heading", { name: "قلهٔ توچال" });
    const yesterdayTab = screen.getByRole("tab", { name: /دیروز/ });
    expect(yesterdayTab.className).toContain("selected");
    expect(yesterdayTab.className).not.toContain("past-day");
  });

  it("does not refetch on repeated draft slider updates", async () => {
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/routes/tochal-darband?date=2026-08-26&period=morning&start_time=06:00&speed=متوسط"]}>
          <Routes>
            <Route path="/routes/:slug" element={<RoutePage />} />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>,
    );
    await screen.findByRole("heading", { name: "دربند تا توچال" });
    const callsAfterLoad = fetchMock.mock.calls.length;
    const slider = screen.getByLabelText("ساعت شروع حرکت") as HTMLInputElement;
    fireEvent.change(slider, { target: { value: "390" } });
    fireEvent.change(slider, { target: { value: "420" } });
    fireEvent.change(slider, { target: { value: "450" } });
    expect(fetchMock.mock.calls.length).toBe(callsAfterLoad);
    await waitFor(
      () => {
        expect(fetchMock.mock.calls.length).toBeGreaterThan(callsAfterLoad);
      },
      { timeout: 1000 },
    );
    expect(fetchMock.mock.calls.length).toBe(callsAfterLoad + 1);
  });

  it("updates draft gauge immediately when switching period", async () => {
    fetchMock.mockImplementation((input: RequestInfo) => {
      const url = forecastUrl(input);
      if (url.includes("/routes/tochal-darband/forecast")) {
        const period = url.includes("period=noon") ? "noon" : "morning";
        return jsonResponse({
          ...routeForecast,
          period: {
            id: period,
            label: period === "noon" ? "ظهر" : "صبح",
            range_label: period === "noon" ? "۱۲ تا ۱۸" : "۰۶ تا ۱۲",
            headline: period === "noon" ? "ظهر" : "صبح",
            hours: period === "noon" ? [12, 14, 16] : [6, 8, 10],
          },
          start_minutes: period === "noon" ? 720 : 360,
          meta: {
            ...routeForecast.meta,
            selected_period: period,
          },
        });
      }
      return jsonResponse({}, false, 404);
    });
    const user = userEvent.setup();
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/routes/tochal-darband?date=2026-08-26&period=morning&start_time=06:00&speed=متوسط"]}>
          <Routes>
            <Route path="/routes/:slug" element={<RoutePage />} />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>,
    );
    await screen.findByRole("heading", { name: "دربند تا توچال" });
    await user.click(screen.getByRole("button", { name: /ظهر/ }));
    expect(screen.getByLabelText("ساعت شروع حرکت")).toHaveValue("720");
  });

  it("opens a canonical point page with the shared back action", async () => {
    const user = userEvent.setup();
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/routes/tochal-darband?date=2026-08-26&period=morning"]}>
          <Routes>
            <Route path="/routes/:slug" element={<RoutePage />} />
            <Route path="/points/:slug" element={<PointDetailPage />} />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>,
    );
    await screen.findByRole("heading", { name: "دربند تا توچال" });
    const weatherLink = screen.getByLabelText(/آب‌وهوای شیرپلا/);
    expect(weatherLink).toHaveAttribute("href", "/points/tochal-shirpala-shelter");
    await user.click(weatherLink);
    expect(await screen.findByRole("heading", { name: "شیرپلا" })).toBeInTheDocument();
    expect(screen.getByText("مقصدها")).toBeInTheDocument();
    expect(document.querySelector(".breadcrumb")?.textContent).not.toMatch(/دربند تا توچال/);
  });

  it("shows the shared back action when point page opens with navigation state", async () => {
    render(
      <ThemeProvider>
        <MemoryRouter
          initialEntries={[
            {
              pathname: "/points/tochal-shirpala-shelter",
              state: {
                fromRoute: {
                  slug: "tochal-darband",
                  title: "دربند تا توچال",
                  pathname: "/routes/tochal-darband",
                  search: "?date=2026-08-26&period=morning&start_time=06:00&speed=متوسط",
                  href: "/routes/tochal-darband?date=2026-08-26&period=morning&start_time=06:00&speed=متوسط",
                },
              },
            },
          ]}
        >
          <Routes>
            <Route path="/points/:slug" element={<PointDetailPage />} />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>,
    );
    expect(await screen.findByRole("heading", { name: "شیرپلا" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "بازگشت به صفحهٔ قبل" })).toBeInTheDocument();
    expect(screen.getAllByText("مسیرهای عبوری از این نقطه").length).toBeGreaterThan(0);
    expect(document.querySelector(".destination-page")).toBeTruthy();
    expect(document.querySelector(".point-page")).toBeNull();
    expect(document.querySelector(".destination-layout")).toBeTruthy();
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

  it("does not write default date and period into point URL on fresh load", async () => {
    function SearchEcho() {
      const [params] = useSearchParams();
      return <div data-testid="url-search">{params.toString()}</div>;
    }
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/points/tochal-shirpala-shelter"]}>
          <Routes>
            <Route
              path="/points/:slug"
              element={
                <>
                  <PointDetailPage />
                  <SearchEcho />
                </>
              }
            />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>,
    );
    await screen.findByRole("heading", { name: "شیرپلا" });
    expect(screen.getByTestId("url-search")).toHaveTextContent("");
  });

  it("renders point page in dark theme without light fallback cards", async () => {
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/points/tochal-shirpala-shelter?date=2026-08-26&period=morning"]}>
          <Routes>
            <Route path="/points/:slug" element={<PointDetailPage />} />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>,
    );
    await screen.findByRole("heading", { name: "شیرپلا" });
    expect(document.querySelector(".destination-page")).toBeTruthy();
    expect(document.querySelector(".point-page")).toBeNull();
    expect(document.querySelector(".weather-card")).toBeTruthy();
    expect(document.querySelector(".mobile-route-selection")).toBeTruthy();
  });

  it("updates speed locally without fetch when timing is pending", async () => {
    fetchMock.mockImplementation((input: RequestInfo) => {
      const url = forecastUrl(input);
      if (url.includes("/routes/tochal-darband/forecast")) {
        return jsonResponse({ ...routeForecast, timing_pending: true });
      }
      return jsonResponse({}, false, 404);
    });
    const user = userEvent.setup();
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/routes/tochal-darband?date=2026-08-26&period=morning&start_time=06:00&speed=متوسط"]}>
          <Routes>
            <Route path="/routes/:slug" element={<RoutePage />} />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>,
    );
    await screen.findByRole("heading", { name: "دربند تا توچال" });
    const callsAfterLoad = fetchMock.mock.calls.length;
    const speedButton = screen.getAllByRole("button", { name: "سریع" })[0];
    await user.click(speedButton);
    expect(speedButton).toHaveClass("selected");
    expect(fetchMock.mock.calls.length).toBe(callsAfterLoad);
  });

  it("dims completely past period toggles from current_local_time", async () => {
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/destination/tochal"]}>
          <Routes>
            <Route path="/destination/:slug" element={<DestinationPage />} />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>,
    );
    await screen.findByRole("heading", { name: "قلهٔ توچال" });
    const states = classifyAllPeriods("2026-08-27", destinationForecast.meta.current_local_time);
    expect(states.morning).toBe("past");
    expect(screen.getByRole("button", { name: /صبح/ })).toHaveClass("past-period");
    expect(screen.getByRole("button", { name: /^شب/ })).toHaveClass("selected");
    expect(screen.getByRole("button", { name: /^شب/ })).not.toHaveClass("past-period");
  });

  it("does not render raw timing pending copy on route page", async () => {
    fetchMock.mockImplementation((input: RequestInfo) => {
      const url = forecastUrl(input);
      if (url.includes("/routes/tochal-darband/forecast")) {
        return jsonResponse({
          ...routeForecast,
          timing_pending: true,
          decision: {
            ...routeForecast.decision,
            title: "با حرکت ساعت ۰۶:۰۰، زمان رسیدن هنوز مشخص نیست.",
            finish: "—",
            timing_pending: true,
          },
        });
      }
      return jsonResponse({}, false, 404);
    });
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/routes/tochal-darband?date=2026-08-26&period=morning&start_time=06:00&speed=متوسط"]}>
          <Routes>
            <Route path="/routes/:slug" element={<RoutePage />} />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>,
    );
    await screen.findByRole("heading", { name: "دربند تا توچال" });
    expect(screen.queryByText(/timing pending/i)).not.toBeInTheDocument();
    expect(screen.getByText(/زمان‌بندی دقیق مسیر هنوز نهایی نشده/)).toBeInTheDocument();
  });

  it("does not render generic destination hourly block on route page", async () => {
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/routes/tochal-darband?date=2026-08-26&period=morning&start_time=06:00&speed=متوسط"]}>
          <Routes>
            <Route path="/routes/:slug" element={<RoutePage />} />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>,
    );
    await screen.findByRole("heading", { name: "دربند تا توچال" });
    expect(screen.queryByText(/تغییرات شب · هر دو ساعت/)).not.toBeInTheDocument();
    expect(document.querySelector(".route-hourly-values")).toBeNull();
  });

  it("navigates tochal summit to destination canonical href", async () => {
    fetchMock.mockImplementation((input: RequestInfo) => {
      const url = forecastUrl(input);
      if (url.includes("/routes/tochal-darband/forecast")) {
        return jsonResponse({
          ...routeForecast,
          points: [
            {
              ...routeForecast.points[0],
              slug: "tochal_summit",
              name: "قلهٔ توچال",
              href: "/destination/tochal",
            },
          ],
        });
      }
      return jsonResponse({}, false, 404);
    });
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/routes/tochal-darband?date=2026-08-26&period=morning"]}>
          <Routes>
            <Route path="/routes/:slug" element={<RoutePage />} />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>,
    );
    await screen.findByRole("heading", { name: "دربند تا توچال" });
    const summitLink = screen.getByLabelText(/آب‌وهوای قلهٔ توچال/);
    expect(summitLink).toHaveAttribute("href", "/destination/tochal");
  });

  it("preserves route back context when opening summit destination from route", async () => {
    let destinationRequestUrl = "";
    fetchMock.mockImplementation((input: RequestInfo) => {
      const url = forecastUrl(input);
      if (url.includes("/routes/tochal-darband/forecast")) {
        return jsonResponse({
          ...routeForecast,
          points: [
            {
              ...routeForecast.points[0],
              slug: "tochal_summit",
              name: "قلهٔ توچال",
              href: "/destination/tochal",
            },
          ],
        });
      }
      if (url.includes("/destinations/tochal/forecast")) {
        destinationRequestUrl = url;
        return jsonResponse(destinationForecast);
      }
      return jsonResponse({}, false, 404);
    });

    const router = createMemoryRouter(
      [
        { path: "/routes/:slug", element: <RoutePage /> },
        { path: "/destination/:slug", element: <DestinationPage /> },
      ],
      {
        initialEntries: ["/routes/tochal-darband?date=2026-08-26&period=morning&start_time=06:00&speed=متوسط"],
      },
    );

    render(
      <ThemeProvider>
        <RouterProvider router={router} />
      </ThemeProvider>,
    );

    await screen.findByRole("heading", { name: "دربند تا توچال" });
    await userEvent.click(screen.getByLabelText(/آب‌وهوای قلهٔ توچال/));
    expect(await screen.findByRole("heading", { name: "قلهٔ توچال" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/destination/tochal");
    expect(router.state.location.search).toBe("");
    expect(destinationRequestUrl).not.toContain("date=");
    expect(destinationRequestUrl).not.toContain("period=");
    expect(destinationRequestUrl).not.toContain("start_time");
    expect(router.state.location.state).toEqual(
      expect.objectContaining({
        fromRoute: expect.objectContaining({
          pathname: "/routes/tochal-darband",
          title: "دربند تا توچال",
        }),
      }),
    );
    expect(screen.getByRole("button", { name: "بازگشت به صفحهٔ قبل" })).toBeInTheDocument();
  });

  it("does not seed place planner from fromRoute — only explicit URL date/period", () => {
    const planner = initialDestinationPlanner(
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
      initialDestinationPlanner(new URLSearchParams("date=2026-08-26&period=noon"), undefined),
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

  it("syncs date and period into the URL for destination after explicit selection", async () => {
    const user = userEvent.setup();
    function SearchEcho() {
      const [params] = useSearchParams();
      return <div data-testid="url-search">{params.toString()}</div>;
    }
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/destination/tochal"]}>
          <Routes>
            <Route
              path="/destination/:slug"
              element={
                <>
                  <DestinationPage />
                  <SearchEcho />
                </>
              }
            />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>,
    );
    await screen.findByRole("heading", { name: "قلهٔ توچال" });
    expect(screen.getByTestId("url-search")).toHaveTextContent("");
    await user.click(screen.getByRole("tab", { name: /فردا/ }));
    await waitFor(() => {
      const q = screen.getByTestId("url-search").textContent ?? "";
      expect(q).toContain("date=2026-08-29");
      expect(q).toContain("period=night");
    });
  });

  it("syncs date and period into the URL for point after explicit selection", async () => {
    const user = userEvent.setup();
    function SearchEcho() {
      const [params] = useSearchParams();
      return <div data-testid="url-search">{params.toString()}</div>;
    }
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/points/tochal-shirpala-shelter"]}>
          <Routes>
            <Route
              path="/points/:slug"
              element={
                <>
                  <PointDetailPage />
                  <SearchEcho />
                </>
              }
            />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>,
    );
    await screen.findByRole("heading", { name: "شیرپلا" });
    expect(screen.getByTestId("url-search")).toHaveTextContent("");
    await user.click(screen.getByRole("button", { name: /ظهر/ }));
    await waitFor(() => {
      const q = screen.getByTestId("url-search").textContent ?? "";
      expect(q).toContain("period=noon");
      expect(q).toContain("date=");
    });
  });

  it("copies ASCII start_time in share URLs and reopens with the same planner state", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal("navigator", { ...navigator, clipboard: { writeText } });

    fetchMock.mockImplementation((input: RequestInfo) => {
      const url = forecastUrl(input);
      if (url.includes("/routes/tochal-darband/forecast")) {
        const start = url.includes("start_time=10%3A15") || url.includes("start_time=10:15") ? 600 : 360;
        return jsonResponse({
          ...routeForecast,
          start_minutes: start,
          start_time: "۰۶:۰۰",
        });
      }
      return jsonResponse({}, false, 404);
    });

    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/routes/tochal-darband?date=2026-08-26&period=morning&start_time=10:15&speed=متوسط"]}>
          <Routes>
            <Route path="/routes/:slug" element={<RoutePage />} />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>,
    );

    await screen.findByRole("heading", { name: "دربند تا توچال" });
    await userEvent.click(screen.getByRole("button", { name: "کپی لینک برنامه" }));

    const copied = writeText.mock.calls.at(-1)?.[0] as string;
    expect(copied).toContain("/routes/tochal-darband");
    expect(copied).toMatch(/start_time=10(%3A|:)00/);
    expect(copied).not.toMatch(/start_time=%D[89ABab]/);
    expect(copied).toContain("period=morning");
    expect(copied).toContain("date=2026-08-26");
    expect(copied).toContain("speed=");
  });

  it("renders point and destination with the shared Forecast Place destination shell", async () => {
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/points/tochal-sarband-square"]}>
          <Routes>
            <Route path="/points/:slug" element={<PointDetailPage />} />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>,
    );
    expect(await screen.findByRole("heading", { name: "سربند" })).toBeInTheDocument();
    expect(document.querySelector(".destination-page")).toBeTruthy();
    expect(document.querySelector(".destination-hero")).toBeTruthy();
    expect(document.querySelector(".destination-layout")).toBeTruthy();
    expect(document.querySelector(".weather-card")).toBeTruthy();
    expect(document.querySelector(".destination-side")).toBeTruthy();
    expect(document.querySelector(".mobile-route-selection")).toBeTruthy();
    expect(document.querySelector(".point-page")).toBeNull();
    expect(document.querySelector(".point-shell")).toBeNull();
    expect(screen.getByText("هوای مقصد، برنامهٔ مسیر")).toBeInTheDocument();
    expect(screen.queryByText(/هر دو ساعت/)).not.toBeInTheDocument();
    expect(screen.queryByText(/تغییرات صبح/)).not.toBeInTheDocument();
  });

  it("hides period headline on destination place page while keeping hourly legend", async () => {
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/destination/tochal"]}>
          <Routes>
            <Route path="/destination/:slug" element={<DestinationPage />} />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>,
    );
    await screen.findByRole("heading", { name: "قلهٔ توچال" });
    expect(screen.queryByText(/تغییرات شب/)).not.toBeInTheDocument();
    expect(screen.queryByText(/هر دو ساعت/)).not.toBeInTheDocument();
    expect(document.querySelector(".legend")).toBeTruthy();
    expect(screen.getByText("هوای مقصد، برنامهٔ مسیر")).toBeInTheDocument();
    expect(document.querySelector(".mobile-route-selection")).toBeNull();
    expect(document.querySelector(".destination-side")).toBeTruthy();
  });

  it("does not expose a destination profile as an independent point page", async () => {
    fetchMock.mockImplementation((input: RequestInfo) => {
      const url = forecastUrl(input);
      if (url.includes("/points/tochal_summit/forecast")) return jsonResponse({}, false, 404);
      if (url.includes("/destinations/tochal/forecast")) {
        return jsonResponse({
          ...destinationForecast,
          forecast: {
            ...destinationForecast.forecast,
            meta: {
              ...destinationForecast.forecast.meta,
              selected_date: "2026-08-26",
              selected_period: "noon",
            },
          },
          meta: {
            ...destinationForecast.meta,
            selected_date: "2026-08-26",
            selected_period: "noon",
          },
        });
      }
      return jsonResponse({}, false, 404);
    });

    const router = createMemoryRouter(
      [
        { path: "/points/:slug", element: <PointDetailPage /> },
        { path: "/destination/:slug", element: <DestinationPage /> },
      ],
      {
        initialEntries: [
          {
            pathname: "/points/tochal_summit",
            search: "?date=2026-08-26&period=noon",
            state: {
              fromRoute: {
                slug: "tochal-darband",
                title: "دربند تا توچال",
                pathname: "/routes/tochal-darband",
                search: "?date=2026-08-26&period=noon&start_time=12:00&speed=متوسط",
                href: "/routes/tochal-darband?date=2026-08-26&period=noon&start_time=12:00&speed=متوسط",
              },
            },
          },
        ],
      },
    );

    render(
      <ThemeProvider>
        <RouterProvider router={router} />
      </ThemeProvider>,
    );
    expect(await screen.findByText("نقطهٔ هواشناسی پیدا نشد")).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/points/tochal_summit");
    expect(router.state.location.search).toBe("?date=2026-08-26&period=noon");
    expect(router.state.location.search).not.toContain("start_time");
    expect(router.state.location.state).toEqual(
      expect.objectContaining({
        fromRoute: expect.objectContaining({ title: "دربند تا توچال" }),
      }),
    );
    expect(screen.getByRole("button", { name: "بازگشت به صفحهٔ قبل" })).toBeInTheDocument();
    expect(document.querySelector(".point-page")).toBeNull();
  });


});
