import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { buildRouteBackState, buildRoutePointLink } from "../src/lib/routeNavigation";
import { MemoryRouter, Route, Routes, useSearchParams } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ThemeProvider } from "../src/app/theme";
import { DestinationPage } from "../src/pages/DestinationPage";
import { RoutePage } from "../src/pages/RoutePage";
import { PointDetailPage } from "../src/pages/PointDetailPage";
import { PERIOD_OPTIONS, PERIOD_RANGES, periodTicks } from "../src/lib/periods";

const destinationForecast = {
  destination: {
    slug: "touchal",
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
    href: "/destination/touchal",
    is_popular: true,
    routes: [],
  },
  days: [
    { date: "2026-08-27", label: "دیروز", jalali: "۶ شهریور", offset: -1, is_yesterday: true, is_today: false, is_past: false, is_future: false, is_current: false },
    { date: "2026-08-28", label: "امروز", jalali: "۷ شهریور", offset: 0, is_yesterday: false, is_today: true, is_past: false, is_future: false, is_current: true },
  ],
  period: { id: "night", label: "شب", range_label: "۱۹ تا ۰۳", headline: "تغییرات شب", hours: [19, 21, 23, 1] },
  current: {
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
  },
  hourly: [],
  metrics: [],
  hero: { status: "☼　الان در توچال　۵°　·　صاف", alert: "آرام" },
  decision: { chip: "دیروز · جمع‌بندی هواچ", title: "صبح", text: "آرام" },
  updated_label: "امروز",
  empty: false,
  meta: { freshness: "ready", generated_at: "2026-08-28T00:30:00+03:30", selected_date: "2026-08-27", selected_period: "night" },
};

const routeForecast = {
  route: {
    slug: "touchal-darband",
    title: "دربند تا توچال",
    subtitle: "",
    origin: "دربند",
    destination_label: "قلهٔ توچال",
    distance_label: "۱۶٫۲ km",
    ascent_label: "۲۲۶۰ m",
    default_start_minutes: 360,
    href: "/routes/touchal-darband",
    parent: destinationForecast.destination,
    points: [],
    siblings: [],
  },
  days: destinationForecast.days,
  period: { id: "morning", label: "صبح", range_label: "۰۳ تا ۱۱", headline: "تغییرات صبح", hours: [3, 5, 7, 9] },
  start_minutes: 360,
  start_time: "۰۶:۰۰",
  speed: "متوسط",
  speed_options: ["آرام", "متوسط", "سریع"],
  timing_pending: false,
  points: [
    {
      slug: "shirpala",
      name: "شیرپلا",
      elevation_label: "۲۴۵۰ m",
      href: "/points/shirpala",
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
  meta: { freshness: "ready", generated_at: "2026-08-26T05:45:00+03:30", selected_date: "2026-08-26", selected_period: "morning" },
};

const pointForecast = {
  point: {
    slug: "shirpala",
    name: "شیرپلا",
    aliases: [],
    kind: "shared",
    elevation_m: 2750,
    elevation_label: "۲۴۵۰ m",
    latitude: 35.855,
    longitude: 51.429,
    status: "approved",
    provenance: "curated",
    href: "/points/shirpala",
    destination: routeForecast.route.parent,
  },
  related_destinations: [routeForecast.route.parent],
  related_routes: [
    {
      slug: "touchal-darband",
      title: "دربند تا توچال",
      trail_label: "مسیر",
      origin: "دربند",
      destination_label: "قلهٔ توچال",
      distance_km: 16.2,
      distance_label: "۱۶٫۲ km",
      ascent_m: 2260,
      ascent_label: "۲۲۶۰ m",
      featured: true,
      href: "/routes/touchal-darband",
    },
  ],
  days: routeForecast.days,
  period: routeForecast.period,
  current: routeForecast.hourly[0],
  weather: routeForecast.hourly[0],
  hourly: routeForecast.hourly,
  hero: { status: "☼　در شیرپلا　۷°　·　صاف" },
  updated_label: "امروز",
  empty: false,
  partial: false,
  meta: routeForecast.meta,
};

function jsonResponse(data: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: async () => data });
}

function forecastUrl(input: RequestInfo) {
  return String(input);
}

function destinationCalls(calls: unknown[][]) {
  return calls.map((call) => forecastUrl(call[0] as RequestInfo)).filter((url) => url.includes("/destinations/touchal/forecast"));
}

describe("periods and route planner", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    fetchMock.mockImplementation((input: RequestInfo) => {
      const url = forecastUrl(input);
      if (url.includes("/destinations/touchal/forecast")) return jsonResponse(destinationForecast);
      if (url.includes("/routes/touchal-darband/forecast")) return jsonResponse(routeForecast);
      if (url.includes("/points/shirpala/forecast")) return jsonResponse(pointForecast);
      if (url.includes("/routes/touchal-darband/points/shirpala/forecast")) {
        return jsonResponse({
          point: {
            ...routeForecast.points[0],
            route_slug: "touchal-darband",
            route_title: "دربند تا توچال",
            route_href: "/routes/touchal-darband",
            destination: routeForecast.route.parent,
            has_weather_point: true,
            has_forecast: true,
            weather_point_slug: "shirpala",
          },
          days: routeForecast.days,
          period: routeForecast.period,
          weather: routeForecast.hourly[0],
          hourly: routeForecast.hourly,
          empty: false,
          partial: false,
          back_href: "/routes/touchal-darband?date=2026-08-26&period=morning",
          canonical_href: "/points/shirpala",
          weather_point_slug: "shirpala",
          meta: routeForecast.meta,
        });
      }
      return jsonResponse({}, false, 404);
    });
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders three period buttons", async () => {
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/routes/touchal-darband?date=2026-08-26&period=morning"]}>
          <Routes>
            <Route path="/routes/:slug" element={<RoutePage />} />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>,
    );
    await screen.findByRole("heading", { name: "دربند تا توچال" });
    expect(PERIOD_OPTIONS).toHaveLength(3);
    expect(screen.getByRole("button", { name: /شب/ })).toBeInTheDocument();
  });

  it("uses four odd-hour slices in each Iran-time period", () => {
    expect(PERIOD_OPTIONS.map((option) => option.rangeLabel)).toEqual(["۰۳ تا ۱۱", "۱۱ تا ۱۹", "۱۹ تا ۰۳"]);
    expect(PERIOD_RANGES.morning).toMatchObject({ min: 180, max: 660 });
    expect(PERIOD_RANGES.afternoon).toMatchObject({ min: 660, max: 1140 });
    expect(PERIOD_RANGES.night).toMatchObject({ min: 1140, max: 1590 });
    expect(periodTicks("morning")).toEqual(["۰۳:۰۰", "۰۵:۰۰", "۰۷:۰۰", "۰۹:۰۰", "۱۱:۰۰"]);
    expect(periodTicks("afternoon")).toEqual(["۱۱:۰۰", "۱۳:۰۰", "۱۵:۰۰", "۱۷:۰۰", "۱۹:۰۰"]);
    expect(periodTicks("night")).toEqual(["۱۹:۰۰", "۲۱:۰۰", "۲۳:۰۰", "۰۱:۰۰", "۰۳:۰۰"]);
  });

  it("does not send period=morning on no-query initial destination load", async () => {
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/destination/touchal"]}>
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
        <MemoryRouter initialEntries={["/destination/touchal"]}>
          <Routes>
            <Route path="/destination/:slug" element={<DestinationPage />} />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>,
    );
    await screen.findByRole("heading", { name: "قلهٔ توچال" });
    expect(screen.getByRole("button", { name: /شب/ })).toHaveAttribute("aria-pressed", "true");
  });

  it("keeps explicit query period on destination load", async () => {
    fetchMock.mockImplementation((input: RequestInfo) => {
      const url = forecastUrl(input);
      if (url.includes("period=afternoon")) {
        return jsonResponse({
          ...destinationForecast,
          meta: { ...destinationForecast.meta, selected_period: "afternoon" },
          period: { id: "afternoon", label: "بعدازظهر", range_label: "۱۱ تا ۱۹", headline: "بعدازظهر", hours: [11, 13, 15, 17] },
        });
      }
      return jsonResponse(destinationForecast);
    });
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/destination/touchal?period=afternoon"]}>
          <Routes>
            <Route path="/destination/:slug" element={<DestinationPage />} />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>,
    );
    await screen.findByRole("heading", { name: "قلهٔ توچال" });
    const destinationRequest = destinationCalls(fetchMock.mock.calls).find((url) => url.includes("period=afternoon"));
    expect(destinationRequest).toBeDefined();
    expect(screen.getByRole("button", { name: /بعدازظهر/ })).toHaveAttribute("aria-pressed", "true");
  });

  it("does not fade the active overnight day tab", async () => {
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/destination/touchal"]}>
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
        <MemoryRouter initialEntries={["/routes/touchal-darband?date=2026-08-26&period=morning&start_time=06:00&speed=متوسط"]}>
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
    const user = userEvent.setup();
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/routes/touchal-darband?date=2026-08-26&period=morning&start_time=06:00&speed=متوسط"]}>
          <Routes>
            <Route path="/routes/:slug" element={<RoutePage />} />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>,
    );
    await screen.findByRole("heading", { name: "دربند تا توچال" });
    await user.click(screen.getByRole("button", { name: /بعدازظهر/ }));
    expect(screen.getByLabelText("ساعت شروع حرکت")).toHaveValue("720");
  });

  it("opens canonical point page from route point card with route back CTA", async () => {
    const user = userEvent.setup();
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/routes/touchal-darband?date=2026-08-26&period=morning"]}>
          <Routes>
            <Route path="/routes/:slug" element={<RoutePage />} />
            <Route path="/points/:slug" element={<PointDetailPage />} />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>,
    );
    await screen.findByRole("heading", { name: "دربند تا توچال" });
    const weatherLink = screen.getByLabelText(/آب‌وهوای شیرپلا/);
    expect(weatherLink).toHaveAttribute("href", "/points/shirpala");
    await user.click(weatherLink);
    expect(await screen.findByRole("heading", { name: "شیرپلا" })).toBeInTheDocument();
    expect(screen.getByText("مقصدها")).toBeInTheDocument();
    expect(document.querySelector(".breadcrumb")?.textContent).not.toMatch(/دربند تا توچال/);
  });

  it("shows route back CTA when point page opened with navigation state", async () => {
    render(
      <ThemeProvider>
        <MemoryRouter
          initialEntries={[
            {
              pathname: "/points/shirpala",
              state: {
                fromRoute: {
                  slug: "touchal-darband",
                  title: "دربند تا توچال",
                  pathname: "/routes/touchal-darband",
                  search: "?date=2026-08-26&period=morning&start_time=06:00&speed=متوسط",
                  href: "/routes/touchal-darband?date=2026-08-26&period=morning&start_time=06:00&speed=متوسط",
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
    const backLink = screen.getByLabelText("بازگشت به مسیر دربند تا توچال");
    expect(backLink.getAttribute("href")).toContain("/routes/touchal-darband");
    expect(backLink.getAttribute("href")).toContain("start_time=06");
    expect(backLink.getAttribute("href")).toContain("speed=");
    expect(screen.queryByText("مسیرهای مرتبط")).not.toBeInTheDocument();
    expect(document.querySelector(".point-layout--single")).toBeTruthy();
  });

  it("builds route back target with planner params for point links", () => {
    const params = new URLSearchParams("date=2026-08-26&period=morning&start_time=06:00&speed=متوسط");
    const fromRoute = buildRouteBackState(
      { slug: "touchal-darband", title: "دربند تا توچال", href: "/routes/touchal-darband" },
      params,
    );
    const link = buildRoutePointLink("/points/shirpala", fromRoute);
    expect(link.pathname).toBe("/points/shirpala");
    expect(link.search).toBe("");
    expect(link.state?.fromRoute.pathname).toBe("/routes/touchal-darband");
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
        <MemoryRouter initialEntries={["/points/shirpala"]}>
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
        <MemoryRouter initialEntries={["/points/shirpala?date=2026-08-26&period=morning"]}>
          <Routes>
            <Route path="/points/:slug" element={<PointDetailPage />} />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>,
    );
    await screen.findByRole("heading", { name: "شیرپلا" });
    expect(document.querySelector(".point-page")).toBeTruthy();
    expect(document.querySelector(".point-weather-card")).toBeTruthy();
  });

  it("updates speed locally without fetch when timing is pending", async () => {
    fetchMock.mockImplementation((input: RequestInfo) => {
      const url = forecastUrl(input);
      if (url.includes("/routes/touchal-darband/forecast")) {
        return jsonResponse({ ...routeForecast, timing_pending: true });
      }
      return jsonResponse({}, false, 404);
    });
    const user = userEvent.setup();
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/routes/touchal-darband?date=2026-08-26&period=morning&start_time=06:00&speed=متوسط"]}>
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
});
