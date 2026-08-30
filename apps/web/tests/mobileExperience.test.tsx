import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { HourlyForecast } from "../src/components/HourlyForecast";
import { DestinationCard } from "../src/components/DestinationCard";
import { MobileRouteSelector } from "../src/components/MobileRouteSelector";
import type { HourlyReading, RouteSummary } from "../src/types";

const routes: RouteSummary[] = [
  {
    slug: "featured-route",
    title: "مسیر پیشنهادی",
    trail_label: "مسیر کوهستانی",
    origin: "مبدأ اول",
    destination_label: "توچال",
    distance_km: 10,
    distance_label: "۱۰ km",
    ascent_m: 1500,
    ascent_label: "۱۵۰۰ m",
    featured: true,
    href: "/routes/featured-route",
    timing_pending: false,
    timing_status: "estimated",
  },
  {
    slug: "second-route",
    title: "مسیر دوم",
    trail_label: "مسیر جنگلی",
    origin: "مبدأ دوم",
    destination_label: "توچال",
    distance_km: 12,
    distance_label: "۱۲ km",
    ascent_m: 1600,
    ascent_label: "۱۶۰۰ m",
    featured: false,
    href: "/routes/second-route",
    timing_pending: false,
    timing_status: "estimated",
  },
  {
    slug: "third-route",
    title: "مسیر سوم",
    trail_label: "مسیر فرعی",
    origin: "مبدأ سوم",
    destination_label: "توچال",
    distance_km: 14,
    distance_label: "۱۴ km",
    ascent_m: 1700,
    ascent_label: "۱۷۰۰ m",
    featured: false,
    href: "/routes/third-route",
    timing_pending: true,
    timing_status: "pending",
  },
];

function reading(time: string, isCurrent: boolean): HourlyReading {
  return {
    time,
    hour: Number(time.slice(0, 2)),
    forecast_at: `2026-08-30T${time}:00+03:30`,
    temperature_c: 10,
    temperature_label: "۱۰°",
    condition: "صاف",
    icon: "☼",
    wind_speed_kmh: 5,
    wind_label: "باد ۵ km/h",
    severity: "normal",
    state: "normal",
    is_yesterday: false,
    is_today: true,
    is_past: !isCurrent,
    is_current: isCurrent,
    is_future: false,
  };
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("mobile route and forecast controls", () => {
  it("shows route elevation and distance without repeating the trail origin", () => {
    render(
      <MemoryRouter>
        <DestinationCard route={routes[0]} />
      </MemoryRouter>,
    );

    expect(screen.getByText("ارتفاع‌گیری: ۱۵۰۰ m")).toBeInTheDocument();
    expect(screen.getByText("مسافت: ۱۰ km")).toBeInTheDocument();
    expect(screen.queryByText(/مسیر کوهستانی/)).not.toBeInTheDocument();
    expect(screen.queryByText(/مبدأ اول/)).not.toBeInTheDocument();
  });

  it("keeps two routes visible and opens the remaining routes in a sheet", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <MobileRouteSelector routes={routes} title="مسیرهای منتهی به توچال" />
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: /مسیر پیشنهادی/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /مسیر دوم/ })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /مسیر سوم/ })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /انتخاب از بین/ }));
    const dialog = screen.getByRole("dialog", { name: "انتخاب مسیر" });
    expect(within(dialog).getByRole("link", { name: /مسیر سوم/ })).toBeInTheDocument();

    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("closes the route sheet through its backdrop", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <MobileRouteSelector routes={routes} title="مسیرهای منتهی به توچال" />
      </MemoryRouter>,
    );
    await user.click(screen.getByRole("button", { name: /انتخاب از بین/ }));
    await user.click(screen.getByRole("button", { name: "بستن پنجرهٔ انتخاب مسیر" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("scrolls the current hourly card into view on mobile", async () => {
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 390 });
    vi.spyOn(window, "matchMedia").mockImplementation((query) =>
      ({ matches: query === "(max-width: 720px)", media: query, onchange: null, addListener: vi.fn(), removeListener: vi.fn(), addEventListener: vi.fn(), removeEventListener: vi.fn(), dispatchEvent: vi.fn() }) as unknown as MediaQueryList,
    );
    vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => {
      callback(0);
      return 1;
    });
    vi.stubGlobal("cancelAnimationFrame", vi.fn());
    const scrollIntoView = vi.fn();
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
      configurable: true,
      value: scrollIntoView,
    });

    render(<HourlyForecast hours={[reading("03:00", false), reading("05:00", true), reading("07:00", false)]} />);

    await waitFor(() => expect(scrollIntoView).toHaveBeenCalledWith({ behavior: "smooth", block: "nearest", inline: "center" }));
    expect(document.querySelectorAll(".hour-item.is-current")).toHaveLength(1);
  });
});
