import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { HourlyForecast } from "../src/components/HourlyForecast";
import { PointCard } from "../src/components/PointCard";
import { DestinationIcon, PointIcon } from "../src/components/PointIcon";
import { DesktopRouteSelector } from "../src/components/DesktopRouteSelector";
import { MobileRouteSelector } from "../src/components/MobileRouteSelector";
import { RouteSiblingNavigation } from "../src/components/RouteSiblingNavigation";
import { SpecialistMetrics } from "../src/components/SpecialistMetrics";
import type { HourlyReading, Metric, RouteSummary } from "../src/types";

const routes: RouteSummary[] = [
  {
    slug: "featured-route",
    title: "مسیر پیشنهادی",
    trail_label: "مسیر کوهستانی",
    origin: "مبدأ اول",
    target_label: "توچال",
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
    target_label: "توچال",
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
    target_label: "توچال",
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

const metrics: Metric[] = [
  { icon: "wind-average", label: "باد", value: "۱۰ km/h", note: "ملایم", color: "teal" },
  { icon: "precipitation", label: "بارش", value: "۵٪", note: "کم", color: "teal" },
  { icon: "visibility", label: "دید", value: "بیش از ۱۰ km", note: "خوب", color: "teal" },
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
  it("renders a waterfall icon from the database category key", () => {
    const { container } = render(<PointIcon categoryKey="waterfall" />);
    expect(container.querySelector(".point-icon.waterfall")).toBeInTheDocument();
  });

  it("keeps ridge destinations in the mountain icon family", () => {
    const { container } = render(<PointIcon categoryKey="ridge" />);
    expect(container.querySelector(".point-icon.mountain")).toBeInTheDocument();
    expect(container.querySelector(".point-icon.nature")).not.toBeInTheDocument();
  });

  it("renders volcanic destinations with the volcano icon", () => {
    const { container } = render(<PointIcon categoryKey="volcano" />);
    expect(container.querySelector(".point-icon.volcano")).toBeInTheDocument();
    expect(container.querySelector(".point-icon.mountain")).not.toBeInTheDocument();
  });

  it("renders the beach category as its own destination icon", () => {
    const { container } = render(<PointIcon categoryKey="beach" />);
    expect(container.querySelector(".point-icon.beach")).toBeInTheDocument();
  });

  it("derives the lake icon when an older profile omitted category_key", () => {
    const { container } = render(<PointIcon categoryKey="" placeType="lake" />);
    expect(container.querySelector(".point-icon.lake")).toBeInTheDocument();
    expect(container.querySelector(".point-icon.nature")).not.toBeInTheDocument();
  });

  it("derives the rural-village artwork when an older profile omitted category_key", () => {
    const { container } = render(
      <DestinationIcon categoryKey="" placeType="village" className="destination-card-icon" />,
    );
    expect(container.querySelector(".destination-artwork.village")).toBeInTheDocument();
    expect(container.querySelector(".point-icon.nature")).not.toBeInTheDocument();
  });

  it("keeps neighborhoods distinct from rural-village artwork", () => {
    const { container } = render(
      <DestinationIcon categoryKey="" placeType="neighborhood" className="destination-card-icon" />,
    );
    expect(container.querySelector(".destination-artwork.neighborhood")).toBeInTheDocument();
    expect(container.querySelector(".destination-artwork.village")).not.toBeInTheDocument();
  });

  it("uses a separate city artwork for city destinations", () => {
    const { container } = render(
      <DestinationIcon categoryKey="" placeType="city" className="destination-card-icon" />,
    );
    expect(container.querySelector(".destination-artwork.city")).toBeInTheDocument();
    expect(container.querySelector(".destination-artwork.neighborhood")).not.toBeInTheDocument();
  });

  it("keeps approved destination artwork inside the shared icon frame", () => {
    const { container } = render(
      <DestinationIcon categoryKey="waterfall" className="destination-card-icon" />,
    );
    expect(container.querySelector(".destination-icon.destination-card-icon")).toBeInTheDocument();
    expect(container.querySelector(".destination-artwork.waterfall")).toBeInTheDocument();
    expect(container.querySelector("svg")).not.toBeInTheDocument();
  });

  it("uses approved artwork through the shared destination wrapper", () => {
    const { container } = render(
      <DestinationIcon categoryKey="desert" className="tile-icon" />,
    );
    expect(container.querySelector(".destination-icon.tile-icon")).toBeInTheDocument();
    expect(container.querySelector(".destination-artwork.desert")).toBeInTheDocument();
    expect(container.querySelector(".point-icon.desert")).not.toBeInTheDocument();
  });

  it("keeps the coast alias in the approved beach-artwork family", () => {
    const { container } = render(
      <DestinationIcon categoryKey="coast" className="tile-icon" />,
    );
    expect(container.querySelector(".destination-artwork.beach")).toBeInTheDocument();
  });

  it("keeps the destination wrapper's place-type fallback for lakes", () => {
    const { container } = render(
      <DestinationIcon categoryKey="" placeType="lake" className="destination-card-icon" />,
    );
    expect(container.querySelector(".point-icon.lake")).toBeInTheDocument();
  });

  it("does not mislabel an unsupported category as a mountain", () => {
    const { container } = render(<PointIcon categoryKey="unknown-place-type" />);
    expect(container.querySelector(".point-icon.nature")).toBeInTheDocument();
    expect(container.querySelector(".point-icon.peak")).not.toBeInTheDocument();
  });

  it("shows route elevation and distance without repeating the trail origin", () => {
    render(
      <MemoryRouter>
        <PointCard route={routes[0]} />
      </MemoryRouter>,
    );

    expect(screen.getByText("ارتفاع‌گیری: ۱۵۰۰ m")).toBeInTheDocument();
    expect(screen.getByText("مسافت: ۱۰ km")).toBeInTheDocument();
    expect(document.querySelectorAll(".route-details .route-detail")).toHaveLength(2);
    expect(screen.queryByText(/مسیر کوهستانی/)).not.toBeInTheDocument();
    expect(screen.queryByText(/مبدأ اول/)).not.toBeInTheDocument();
    expect(screen.queryByText("پیشنهاد هواچ")).not.toBeInTheDocument();
    expect(screen.getByRole("link")).not.toHaveClass("recommended");
  });

  it("keeps two specialist metrics inline and opens the rest in a sheet", async () => {
    const user = userEvent.setup();
    render(<SpecialistMetrics metrics={metrics} dayLabel="امروز" />);

    expect(document.querySelectorAll(".specialist-metrics-preview .metric")).toHaveLength(2);
    await user.click(screen.getByRole("button", { name: "دیدن همهٔ جزئیات تخصصی امروز" }));
    expect(within(screen.getByRole("dialog", { name: /جزئیات تخصصی امروز/ })).getByText("دید")).toBeInTheDocument();
  });

  it("keeps two routes visible and opens the remaining routes in a sheet", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <MobileRouteSelector routes={routes} title="مسیرهای منتهی به توچال" />
      </MemoryRouter>,
    );

    expect(screen.getByText("تصمیم بعدی")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /مسیر پیشنهادی/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /مسیر دوم/ })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /مسیر سوم/ })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "دیدن همهٔ مسیرها" }));
    const dialog = screen.getByRole("dialog", { name: "انتخاب مسیر" });
    expect(within(dialog).getByRole("link", { name: /مسیر سوم/ })).toBeInTheDocument();

    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("keeps the first four database-ranked routes visible on desktop", async () => {
    const user = userEvent.setup();
    const fiveRoutes = [
      ...routes,
      {
        ...routes[0],
        slug: "fourth-route",
        title: "مسیر چهارم",
        href: "/routes/fourth-route",
      },
      {
        ...routes[0],
        slug: "fifth-route",
        title: "مسیر پنجم",
        href: "/routes/fifth-route",
      },
    ];

    render(
      <MemoryRouter>
        <DesktopRouteSelector routes={fiveRoutes} title="مسیرهای منتهی به توچال" />
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: /مسیر پیشنهادی/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /مسیر چهارم/ })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /مسیر پنجم/ })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "دیدن باقی مسیرها" }));
    expect(within(screen.getByRole("menu", { name: "مسیرهای بیشتر" })).getByRole("menuitem", { name: /مسیر پنجم/ })).toBeInTheDocument();
  });

  it("keeps a single desktop route compact and restores missing numeric labels", () => {
    const singleRoute = {
      ...routes[0],
      distance_label: "—",
      ascent_label: "—",
    };
    render(
      <MemoryRouter>
        <DesktopRouteSelector routes={[singleRoute]} title="مسیرهای منتهی به توچال" />
      </MemoryRouter>,
    );

    expect(document.querySelector(".desktop-route-selection")).toHaveClass("single-route");
    expect(screen.queryByRole("button", { name: "دیدن باقی مسیرها" })).not.toBeInTheDocument();
    expect(screen.getByText("ارتفاع‌گیری: ۱۵۰۰ m")).toBeInTheDocument();
    expect(screen.getByText("مسافت: ۱۰ km")).toBeInTheDocument();
  });

  it("uses a compact trigger when route alternatives belong in a route hero", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <MobileRouteSelector routes={routes.slice(1)} title="مسیرهای دیگر توچال" variant="trigger" />
      </MemoryRouter>,
    );

    expect(screen.getByRole("button", { name: /مسیرهای دیگر/ })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /مسیر دوم/ })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /مسیرهای دیگر/ }));
    expect(within(screen.getByRole("dialog", { name: "انتخاب مسیر" })).getByRole("link", { name: /مسیر دوم/ })).toBeInTheDocument();
  });

  it("closes the route menu as soon as another route is selected", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <RouteSiblingNavigation
          parentName="توچال"
          currentRoute={{ title: "مسیر فعلی", href: "/routes/current-route" }}
          routes={[routes[1]]}
        />
      </MemoryRouter>,
    );

    await user.click(screen.getByText("تغییر مسیر"));
    const details = document.querySelector(".route-sibling-details");
    expect(details).toHaveAttribute("open");
    await user.click(screen.getByRole("link", { name: /مسیر دوم/ }));
    expect(details).not.toHaveAttribute("open");
  });

  it("closes the route sheet through its backdrop", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <MobileRouteSelector routes={routes} title="مسیرهای منتهی به توچال" />
      </MemoryRouter>,
    );
    await user.click(screen.getByRole("button", { name: "دیدن همهٔ مسیرها" }));
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
