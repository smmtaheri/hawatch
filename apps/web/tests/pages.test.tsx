import { StrictMode } from "react";
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ThemeProvider } from "../src/app/theme";
import { AppRoutes } from "../src/app/App";
import { buildRouteShareUrl } from "../src/lib/routeShare";
import { HourlyForecast } from "../src/components/HourlyForecast";
import { copyShareLink } from "../src/lib/shareImage";
import { CategoryIcon, WeatherIcon } from "../src/components/DesignIcon";
import pointFixture from "./fixtures/point-day.json";
import routeFixture from "./fixtures/route-day.json";
import type { HourlyReading, RouteForecast } from "../src/types";

const day = pointFixture.meta.selected_date;
const previous = pointFixture.days[0].date;
const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value));
const response = (data: unknown, status = 200) =>
  Promise.resolve({ ok: status < 400, status, json: async () => data });
let authenticated = false;
let paid = false;
let error = 0;
let pending = false;
let stale = false;
const fetchMock = vi.fn();
function Probe() {
  const location = useLocation();
  return (
    <output data-testid="location">
      {location.pathname}
      {location.search}
    </output>
  );
}
function mount(path = "/", strict = false) {
  const content = (
    <ThemeProvider>
      <MemoryRouter initialEntries={[path]}>
        <AppRoutes />
        <Probe />
      </MemoryRouter>
    </ThemeProvider>
  );
  return render(strict ? <StrictMode>{content}</StrictMode> : content);
}
function weatherCalls() {
  return fetchMock.mock.calls.filter(([url]) =>
    String(url).includes("/forecast/"),
  );
}
function account() {
  return {
    authenticated: true,
    plan: {
      code: paid ? "professional" : "free",
      title: paid ? "طرح حرفه‌ای" : "عضویت رایگان",
      tier: paid ? "paid" : "free",
    },
    days_remaining: paid ? 4 : null,
    forecast_access: { ...pointFixture.forecast_access, viewer: "member" },
  };
}
function pointBundle(url: URL) {
  const data = clone(pointFixture);
  const date = url.searchParams.get("date") || day;
  const period = url.searchParams.get("period") || data.meta.selected_period;
  data.meta.selected_date = date;
  data.meta.selected_period = period;
  data.forecast.meta = data.meta;
  data.meta.freshness = stale ? "stale" : "ready";
  if (authenticated) {
    data.forecast_access.viewer = "member";
    data.days.forEach((item) => {
      if (item.offset <= 1) item.access = "available";
    });
  }
  data.periods[period as keyof typeof data.periods].hourly.forEach((hour) => {
    hour.apparent_temperature_c = -7;
    hour.temperature_c = 91;
  });
  return data;
}
function routeBundle(url: URL) {
  const data = clone(routeFixture);
  data.meta.selected_date = url.searchParams.get("date") || day;
  data.meta.selected_period = url.searchParams.get("period") || "morning";
  data.speed = "متوسط";
  data.start_minutes = 480;
  data.start_time = "۰۸:۰۰";
  data.timing_pending = pending;
  if (pending)
    for (const plan of Object.values(data.plans)) {
      plan.decision.timing_pending = true;
      plan.points.forEach(
        (point) => ((point as { arrival_at: string | null }).arrival_at = null),
      );
    }
  return data;
}
function pointSummary() {
  return pointFixture.point;
}
function routeSuggestion() {
  return {
    type: "route",
    id: "route:tochal-darband",
    label: "دربند تا توچال",
    slug: "tochal-darband",
    href: "/routes/tochal-darband",
    hint: "۶ نقطه · ۱۰ کیلومتر",
    category_key: "route",
    place_type: "route",
    normalized_query: "توچال",
  };
}
function pointSuggestion() {
  return {
    type: "point",
    id: "point:tochal",
    label: "قلهٔ توچال",
    slug: "tochal",
    href: "/points/tochal",
    hint: "تهران · ۳۹۵۵ متر",
    category_key: "mountain",
    place_type: "peak",
    normalized_query: "توچال",
  };
}
function defaultFetch(input: RequestInfo) {
  const url = new URL(String(input), "http://localhost");
  if (url.pathname.includes("/auth/me"))
    return response(authenticated ? account() : {}, authenticated ? 200 : 403);
  if (url.pathname.includes("/auth/csrf"))
    return response({ csrf_token: "test-csrf" });
  if (url.pathname.includes("/auth/login")) {
    authenticated = true;
    return response(account());
  }
  if (url.pathname.includes("/auth/logout")) {
    authenticated = false;
    return response({ authenticated: false });
  }
  if (url.pathname.includes("/forecast/")) {
    if (error) return response({ detail: "forecast error" }, error);
    if (
      url.searchParams.get("date") &&
      url.searchParams.get("date")! > day &&
      !authenticated
    )
      return response({ code: "login_required" }, 403);
    return response(
      url.pathname.includes("/routes/") ? routeBundle(url) : pointBundle(url),
    );
  }
  if (url.pathname.includes("/search/suggestions"))
    return response({ results: [pointSuggestion(), routeSuggestion()] });
  if (url.pathname.endsWith("/destinations/"))
    return response({
      destinations:
        url.searchParams.get("query") === "هیچ" ? [] : [pointSummary()],
      pagination: {
        page: 1,
        page_size: 16,
        total: 1,
        has_next: false,
        next_page: null,
        next_href: null,
        previous_href: null,
      },
    });
  if (url.pathname.endsWith("/routes/"))
    return response({
      routes:
        url.searchParams.get("query") === "هیچ" ? [] : [routeFixture.route],
      empty: false,
    });
  if (url.pathname.endsWith("/points/"))
    return response({
      results: [pointSummary()],
      meta: {
        ...pointFixture.meta,
        catalog_counts: { points: 746, routes: 166 },
      },
    });
  return response({}, 404);
}

beforeEach(() => {
  authenticated = false;
  paid = false;
  error = 0;
  pending = false;
  stale = false;
  fetchMock.mockReset();
  fetchMock.mockImplementation(defaultFetch);
  vi.stubGlobal("fetch", fetchMock);
  localStorage.clear();
});
afterEach(() => vi.unstubAllGlobals());

describe("new-design pages and real day contracts", () => {
  it("shows a gust-only warning in yellow details without a red hazard icon", async () => {
    const hour = clone(pointFixture.periods.noon.hourly[0]) as HourlyReading;
    Object.assign(hour, {
      condition: "ابری", weather_code: "overcast", wind_speed_kmh: 15,
      wind_gust_kmh: 45, state: "change", severity: "change", is_past: true,
      wind_alert: { code: "gale", label: "تندباد", severity: "change" },
    });
    render(<HourlyForecast hours={[hour]} />);
    const trigger = screen.getByRole("button", { name: "جزئیات تخصصی" });
    expect(trigger).toHaveClass("risk-yellow");
    expect(document.querySelector(".hazard")).toBeNull();
    expect(screen.getByText("ابری")).not.toHaveClass("risk-yellow", "risk-red");
    await userEvent.click(trigger);
    expect(screen.getByText("تندباد")).toHaveClass("risk-yellow");
    expect(screen.getByText("باد", { selector: ".metric span" })).not.toHaveClass("risk-yellow");
  });

  it("keeps the day label neutral while coloring the weather summary", async () => {
    mount("/points/tochal");
    await screen.findByRole("heading", { name: "آب‌وهوای قلهٔ توچال" });
    const label = document.querySelector(".day-summary-label");
    expect(label).not.toBeNull();
    expect(label).not.toHaveClass("risk-yellow", "risk-red");
    expect(document.querySelector(".day-summary-line")).not.toHaveClass("risk-yellow", "risk-red");
    expect(document.querySelector(".day-summary-line > .risk-red")).not.toBeNull();
  });

  it("removes expired membership weather before revalidation without losing day controls", async () => {
    authenticated = true;
    paid = true;
    let requests = 0;
    fetchMock.mockImplementation((input: RequestInfo) => {
      const url = new URL(String(input), "http://localhost");
      if (url.pathname.includes("/forecast/")) {
        if (requests++) return new Promise(() => {});
        const data = pointBundle(url);
        return response({
          ...data,
          cache_expires_at: new Date(
            Date.parse(data.meta.current_local_time) + 1000,
          ).toISOString(),
        });
      }
      return defaultFetch(input);
    });
    vi.useFakeTimers();
    try {
      await act(async () => {
        mount("/points/tochal");
      });
      expect(document.querySelector(".hour-card")).not.toBeNull();
      const today = screen.getByRole("tab", { name: /امروز/ });
      today.focus();
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1002);
      });
      expect(weatherCalls()).toHaveLength(2);
      expect(document.querySelector(".hour-card")).toBeNull();
      expect(today).toBeVisible();
      expect(today).toHaveFocus();
    } finally {
      vi.useRealTimers();
    }
  });

  it("keeps day controls focused during a request and ignores a late previous-day response", async () => {
    let finish!: (value: unknown) => void;
    fetchMock.mockImplementation((input: RequestInfo) => {
      const url = new URL(String(input), "http://localhost");
      if (
        url.pathname.includes("/forecast/") &&
        url.searchParams.get("date") === previous
      ) {
        return new Promise((resolve) => {
          finish = resolve;
        });
      }
      return defaultFetch(input);
    });
    mount("/points/tochal");
    await screen.findByRole("heading", { name: "آب‌وهوای قلهٔ توچال" });
    const yesterday = screen.getByRole("tab", { name: /دیروز/ });
    await userEvent.click(yesterday);
    await waitFor(() => expect(weatherCalls()).toHaveLength(2));
    expect(yesterday).toHaveFocus();
    expect(screen.getByRole("tab", { name: /امروز/ })).toBeVisible();
    expect(document.querySelector(".hour-card")).toBeNull();
    await userEvent.click(screen.getByRole("tab", { name: /امروز/ }));
    await act(async () => {
      finish(
        await response(
          pointBundle(new URL(`http://localhost/forecast/?date=${previous}`)),
        ),
      );
    });
    expect(screen.getByRole("tab", { name: /امروز/ })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByTestId("location")).toHaveTextContent(`date=${day}`);
    expect(weatherCalls()).toHaveLength(2);
  });

  it("renders home counts and navigation to both independent catalogs", async () => {
    mount();
    expect(await screen.findByText("۷۴۶")).toBeVisible();
    expect(screen.getByRole("link", { name: "همهٔ مقصدها" })).toHaveAttribute(
      "href",
      "/destinations",
    );
    expect(screen.getByRole("link", { name: "همهٔ مسیرها" })).toHaveAttribute(
      "href",
      "/routes",
    );
    expect(screen.getByRole("link", { name: "تلگرام هواچ" })).toBeVisible();
  });
  it.each(["/destinations", "/routes"])(
    "queries its own %s catalog",
    async (path) => {
      mount(path);
      await screen.findByRole("heading", { level: 1 });
      await userEvent.type(screen.getByRole("searchbox"), "هیچ");
      await waitFor(() =>
        expect(
          fetchMock.mock.calls.some(
            ([url]) =>
              String(url).includes(path + "/?") &&
              String(url).includes("query="),
          ),
        ).toBe(true),
      );
      expect(weatherCalls()).toHaveLength(0);
    },
  );
  it("deduplicates the first complete day request in StrictMode", async () => {
    mount("/points/tochal", true);
    await screen.findByRole("heading", { name: "آب‌وهوای قلهٔ توچال" });
    expect(weatherCalls()).toHaveLength(1);
    expect(String(weatherCalls()[0][0])).toContain("/forecast/day/");
    expect(screen.getByTestId("location")).toHaveTextContent(
      /^\/points\/tochal$/,
    );
  });
  it("keeps the backend default period on a clean point URL", async () => {
    mount("/points/tochal");
    await screen.findByRole("heading", { name: "آب‌وهوای قلهٔ توچال" });
    expect(
      document.querySelector('.period[aria-pressed="true"]'),
    ).toHaveTextContent("ظهر");
    expect(String(weatherCalls()[0][0])).not.toContain("period=");
  });
  it("honors an explicit period without a second weather request", async () => {
    mount(`/points/tochal?date=${day}&period=night`);
    await screen.findByRole("heading", { name: "آب‌وهوای قلهٔ توچال" });
    expect(
      document.querySelector('.period[aria-pressed="true"]'),
    ).toHaveTextContent("شب");
    expect(weatherCalls()).toHaveLength(1);
  });
  it("switches all four periods locally and preserves focus and scroll", async () => {
    mount("/points/tochal");
    await screen.findByRole("heading", { name: "آب‌وهوای قلهٔ توچال" });
    const scroll = vi.mocked(window.scrollTo);
    scroll.mockClear();
    for (const label of ["بامداد", "صبح", "ظهر", "شب"])
      await userEvent.click(
        screen.getByRole("button", { name: new RegExp("^" + label + "،") }),
      );
    expect(weatherCalls()).toHaveLength(1);
    expect(scroll).not.toHaveBeenCalled();
    expect(document.activeElement).toHaveTextContent("شب");
    expect(screen.getByTestId("location")).toHaveTextContent("period=night");
  });
  it("reads a new day once and reuses the initial resolved-day cache", async () => {
    mount("/points/tochal");
    await screen.findByRole("heading", { name: "آب‌وهوای قلهٔ توچال" });
    await userEvent.click(screen.getByRole("tab", { name: /دیروز/ }));
    await waitFor(() => expect(weatherCalls()).toHaveLength(2));
    await userEvent.click(screen.getByRole("tab", { name: /امروز/ }));
    expect(weatherCalls()).toHaveLength(2);
    expect(screen.getByTestId("location")).toHaveTextContent(`date=${day}`);
  });
  it("renders apparent temperatures while never using ordinary temperature", async () => {
    mount(`/points/tochal?period=morning`);
    await screen.findByRole("heading", { name: "آب‌وهوای قلهٔ توچال" });
    expect(document.querySelector(".hour-card .degree")).toHaveTextContent(
      "−۷°",
    );
    expect(document.querySelector(".hour-card .degree")).not.toHaveTextContent(
      "۹۱",
    );
  });
  it("opens one hour-specific panel, switches it, and closes it without fetching", async () => {
    mount("/points/tochal");
    await screen.findByRole("heading", { name: "آب‌وهوای قلهٔ توچال" });
    const buttons = screen.getAllByRole("button", { name: "جزئیات تخصصی" });
    expect(document.querySelector(".detail-panel")).toBeNull();
    await userEvent.click(buttons[0]);
    expect(document.querySelector(".detail-panel h2")).toHaveTextContent(
      "۱۲:۰۰",
    );
    await userEvent.click(buttons[1]);
    expect(document.querySelectorAll(".detail-panel")).toHaveLength(1);
    expect(buttons[0]).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(buttons[1]);
    expect(document.querySelector(".detail-panel")).toBeNull();
    expect(weatherCalls()).toHaveLength(1);
  });
  it("resets hour details when changing the period", async () => {
    mount("/points/tochal");
    await screen.findByRole("heading", { name: "آب‌وهوای قلهٔ توچال" });
    await userEvent.click(
      screen.getAllByRole("button", { name: "جزئیات تخصصی" })[0],
    );
    await userEvent.click(screen.getByRole("button", { name: /^شب،/ }));
    expect(document.querySelector(".detail-panel")).toBeNull();
  });
  it("does not invent missing readings and preserves valid zero readings", async () => {
    const hour = clone(pointFixture.periods.morning.hourly[0]);
    (hour as HourlyReading).apparent_temperature_c = null;
    hour.rain_mm = 0;
    render(<HourlyForecast hours={[hour as HourlyReading]} />);
    expect(document.querySelector(".degree")).toHaveTextContent("نامشخص");
    await userEvent.click(screen.getByRole("button", { name: "جزئیات تخصصی" }));
    expect(document.querySelector(".detail-panel")).toHaveTextContent("۰ mm");
  });
  it("renders all route points, four periods and one summary share action", async () => {
    mount("/routes/tochal-darband");
    await screen.findByRole("heading", { name: "دربند تا توچال" });
    expect(document.querySelectorAll(".point-card")).toHaveLength(
      routeFixture.points.length,
    );
    expect(document.querySelectorAll(".period")).toHaveLength(4);
    expect(
      document.querySelectorAll(".trip-summary .share-actions button"),
    ).toHaveLength(1);
    expect(screen.queryByText("جزئیات تخصصی")).toBeNull();
  });
  it("changes route hour, pace and period from 72 authoritative plans without fetching", async () => {
    mount(`/routes/tochal-darband?date=${day}&period=morning&start_time=08:00`);
    await screen.findByRole("heading", { name: "دربند تا توچال" });
    const slider = screen.getByRole("slider");
    fireEvent.change(slider, { target: { value: "600" } });
    await userEvent.click(screen.getByRole("button", { name: "سریع" }));
    await userEvent.click(screen.getByRole("button", { name: /^شب،/ }));
    expect(slider).toHaveAttribute("min", "1080");
    expect(weatherCalls()).toHaveLength(1);
    expect(screen.getByTestId("location")).toHaveTextContent("speed=");
  });
  it("updates pending timing locally and explicitly reports unavailable arrivals", async () => {
    pending = true;
    mount("/routes/tochal-darband");
    await screen.findByRole("heading", { name: "دربند تا توچال" });
    await userEvent.click(screen.getByRole("button", { name: "آرام" }));
    expect(weatherCalls()).toHaveLength(1);
    expect(screen.getByText(/زمان‌بندی دقیق مسیر هنوز/)).toBeVisible();
  });
  it("maps speed aliases on an incoming shared URL", async () => {
    mount(
      `/routes/tochal-darband?date=${day}&period=morning&start_time=08:00&speed=fast`,
    );
    await screen.findByRole("heading", { name: "دربند تا توچال" });
    expect(screen.getByRole("button", { name: "سریع" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("slider")).toHaveValue("480");
  });
  it("keeps shared links on the real route with explicit date, ASCII clock and pace", () => {
    const forecast = clone(routeFixture) as unknown as RouteForecast;
    forecast.period.id = "morning";
    forecast.start_minutes = 480;
    const url = new URL(
      buildRouteShareUrl(forecast, "http://202.133.89.120:5050"),
    );
    expect(url.pathname).toBe("/routes/tochal-darband");
    expect(url.searchParams.get("date")).toBe(day);
    expect(url.searchParams.get("start_time")).toBe("08:00");
    expect(url.searchParams.get("speed")).toBe("متوسط");
  });
  it("opens a canonical point from a route and retains the return planner context", async () => {
    mount(`/routes/tochal-darband?date=${day}&period=morning&start_time=08:00`);
    await screen.findByRole("heading", { name: "دربند تا توچال" });
    vi.mocked(window.scrollTo).mockClear();
    await userEvent.click(document.querySelector(".point-card")!);
    await waitFor(() =>
      expect(screen.getByTestId("location")).toHaveTextContent("/points/"),
    );
    expect(window.scrollTo).toHaveBeenCalledWith({
      top: 0,
      left: 0,
      behavior: "instant",
    });
    expect(screen.getByRole("button", { name: /بازگشت/ })).toBeInTheDocument();
  });
  it("changes route through a dialog and closes it on navigation", async () => {
    mount("/routes/tochal-darband");
    await screen.findByRole("heading", { name: "دربند تا توچال" });
    await userEvent.click(screen.getByRole("button", { name: "تغییر مسیر" }));
    const dialog = screen.getByRole("dialog");
    const link = within(dialog).getAllByRole("link")[0];
    await userEvent.click(link);
    expect(document.querySelector("dialog")).toBeNull();
  });
  it("shows a noindex 404 and removes its canonical", async () => {
    error = 404;
    mount("/points/missing");
    await screen.findByRole("heading", { name: "نقطه پیدا نشد" });
    expect(document.querySelector('meta[name="robots"]')).toHaveAttribute(
      "content",
      "noindex,follow",
    );
    expect(document.querySelector('link[rel="canonical"]')).toBeNull();
  });
  it("shows a retryable API error and recovers with a fresh request", async () => {
    error = 500;
    mount("/points/tochal");
    await screen.findByRole("button", { name: /تلاش دوباره/ });
    error = 0;
    await userEvent.click(screen.getByRole("button", { name: /تلاش دوباره/ }));
    await screen.findByRole("heading", { name: "آب‌وهوای قلهٔ توچال" });
    expect(weatherCalls()).toHaveLength(2);
  });
  it("retains the stale-data notice", async () => {
    stale = true;
    mount("/points/tochal");
    expect(await screen.findByText(/داده.*قدیمی/)).toBeInTheDocument();
  });
  it("switches theme without refetching weather", async () => {
    mount("/points/tochal");
    await screen.findByRole("heading", { name: "آب‌وهوای قلهٔ توچال" });
    await userEvent.click(screen.getByRole("button", { name: "تغییر تم" }));
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(weatherCalls()).toHaveLength(1);
  });
  it("opens login underneath the avatar without changing URL or locking body", async () => {
    mount("/points/tochal");
    await screen.findByRole("heading", { name: "آب‌وهوای قلهٔ توچال" });
    await userEvent.click(screen.getByRole("button", { name: "ورود" }));
    expect(screen.getByLabelText("شمارهٔ موبایل")).toBeVisible();
    expect(document.querySelector("dialog")).toBeNull();
    expect(document.body.style.overflow).not.toBe("hidden");
    expect(screen.getByTestId("location")).toHaveTextContent(
      /^\/points\/tochal$/,
    );
  });
  it("uses the actual session endpoint, refreshes access and logs out in place", async () => {
    mount("/points/tochal");
    await screen.findByRole("heading", { name: "آب‌وهوای قلهٔ توچال" });
    await userEvent.click(screen.getByRole("button", { name: "ورود" }));
    await userEvent.type(screen.getByLabelText("شمارهٔ موبایل"), "۰۹۱۱۱۱۱۱۱۱۱");
    await userEvent.click(screen.getByRole("button", { name: /ادامه/ }));
    await userEvent.type(screen.getByLabelText("کد ورود"), "۱۲۳۴");
    await userEvent.click(screen.getByRole("button", { name: "تأیید و ورود" }));
    await screen.findByText("عضویت رایگان");
    expect(screen.queryByText(/روز باقی/)).toBeNull();
    await waitFor(() => expect(weatherCalls()).toHaveLength(2));
    await userEvent.click(screen.getByRole("button", { name: "خروج از حساب" }));
    await waitFor(() => expect(weatherCalls()).toHaveLength(3));
    const post = fetchMock.mock.calls.find(([url]) =>
      String(url).includes("/auth/login/"),
    );
    expect(JSON.parse(post![1].body)).toEqual({
      phone: "989111111111",
      code: "1234",
    });
  });
  it("shows actual days beside a paid plan without a progress bar", async () => {
    authenticated = true;
    paid = true;
    mount();
    await screen.findByText("۷۴۶");
    await userEvent.click(screen.getByRole("button", { name: "حساب" }));
    expect(screen.getByText(/۴ روز/)).toBeVisible();
    expect(document.querySelector(".account-menu progress")).toBeNull();
  });
  it("preserves the server rejection of a login code", async () => {
    fetchMock.mockImplementation((input: RequestInfo) =>
      String(input).includes("/auth/login/")
        ? response({ detail: "کد معتبر نیست" }, 403)
        : defaultFetch(input),
    );
    mount();
    await screen.findByText("۷۴۶");
    await userEvent.click(screen.getByRole("button", { name: "ورود" }));
    await userEvent.type(screen.getByLabelText("شمارهٔ موبایل"), "09111111111");
    await userEvent.click(screen.getByRole("button", { name: /ادامه/ }));
    await userEvent.type(screen.getByLabelText("کد ورود"), "4321");
    await userEvent.click(screen.getByRole("button", { name: "تأیید و ورود" }));
    expect(await screen.findByText("کد معتبر نیست")).toBeVisible();
  });
  it("keeps old direct login URLs functional with the compact menu", async () => {
    mount("/login?returnTo=%2Fpoints%2Ftochal");
    await screen.findByLabelText("شمارهٔ موبایل");
    expect(screen.getByTestId("location")).toHaveTextContent(
      /^\/points\/tochal$/,
    );
    expect(document.querySelector("dialog")).toBeNull();
  });
  it("opens the login CTA for a locked day without fetching its weather", async () => {
    mount("/points/tochal");
    await screen.findByRole("heading", { name: "آب‌وهوای قلهٔ توچال" });
    await userEvent.click(screen.getByRole("tab", { name: /فردا، ورود/ }));
    expect(screen.getByLabelText("شمارهٔ موبایل")).toBeVisible();
    expect(weatherCalls()).toHaveLength(1);
  });
  it("groups home search points and routes with working internal links", async () => {
    mount();
    await screen.findByText("۷۴۶");
    await userEvent.type(screen.getByRole("combobox"), "توچال");
    await screen.findByRole("option", { name: /دربند تا توچال/ });
    expect(document.querySelectorAll(".search-result")).toHaveLength(2);
    await userEvent.click(
      screen.getByRole("option", { name: /دربند تا توچال/ }),
    );
    await screen.findByRole("heading", { name: "دربند تا توچال" });
  });
  it("navigates to the active search suggestion on Enter", async () => {
    mount();
    await screen.findByText("۷۴۶");
    const input = screen.getByRole("combobox");
    await userEvent.type(input, "توچال");
    await screen.findByRole("option", { name: /قلهٔ توچال/ });
    await userEvent.keyboard("{ArrowDown}{Enter}");
    await screen.findByRole("heading", { name: "آب‌وهوای قلهٔ توچال" });
  });
  it("never chooses a night weather icon based on the light/dark theme", () => {
    document.documentElement.dataset.theme = "dark";
    const { container } = render(
      <WeatherIcon code="clear" at="2026-10-01T08:00:00+03:30" />,
    );
    const morning = container.innerHTML;
    document.documentElement.dataset.theme = "light";
    const { container: night } = render(
      <WeatherIcon code="clear" at="2026-10-01T22:00:00+03:30" />,
    );
    expect(night.innerHTML).not.toBe(morning);
  });
  it("renders the category source at the approved viewBox and stroke", () => {
    const { container } = render(<CategoryIcon placeType="peak" />);
    expect(container.querySelector("svg")).toHaveAttribute(
      "viewBox",
      "0 0 32 32",
    );
    expect(container.querySelector("svg")).toHaveAttribute(
      "stroke-width",
      "1.8",
    );
  });
  it("falls back to HTTP-safe link copy and reports failure honestly", async () => {
    Object.defineProperty(document, "execCommand", {
      configurable: true,
      value: vi.fn(() => true),
    });
    expect(
      await copyShareLink("http://202.133.89.120:5050/routes/tochal-darband"),
    ).toBe(true);
    Object.defineProperty(document, "execCommand", {
      configurable: true,
      value: vi.fn(() => false),
    });
    expect(await copyShareLink("http://202.133.89.120:5050/")).toBe(false);
    expect(document.querySelector("textarea")).toBeNull();
  });
});
