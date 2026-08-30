import { render, screen, cleanup, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ThemeProvider } from "../src/app/theme";
import { AppRoutes } from "../src/app/App";
import { HomePage } from "../src/pages/HomePage";
import { LoginPage } from "../src/pages/LoginPage";
import { DestinationPage } from "../src/pages/DestinationPage";
import { RoutePage } from "../src/pages/RoutePage";
import { PointDetailPage } from "../src/pages/PointDetailPage";

const destinationForecast = {
  subject: {
    kind: "destination" as const,
    slug: "touchal",
    weather_point_slug: "tochal_summit",
    canonical_href: "/destination/touchal",
    name: "قلهٔ توچال",
    elevation_m: 3964,
    elevation_label: "۳۹۶۴ متر",
    latitude: 35.88,
    longitude: 51.42,
    context_label: "کوه · البرز مرکزی",
    hero_image: "/images/touchal-banner-clean.png",
    hero_image_alt: "نمای کوهستان توچال",
    region: "تهران",
    category: "کوه · البرز مرکزی",
  },
  destination: {
    slug: "touchal",
    tile_name: "توچال",
    name: "قلهٔ توچال",
    short_category: "کوه",
    category: "کوه · البرز مرکزی",
    category_key: "mountain",
    region: "تهران",
    elevation_m: 3964,
    elevation_label: "۳۹۶۴ متر",
    image: "/images/touchal-banner-clean.png",
    image_alt: "نمای کوهستان توچال",
    href: "/destination/touchal",
    is_popular: true,
    routes: [
      {
        slug: "touchal-darband",
        title: "دربند تا توچال",
        trail_label: "ترک کوه‌پیمایی",
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
  },
  days: [
    { date: "2026-08-25", label: "دیروز", jalali: "۳ شهریور", offset: -1, is_yesterday: true, is_today: false, is_past: true, is_future: false, is_current: false },
    { date: "2026-08-26", label: "امروز", jalali: "۴ شهریور", offset: 0, is_yesterday: false, is_today: true, is_past: false, is_future: false, is_current: true },
  ],
  period: { id: "morning", label: "صبح", range_label: "۰۳ تا ۱۱", headline: "تغییرات صبح · هر دو ساعت", hours: [3, 5, 7, 9] },
  current: null,
  hourly: [
    { time: "۰۳:۰۰", hour: 3, temperature_c: 7, temperature_label: "۷°", condition: "صاف", icon: "☼", wind_speed_kmh: 7, wind_label: "باد ۷ km/h", severity: "normal", state: "normal", is_yesterday: false, is_today: true, is_past: true, is_current: false, is_future: false },
  ],
  metrics: [{ icon: "wind-average", label: "باد میانگین", value: "۱۰ km/h", note: "جنوب‌غربی", color: "teal" }],
  hero: { status: "الان در قله ۹°", alert: "تغییر مهم" },
  decision: { chip: "امروز · جمع‌بندی هواچ", title: "صبح برای شروع برنامه مناسب‌تر است.", text: "تا ساعت ۱۱ آرام‌تر است." },
  related_routes: [
    {
      slug: "touchal-darband",
      title: "دربند تا توچال",
      trail_label: "ترک کوه‌پیمایی",
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
  related_routes_title: "مسیرهای منتهی به توچال",
  updated_label: "آخرین به‌روزرسانی: امروز، ۰۵:۴۵",
  empty: false,
  meta: { freshness: "ready", generated_at: "2026-08-26T05:45:00+03:30", current_local_time: "2026-08-26T06:00:00+03:30", selected_date: "2026-08-26", selected_period: "morning" },
  forecast: {
    days: [
      { date: "2026-08-25", label: "دیروز", jalali: "۳ شهریور", offset: -1, is_yesterday: true, is_today: false, is_past: true, is_future: false, is_current: false },
      { date: "2026-08-26", label: "امروز", jalali: "۴ شهریور", offset: 0, is_yesterday: false, is_today: true, is_past: false, is_future: false, is_current: true },
    ],
    period: { id: "morning", label: "صبح", range_label: "۰۳ تا ۱۱", headline: "تغییرات صبح · هر دو ساعت", hours: [3, 5, 7, 9] },
    current: null,
    hourly: [
      { time: "۰۳:۰۰", hour: 3, temperature_c: 7, temperature_label: "۷°", condition: "صاف", icon: "☼", wind_speed_kmh: 7, wind_label: "باد ۷ km/h", severity: "normal", state: "normal", is_yesterday: false, is_today: true, is_past: true, is_current: false, is_future: false },
    ],
    meta: { freshness: "ready", generated_at: "2026-08-26T05:45:00+03:30", current_local_time: "2026-08-26T06:00:00+03:30", selected_date: "2026-08-26", selected_period: "morning" },
  },
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
    siblings: [
      { slug: "touchal-welanjak", title: "ولنجک تا توچال", trail_label: "ترک", origin: "ولنجک", destination_label: "قلهٔ توچال", distance_km: 14.8, distance_label: "۱۴٫۸ km", ascent_m: 2160, ascent_label: "۲۱۶۰ m", featured: false, href: "/routes/touchal-welanjak" },
    ],
  },
  days: destinationForecast.days,
  period: { id: "morning", label: "صبح", range_label: "۰۳ تا ۱۱", hours: [3, 5, 7, 9] },
  start_minutes: 360,
  start_time: "۰۶:۰۰",
  speed: "متوسط",
  speed_options: ["آرام", "متوسط", "سریع"],
  points: [
    { slug: "darband", name: "دربند", elevation_label: "۱۸۰۰ m", href: "/routes/touchal-darband/points/darband", axis_x: 10, axis_y: 83, time: "۰۶:۰۰", temp: 8, wind: 6, icon: "☼", condition: "شروع آرام", state: "normal", note: "شروع آرام", arrival_minutes: 360 },
  ],
  hourly: destinationForecast.hourly,
  hero: { status: "نقطهٔ حساس: گردنهٔ لوپ" },
  stats: [{ label: "مسافت", value: "۱۶٫۲ km" }],
  decision: {
    chip: "پیش‌بینی مسیر · امروز",
    title: "با حرکت ساعت ۰۶:۰۰، حدود ۱۳:۰۰ به مقصد می‌رسی.",
    status: "هشدار",
    state: "critical",
    summary: "شرایط پرریسک",
    hero_status: "نقطهٔ حساس",
    critical_name: "گردنهٔ لوپ",
    critical_time: "۱۰:۴۵",
    critical_note: "زمان ذخیره",
    recommendations: ["برگرد اگر دید محدود است."],
    start: "۰۶:۰۰",
    finish: "۱۳:۰۰",
    speed: "متوسط",
  },
  empty: false,
  meta: destinationForecast.meta,
};

function jsonResponse(data: unknown, ok = true, status = 200) {
  return Promise.resolve({
    ok,
    status,
    json: async () => data,
  });
}

function renderAt(path: string) {
  return render(
    <ThemeProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/destination/:slug" element={<DestinationPage />} />
          <Route path="/routes/:slug" element={<RoutePage />} />
        </Routes>
      </MemoryRouter>
    </ThemeProvider>,
  );
}

function renderApplication(path: string) {
  return render(
    <ThemeProvider>
      <MemoryRouter initialEntries={[path]}>
        <AppRoutes />
      </MemoryRouter>
    </ThemeProvider>,
  );
}

describe("Hawatch pages", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo) => {
        const url = String(input);
        if (url.includes("/destinations/touchal/forecast")) return jsonResponse(destinationForecast);
        if (url.includes("/routes/touchal-darband/forecast")) return jsonResponse(routeForecast);
        if (url.includes("/destinations/")) {
          return jsonResponse({ results: [destinationForecast.destination], empty: false, query: "", meta: { freshness: "ready" } });
        }
        if (url.includes("/search/suggestions")) {
          return jsonResponse({
            query: "پس",
            results: [
              {
                type: "point",
                slug: "pas_ghaleh",
                label: "پس‌قلعه",
                hint: "نقطهٔ مسیر · توچال",
                href: "/points/pas_ghaleh",
                match_kind: "name",
              },
            ],
            empty: false,
            meta: { freshness: "ready" },
          });
        }
        return jsonResponse({}, false, 500);
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    document.documentElement.removeAttribute("style");
  });

  it("renders home, destination and route", async () => {
    renderAt("/");
    expect(await screen.findByText("توچال")).toBeInTheDocument();
    expect(screen.getAllByLabelText("تغییر تم").length).toBeGreaterThan(0);
  });

  it("opens a route-backed login overlay from the shared header", async () => {
    const user = userEvent.setup();
    renderApplication("/");
    await screen.findByText("توچال");
    await user.click(screen.getByRole("link", { name: "ورود" }));
    const dialog = await screen.findByRole("dialog", { name: "ورود به هواچ" });
    expect(within(dialog).getByLabelText("شمارهٔ موبایل")).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "دریافت کد ورود" })).toBeDisabled();
    expect(within(dialog).getByText("ورود پیامکی هنوز فعال نشده است.")).toBeInTheDocument();
    expect(document.title).toBe("هوای ورود | هواچ");
    await user.click(within(dialog).getByRole("button", { name: "بستن ورود" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(document.title).toBe("هواچ | هوای مقصد، برنامهٔ مسیر");
  });

  it("renders a full login surface for a direct login URL", async () => {
    renderAt("/login?returnTo=%2Fdestination%2Ftouchal");
    expect(await screen.findByRole("heading", { name: "ورود به هواچ" })).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByText("ورود پیامکی هنوز فعال نشده است.")).toBeInTheDocument();
  });

  it("renders destination and can open a route", async () => {
    const user = userEvent.setup();
    renderAt("/destination/touchal");
    expect(await screen.findByRole("heading", { name: "قلهٔ توچال" })).toBeInTheDocument();
    expect(document.querySelector('.specialist-metric-icon use')).toHaveAttribute(
      "href",
      "/icons/specialist/hawatch-specialist-icons.svg#icon-wind-average",
    );
    expect(document.querySelectorAll(".daypart-toggle").length).toBe(1);
    await user.click(screen.getAllByText("دربند تا توچال")[0]);
    expect(await screen.findByRole("heading", { name: "دربند تا توچال" })).toBeInTheDocument();
  });

  it("renders route sibling navigation and a single period control", async () => {
    renderAt("/routes/touchal-darband");
    expect(await screen.findByRole("heading", { name: "دربند تا توچال" })).toBeInTheDocument();
    expect(screen.getByText("ولنجک تا توچال")).toBeInTheDocument();
    expect(document.querySelectorAll(".daypart-toggle").length).toBe(1);
    expect(screen.getByRole("button", { name: "بازگشت به صفحهٔ قبل" })).toBeInTheDocument();
    expect(document.title).toBe("هوای دربند تا توچال | هواچ");

    const pointWeather = screen.getByLabelText("آب‌وهوای متناظر با نقاط مهم مسیر");
    expect(within(pointWeather).getByText("8°")).toBeInTheDocument();
    expect(pointWeather.querySelector(".route-point-weather-condition")).toBeInTheDocument();
  });

  it("shows error and empty states", async () => {
    vi.stubGlobal("fetch", vi.fn(() => jsonResponse({}, false, 500)));
    renderAt("/");
    expect(await screen.findByText("بارگذاری ناموفق بود")).toBeInTheDocument();
    cleanup();
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo) => {
        const url = String(input);
        if (url.includes("/search/suggestions")) {
          return jsonResponse({ query: "xyz", results: [], empty: true, meta: { freshness: "ready" } });
        }
        if (url.includes("/destinations/")) {
          return jsonResponse({ results: [destinationForecast.destination], empty: false, query: "", meta: { freshness: "ready" } });
        }
        return jsonResponse({}, false, 500);
      }),
    );
    const user = userEvent.setup();
    renderAt("/");
    await screen.findByText("توچال");
    const input = screen.getByRole("combobox", { name: "جست‌وجوی مقصد یا نقطهٔ مسیر" });
    await user.type(input, "xyz");
    await user.click(screen.getByRole("button", { name: "جست‌وجو" }));
    expect(await screen.findByText(/نتیجه‌ای پیدا نشد/)).toBeInTheDocument();
  });

  it("shows stale notice", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        jsonResponse({
          ...destinationForecast,
          meta: { ...destinationForecast.meta, freshness: "stale" },
          forecast: {
            ...destinationForecast.forecast,
            meta: { ...destinationForecast.forecast.meta, freshness: "stale" },
          },
        }),
      ),
    );
    renderAt("/destination/touchal");
    expect(await screen.findByText(/ممکن است قدیمی باشد/)).toBeInTheDocument();
  });

  it("switches theme without losing the page", async () => {
    const user = userEvent.setup();
    renderAt("/");
    await screen.findByText("توچال");
    await user.click(screen.getAllByLabelText("تغییر تم")[0]);
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("shows autocomplete suggestions while typing", async () => {
    const user = userEvent.setup();
    renderAt("/");
    await screen.findByText("توچال");
    const input = screen.getByRole("combobox", { name: "جست‌وجوی مقصد یا نقطهٔ مسیر" });
    await user.type(input, "پس");
    expect(await screen.findByText("پس‌قلعه")).toBeInTheDocument();
    expect(screen.getByText(/نقطهٔ مسیر · توچال/)).toBeInTheDocument();
  });

  it("ignores stale autocomplete responses", async () => {
    let resolveSlow: ((value: unknown) => void) | undefined;
    const slow = new Promise((resolve) => {
      resolveSlow = resolve;
    });
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo) => {
        const url = String(input);
        if (url.includes("/search/suggestions?q=%D9%BE%D8%B3%D8%B3")) {
          return slow;
        }
        if (url.includes("/search/suggestions")) {
          return jsonResponse({
            query: "پس",
            results: [
              {
                type: "point",
                slug: "pas_ghaleh",
                label: "پس‌قلعه",
                hint: "نقطهٔ مسیر · توچال",
                href: "/points/pas_ghaleh",
                match_kind: "name",
              },
            ],
            empty: false,
            meta: { freshness: "ready" },
          });
        }
        if (url.includes("/destinations/")) {
          return jsonResponse({ results: [destinationForecast.destination], empty: false, query: "", meta: { freshness: "ready" } });
        }
        return jsonResponse({}, false, 500);
      }),
    );
    const user = userEvent.setup();
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/"]}>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/points/:slug" element={<PointDetailPage />} />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>,
    );
    await screen.findByText("توچال");
    const input = screen.getByRole("combobox", { name: "جست‌وجوی مقصد یا نقطهٔ مسیر" });
    await user.type(input, "پ");
    await user.type(input, "s");
    await user.type(input, "s");
    resolveSlow?.({
      ok: true,
      status: 200,
      json: async () => ({
        query: "pss",
        results: [{ type: "point", slug: "stale", label: "قدیمی", hint: "", href: "/points/stale", match_kind: "name" }],
        empty: false,
        meta: { freshness: "ready" },
      }),
    });
    expect(await screen.findByText("پس‌قلعه")).toBeInTheDocument();
    expect(screen.queryByText("قدیمی")).not.toBeInTheDocument();
  });

  it("submits unified search for a point query via search button", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo) => {
        const url = String(input);
        if (url.includes("/search/suggestions")) {
          return jsonResponse({
            query: "پس",
            results: [
              {
                type: "point",
                slug: "pas_ghaleh",
                label: "پس‌قلعه",
                hint: "نقطهٔ مسیر · توچال",
                href: "/points/pas_ghaleh",
                match_kind: "name",
              },
              {
                type: "point",
                slug: "other_point",
                label: "نقطهٔ دیگر",
                hint: "نقطهٔ مسیر · توچال",
                href: "/points/other_point",
                match_kind: "name",
              },
            ],
            empty: false,
            meta: { freshness: "ready" },
          });
        }
        if (url.includes("/destinations/")) {
          return jsonResponse({ results: [destinationForecast.destination], empty: false, query: "", meta: { freshness: "ready" } });
        }
        return jsonResponse({}, false, 500);
      }),
    );
    const user = userEvent.setup();
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/"]}>
          <Routes>
            <Route path="/" element={<HomePage />} />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>,
    );
    await screen.findByText("توچال");
    const input = screen.getByRole("combobox", { name: "جست‌وجوی مقصد یا نقطهٔ مسیر" });
    await user.type(input, "پس");
    await user.click(screen.getByRole("button", { name: "جست‌وجو" }));
    expect(await screen.findByRole("link", { name: /پس‌قلعه/ })).toHaveAttribute("href", "/points/pas_ghaleh");
    expect(screen.getAllByText(/نقطهٔ مسیر · توچال/).length).toBeGreaterThan(0);
    expect(screen.getByText("نتایج مرتبط")).toBeInTheDocument();
  });

  it("shows an error and retry action when unified search fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo) => {
        const url = String(input);
        if (url.includes("/search/suggestions")) return jsonResponse({}, false, 503);
        if (url.includes("/destinations/")) {
          return jsonResponse({ results: [destinationForecast.destination], empty: false, query: "", meta: { freshness: "ready" } });
        }
        return jsonResponse({}, false, 500);
      }),
    );
    const user = userEvent.setup();
    renderAt("/");
    await screen.findByText("توچال");
    const input = screen.getByRole("combobox", { name: "جست‌وجوی مقصد یا نقطهٔ مسیر" });
    await user.type(input, "پس");
    await user.click(screen.getByRole("button", { name: "جست‌وجو" }));
    expect(await screen.findByText("جست‌وجوی مقصد یا نقطهٔ مسیر ناموفق بود. دوباره تلاش کن.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "تلاش دوباره" })).toBeInTheDocument();
  });

  it("navigates to point on Enter with active suggestion", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo) => {
        const url = String(input);
        if (url.includes("/search/suggestions")) {
          return jsonResponse({
            query: "پس",
            results: [
              {
                type: "point",
                slug: "pas_ghaleh",
                label: "پس‌قلعه",
                hint: "نقطهٔ مسیر · توچال",
                href: "/points/pas_ghaleh",
                match_kind: "name",
              },
            ],
            empty: false,
            meta: { freshness: "ready" },
          });
        }
        if (url.includes("/points/pas_ghaleh/forecast")) {
          return jsonResponse({
            subject: {
              kind: "point" as const,
              slug: "pas_ghaleh",
              weather_point_slug: "pas_ghaleh",
              canonical_href: "/points/pas_ghaleh",
              name: "پس‌قلعه",
              elevation_m: 1936,
              elevation_label: "۱۹۳۶ متر",
              latitude: 35.836,
              longitude: 51.423,
              context_label: "تهران",
              hero_image: "/images/touchal-banner-clean.png",
              hero_image_alt: "توچال",
              region: "تهران",
              category: "کوه",
            },
            point: {
              slug: "pas_ghaleh",
              name: "پس‌قلعه",
              aliases: [],
              kind: "shared",
              elevation_m: 1936,
              elevation_label: "۱۹۳۶ m",
              latitude: 35.836,
              longitude: 51.423,
              status: "approved",
              provenance: "curated",
              href: "/points/pas_ghaleh",
              canonical_href: "/points/pas_ghaleh",
              destination: destinationForecast.destination,
            },
            related_destinations: [destinationForecast.destination],
            related_routes: [],
            related_routes_title: "مسیرهای عبوری از این نقطه",
            days: destinationForecast.days,
            period: destinationForecast.period,
            current: destinationForecast.hourly[0],
            weather: destinationForecast.hourly[0],
            hourly: destinationForecast.hourly,
            metrics: [],
            hero: { status: "☼　در پس‌قلعه　۷°　·　صاف", alert: "✓　شرایط فعلاً آرام‌تر است" },
            decision: { chip: "امروز · جمع‌بندی هواچ", title: "صبح", text: "آرام" },
            updated_label: "امروز",
            empty: false,
            partial: false,
            meta: destinationForecast.meta,
            forecast: {
              days: destinationForecast.forecast.days,
              period: destinationForecast.forecast.period,
              current: destinationForecast.hourly[0],
              hourly: destinationForecast.hourly,
              meta: destinationForecast.forecast.meta,
            },
          });
        }
        if (url.includes("/destinations/")) {
          return jsonResponse({ results: [destinationForecast.destination], empty: false, query: "", meta: { freshness: "ready" } });
        }
        return jsonResponse({}, false, 500);
      }),
    );
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/"]}>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/points/:slug" element={<PointDetailPage />} />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>,
    );
    await screen.findByText("توچال");
    const user = userEvent.setup();
    const input = screen.getByRole("combobox", { name: "جست‌وجوی مقصد یا نقطهٔ مسیر" });
    await user.type(input, "پس");
    await user.keyboard("{Enter}");
    expect(await screen.findByRole("heading", { name: "پس‌قلعه" })).toBeInTheDocument();
  });

  it("does not create full-page horizontal overflow at the mobile reference width", async () => {
    Object.defineProperty(HTMLElement.prototype, "scrollWidth", { configurable: true, get: () => 576 });
    Object.defineProperty(HTMLElement.prototype, "clientWidth", { configurable: true, get: () => 576 });
    renderAt("/");
    await screen.findByText("توچال");
    expect(document.documentElement.scrollWidth).toBeLessThanOrEqual(document.documentElement.clientWidth);
  });
});
