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
import { captureInitialSeoContent, initialSeoContentFor } from "../src/lib/initialSeoContent";
import { HourlyForecast } from "../src/components/HourlyForecast";
import { copyShareLink } from "../src/lib/shareImage";
import { CategoryIcon, WeatherIcon } from "../src/components/DesignIcon";
import {clearWeekCache} from '../src/features/week/WeekForecastPage';
import {weekFixture} from './fixtures/week';
import pointFixture from "./fixtures/point-day.json";
import routeFixture from "./fixtures/route-day.json";
import type { HourlyReading, RouteForecast } from "../src/types";

const day = new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tehran',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
const previous = pointFixture.days[0].date;
const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value));
const response = (data: unknown, status = 200) =>
  Promise.resolve({ ok: status < 400, status, headers:new Headers(), json: async () => data });
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
    String(url).includes("/forecast/") && !String(url).endsWith("/forecast/visit/"),
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
  if (url.pathname.endsWith("/forecast/visit/")) return response({});
  if (url.pathname.endsWith("/forecast/week/")) {
    if (error) return response({},error);
    return response(weekFixture(url.pathname.includes("/routes/")?"route":"point",day,{pending,stale}));
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
  clearWeekCache();
  window.history.replaceState({}, "", "/");
  captureInitialSeoContent();
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

describe("approved week forecast and unchanged public pages", () => {
  it.each([['point', 390], ['point', 1440], ['route', 390], ['route', 1440]] as const)(
    "scrolls to the %s identity header once at entry (%ipx), preserving selection and refresh scroll",
    async (kind, width) => {
      Object.defineProperty(window, 'innerWidth', {configurable: true, value: width});
      const original = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'scrollIntoView');
      const targets: Element[] = [];
      Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
        configurable: true,
        value: function(this: Element) { targets.push(this); },
      });
      try {
        mount(kind === 'point' ? '/points/tochal' : '/routes/tochal-darband', true);
        await waitFor(() => expect(targets).toHaveLength(1));
        expect(targets[0]).toBe(document.querySelector(`.${kind}-page .hero`));
        expect(targets[0].querySelector('h1')).toBeTruthy();
        if (kind === 'point') fireEvent.click(document.querySelector('[data-v4-expand="0"]')!);
        else fireEvent.click(document.querySelector('[data-v4-speed="fast"]')!);
        clearWeekCache();
        fireEvent(window, new Event('focus'));
        await waitFor(() => expect(weatherCalls()).toHaveLength(2));
        await act(async () => { await new Promise(resolve => setTimeout(resolve, 50)); });
        expect(targets).toHaveLength(1);
      } finally {
        if (original) Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', original);
        else delete (HTMLElement.prototype as Partial<HTMLElement>).scrollIntoView;
      }
    },
  );

  for(const path of ['/points/tochal','/routes/tochal-darband']){
    it(`shows the condition below weather icons: ${path}`,async()=>{
      mount(path);
      await waitFor(()=>expect(document.querySelector('.weather-label')).toHaveTextContent('صاف'));
      expect(document.querySelectorAll('.weather-label').length).toBeGreaterThan(1);
      expect(weatherCalls()).toHaveLength(1);
    });
  }
  for(const path of ['/points/tochal','/routes/tochal-darband']){
    it(`preserves server HTML during an API error and replaces it after retry: ${path}`,async()=>{
      const title='پیش‌بینی اولیهٔ سرور';window.history.replaceState({},"",path);document.body.innerHTML=`<div data-seo-initial="true"><article><h1>${title}</h1></article></div>`;captureInitialSeoContent();document.body.innerHTML="";error=500;mount(path);
      await screen.findByRole('button',{name:/تلاش دوباره/});expect(screen.getByRole('heading',{name:title})).toBeVisible();error=0;await userEvent.click(screen.getByRole('button',{name:/تلاش دوباره/}));
      await waitFor(()=>expect(document.getElementById('forecast-v4')).not.toBeNull());expect(weatherCalls()).toHaveLength(2);
    });
  }
  it('records page entry once and never renews it on day selection or weather refresh',async()=>{
    mount('/points/tochal');
    await screen.findByRole('heading',{name:'آب‌وهوای قلهٔ توچال'});
    const visits=()=>fetchMock.mock.calls.filter(([url])=>String(url).endsWith('/forecast/visit/'));
    expect(visits()).toHaveLength(1);
    expect(visits()[0][1]).toMatchObject({method:'POST',credentials:'omit'});
    fireEvent(window,new Event('focus'));
    await new Promise(resolve=>setTimeout(resolve,20));
    expect(visits()).toHaveLength(1);
  });
  it('deduplicates the week request in StrictMode',async()=>{mount('/points/tochal',true);await screen.findByRole('heading',{name:'آب‌وهوای قلهٔ توچال'});expect(weatherCalls()).toHaveLength(1);expect(String(weatherCalls()[0][0])).toMatch(/forecast\/week\/$/);});
  it('expands one day through six, three and one hour and opens details without fetching',async()=>{
    mount('/points/tochal');await screen.findByRole('heading',{name:'آب‌وهوای قلهٔ توچال'});
    for(let i=0;i<3;i++)await userEvent.click(document.querySelector('[data-v4-expand="0"]')!);
    expect(document.querySelectorAll('.stamp').length).toBe(24);await userEvent.click(screen.getByRole('button',{name:'جزئیات تخصصی'}));expect(weatherCalls()).toHaveLength(1);
    await userEvent.click(document.querySelector('[data-v4-collapse="0"]')!);expect(document.querySelectorAll('.stamp').length).toBe(8);
  });
  it('shows felt values with true actual extrema and preserves zero precipitation',async()=>{
    mount('/points/tochal');await screen.findByRole('heading',{name:'آب‌وهوای قلهٔ توچال'});expect(document.querySelector('.chart-value.temperature')).toHaveTextContent('−۷');
    await userEvent.click(screen.getByRole('button',{name:'جزئیات تخصصی'}));expect(document.querySelector('[data-range="90,92"]')).not.toBeNull();
  });
  it('uses all hourly start options and authoritative pace plans without refetching',async()=>{
    mount('/routes/tochal-darband?date='+day+'&start_time=08:00&speed=medium');await screen.findByRole('heading',{name:'دربند تا توچال'});
    await userEvent.click(document.querySelector('[data-v4-menu]')!);expect(screen.getAllByRole('option')).toHaveLength(24);
    await userEvent.click(document.querySelector('[data-v4-start="1380"]')!);await userEvent.click(document.querySelector('[data-v4-speed="slow"]')!);await userEvent.click(document.querySelector('[data-v4-date="7"]')!);
    expect(screen.getByTestId('location')).toHaveTextContent('start_time=23%3A00');expect(screen.getByTestId('location')).toHaveTextContent('speed=slow');expect(weatherCalls()).toHaveLength(1);
  });
  it('keeps pending route timing explicit without fabricated arrivals',async()=>{pending=true;mount('/routes/tochal-darband');expect(await screen.findByText(/زمان‌بندی مسیر هنوز تأیید نشده/)).toBeVisible();await screen.findByRole('heading',{name:'دربند تا توچال'});expect(document.querySelector('.arrival-clock')).toHaveTextContent('—');});
  it('opens canonical route points and shows a route chooser that closes on navigation',async()=>{
    mount('/routes/tochal-darband');await screen.findByRole('heading',{name:'دربند تا توچال'});await userEvent.click(document.querySelector('[data-v4-routes]')!);
    expect(screen.getByRole('dialog')).toBeVisible();await userEvent.click(within(screen.getByRole('dialog')).getByRole('link',{name:'دربند تا توچال'}));expect(screen.queryByRole('dialog')).toBeNull();
    await userEvent.click(document.querySelector('a[data-nav][href="/points/tochal"]')!);await screen.findByRole('heading',{name:'آب‌وهوای قلهٔ توچال'});
  });
  it('explains a past shared program on the current route page',async()=>{mount('/routes/tochal-darband?past_program=1');expect(await screen.findByText(/تاریخ این برنامه گذشته است/)).toBeVisible();await screen.findByRole('heading',{name:'دربند تا توچال'});});
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
    await waitFor(() => expect(weatherCalls()).toHaveLength(1));
    await userEvent.click(screen.getByRole("button", { name: "خروج از حساب" }));
    await waitFor(() => expect(weatherCalls()).toHaveLength(1));
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
