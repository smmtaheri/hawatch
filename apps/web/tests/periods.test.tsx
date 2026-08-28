import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ThemeProvider } from "../src/app/theme";
import { RoutePage } from "../src/pages/RoutePage";
import { PointDetailPage } from "../src/pages/PointDetailPage";
import { PERIOD_OPTIONS } from "../src/lib/periods";

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
    parent: {
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
    },
    points: [],
    siblings: [],
  },
  days: [{ date: "2026-08-26", label: "امروز", jalali: "۴ شهریور", offset: 0, is_yesterday: false, is_today: true, is_past: false, is_future: false, is_current: true }],
  period: { id: "morning", label: "صبح", range_label: "۰۲ تا ۱۰", headline: "تغییرات صبح", hours: [2, 4, 6, 8] },
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
      href: "/routes/touchal-darband/points/shirpala",
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
    { time: "۰۲:۰۰", hour: 2, forecast_at: "2026-08-26T02:00:00+03:30", temperature_c: 7, temperature_label: "۷°", condition: "صاف", icon: "☼", wind_speed_kmh: 7, wind_label: "باد ۷ km/h", severity: "normal", state: "normal", is_yesterday: false, is_today: true, is_past: true, is_current: false, is_future: false },
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

function jsonResponse(data: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: async () => data });
}

describe("periods and route planner", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    fetchMock.mockImplementation((input: RequestInfo) => {
      const url = String(input);
      if (url.includes("/routes/touchal-darband/forecast")) return jsonResponse(routeForecast);
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
          },
          days: routeForecast.days,
          period: routeForecast.period,
          weather: routeForecast.hourly[0],
          hourly: routeForecast.hourly,
          empty: false,
          partial: false,
          back_href: "/routes/touchal-darband?date=2026-08-26&period=morning",
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
        <MemoryRouter initialEntries={["/routes/touchal-darband"]}>
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

  it("does not refetch on every slider input event", async () => {
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
    const initialCalls = fetchMock.mock.calls.length;
    const slider = screen.getByLabelText("ساعت شروع حرکت");
    await user.click(slider);
    expect(fetchMock.mock.calls.length).toBe(initialCalls);
  });

  it("opens point detail page from route point card", async () => {
    const user = userEvent.setup();
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/routes/touchal-darband?date=2026-08-26&period=morning"]}>
          <Routes>
            <Route path="/routes/:slug" element={<RoutePage />} />
            <Route path="/routes/:routeSlug/points/:pointSlug" element={<PointDetailPage />} />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>,
    );
    await screen.findByRole("heading", { name: "دربند تا توچال" });
    await user.click(screen.getByLabelText(/آب‌وهوای شیرپلا/));
    expect(await screen.findByRole("heading", { name: "شیرپلا" })).toBeInTheDocument();
    expect(screen.getByLabelText("بازگشت به مسیر")).toHaveAttribute("href", expect.stringContaining("/routes/touchal-darband"));
  });

  it("skips planner refetch when timing is pending", async () => {
    fetchMock.mockImplementation((input: RequestInfo) => {
      const url = String(input);
      if (url.includes("/routes/touchal-darband/forecast")) {
        return jsonResponse({ ...routeForecast, timing_pending: true });
      }
      return jsonResponse({}, false, 404);
    });
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
    await userEvent.click(speedButton);
    await waitFor(() => {
      expect(fetchMock.mock.calls.length).toBe(callsAfterLoad);
    });
  });
});
