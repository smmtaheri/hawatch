import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router-dom";
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";
import { ThemeProvider } from "../src/app/theme";
import { AppRoutes } from "../src/app/App";
import { DaySelector } from "../src/components/DaySelector";

function jsonResponse(data: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: async () => data });
}

function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location">{location.pathname}{location.search}</output>;
}

describe("subscription plans", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo) => {
      const url = String(input);
      if (url.includes("/auth/me")) return jsonResponse({}, false, 403);
      if (url.includes("/auth/plans")) {
        return jsonResponse({
          plans: [
            { code: "free", title: "عضویت رایگان", tier: "free", duration_months: null, visible_days_from_yesterday: 2 },
            { code: "professional", title: "طرح حرفه‌ای", tier: "paid", duration_months: 3, visible_days_from_yesterday: 6 },
          ],
          display_day_count: 7,
          anonymous_visible_days_from_yesterday: 1,
        });
      }
      return jsonResponse({}, false, 500);
    }));
  });

  afterEach(() => vi.unstubAllGlobals());

  it("keeps the free plan on the right and sends a guest to the login overlay", async () => {
    const user = userEvent.setup();
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/account/plans"]}>
          <AppRoutes />
        </MemoryRouter>
      </ThemeProvider>,
    );

    expect(await screen.findByRole("heading", { name: "طرح مناسب پیش‌بینی را انتخاب کن" })).toBeInTheDocument();
    const cards = screen.getByRole("region", { name: "طرح‌های اشتراک" });
    expect(cards.querySelector(".subscription-plan-card.free")).toBeTruthy();
    expect(cards.querySelector(".subscription-plan-card.paid")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "ورود برای خرید" }));
    await waitFor(() => expect(screen.getByRole("dialog", { name: "ورود به هواچ" })).toBeInTheDocument());
  });

  it("uses the clean plans URL even when an older continuation query is opened", async () => {
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={["/account/plans?returnTo=%2Fpoints%2Fdamavand%3Fdate%3D2026-09-12"]}>
          <AppRoutes />
          <LocationProbe />
        </MemoryRouter>
      </ThemeProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent(/^\/account\/plans$/));
  });

  it("keeps locked-day actions accessible while rendering an icon-only lock", async () => {
    const onLocked = vi.fn();
    render(
      <DaySelector
        days={[
          { date: "2026-08-28", label: "امروز", jalali: "۷ شهریور", offset: 0, is_yesterday: false, is_today: true, is_past: false, is_future: false, is_current: true, access: "login_required" },
          { date: "2026-08-29", label: "فردا", jalali: "۸ شهریور", offset: 1, is_yesterday: false, is_today: false, is_past: false, is_future: true, is_current: false, access: "plan_required" },
        ]}
        selected="2026-08-28"
        onSelect={vi.fn()}
        onLocked={onLocked}
      />,
    );
    const user = userEvent.setup();
    await user.click(screen.getByRole("tab", { name: "فردا، خرید اشتراک" }));
    expect(onLocked).toHaveBeenCalledWith(expect.objectContaining({ access: "plan_required" }));
    await user.click(screen.getByRole("tab", { name: "امروز، ورود" }));
    expect(onLocked).toHaveBeenCalledWith(expect.objectContaining({ access: "login_required" }));
    expect(document.querySelectorAll(".day-lock-badge")).toHaveLength(2);
    expect(document.querySelectorAll(".day-lock-badge .day-lock-symbol")).toHaveLength(2);
    expect(document.querySelectorAll(".day-tabs button > .day-lock-badge")).toHaveLength(2);
    expect(document.querySelectorAll(".day-tab-copy > .day-lock-badge")).toHaveLength(0);
    expect(screen.queryByText("ورود")).not.toBeInTheDocument();
    expect(screen.queryByText("خرید اشتراک")).not.toBeInTheDocument();
  });
});
