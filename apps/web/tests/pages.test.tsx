import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ThemeProvider } from "../src/app/theme";
import { HomePage } from "../src/pages/HomePage";
import { DestinationPage } from "../src/pages/DestinationPage";
import { RoutePage } from "../src/pages/RoutePage";

const destinationForecast = {
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
  period: { id: "morning", label: "صبح", range_label: "۰۲ تا ۱۰", headline: "تغییرات صبح · هر دو ساعت", hours: [2, 4, 6, 8] },
  current: null,
  hourly: [
    { time: "۰۲:۰۰", hour: 2, temperature_c: 7, temperature_label: "۷°", condition: "صاف", icon: "☼", wind_speed_kmh: 7, wind_label: "باد ۷ km/h", severity: "normal", state: "normal", is_yesterday: false, is_today: true, is_past: true, is_current: false, is_future: false },
  ],
  metrics: [{ icon: "⌁", label: "باد میانگین", value: "۱۰ km/h", note: "جنوب‌غربی", color: "teal" }],
  hero: { status: "الان در قله ۹°", alert: "تغییر مهم" },
  decision: { chip: "امروز · جمع‌بندی هواچ", title: "صبح برای شروع برنامه مناسب‌تر است.", text: "تا ساعت ۱۰ آرام‌تر است." },
  updated_label: "آخرین به‌روزرسانی: امروز، ۰۵:۴۵",
  empty: false,
  meta: { freshness: "ready", generated_at: "2026-08-26T05:45:00+03:30", selected_date: "2026-08-26", selected_period: "morning" },
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
  period: { id: "morning", label: "صبح", range_label: "۰۲ تا ۱۰", hours: [2, 4, 6, 8] },
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
          <Route path="/destination/:slug" element={<DestinationPage />} />
          <Route path="/routes/:slug" element={<RoutePage />} />
        </Routes>
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

  it("renders destination and can open a route", async () => {
    const user = userEvent.setup();
    renderAt("/destination/touchal");
    expect(await screen.findByRole("heading", { name: "قلهٔ توچال" })).toBeInTheDocument();
    expect(document.querySelectorAll(".daypart-toggle").length).toBe(1);
    await user.click(screen.getAllByText("دربند تا توچال")[0]);
    expect(await screen.findByRole("heading", { name: "دربند تا توچال" })).toBeInTheDocument();
  });

  it("renders route sibling navigation and a single period control", async () => {
    renderAt("/routes/touchal-darband");
    expect(await screen.findByRole("heading", { name: "دربند تا توچال" })).toBeInTheDocument();
    expect(screen.getByText("ولنجک تا توچال")).toBeInTheDocument();
    expect(document.querySelectorAll(".daypart-toggle").length).toBe(1);
    expect(screen.getByLabelText("بازگشت به صفحهٔ مقصد")).toBeInTheDocument();
  });

  it("shows error and empty states", async () => {
    vi.stubGlobal("fetch", vi.fn(() => jsonResponse({}, false, 500)));
    renderAt("/");
    expect(await screen.findByText("بارگذاری ناموفق بود")).toBeInTheDocument();
    vi.stubGlobal(
      "fetch",
      vi.fn(() => jsonResponse({ results: [], empty: true, query: "xyz", meta: { freshness: "ready" } })),
    );
    renderAt("/");
    expect(await screen.findByText(/مقصد مرتبطی پیدا نشد/)).toBeInTheDocument();
  });

  it("shows stale notice", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        jsonResponse({
          ...destinationForecast,
          meta: { ...destinationForecast.meta, freshness: "stale" },
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

  it("does not create full-page horizontal overflow at the mobile reference width", async () => {
    Object.defineProperty(HTMLElement.prototype, "scrollWidth", { configurable: true, get: () => 576 });
    Object.defineProperty(HTMLElement.prototype, "clientWidth", { configurable: true, get: () => 576 });
    renderAt("/");
    await screen.findByText("توچال");
    expect(document.documentElement.scrollWidth).toBeLessThanOrEqual(document.documentElement.clientWidth);
  });
});
