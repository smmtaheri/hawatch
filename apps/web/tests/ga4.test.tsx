import { StrictMode, useLayoutEffect } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, useLocation, useNavigate } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { RoutePageViewTracker } from "../src/app/RoutePageViewTracker";
import {
  createPageViewCoordinator,
  handleGa4ScriptFailure,
  publicAnalyticsPath,
  sanitizeAnalyticsTitle,
  shouldEnableGa4,
} from "../src/lib/ga4";

describe("GA4 configuration and page-view coordination", () => {
  it("enables the configured stream only on the production HTTPS site", () => {
    const production = {
      measurementId: "G-B9F7GYQ0X8",
      hostname: "hawatch.ir",
      protocol: "https:",
      port: "",
      production: true,
      qaPreview: false,
    };

    expect(shouldEnableGa4(production)).toBe(true);
    expect(shouldEnableGa4({ ...production, hostname: "localhost" })).toBe(false);
    expect(shouldEnableGa4({ ...production, protocol: "http:" })).toBe(false);
    expect(shouldEnableGa4({ ...production, port: "5050" })).toBe(false);
    expect(shouldEnableGa4({ ...production, production: false })).toBe(false);
    expect(shouldEnableGa4({ ...production, qaPreview: true })).toBe(false);
    expect(shouldEnableGa4({ ...production, measurementId: "" })).toBe(false);
  });

  it("accepts only public page paths and keeps queries out of the path", () => {
    expect(publicAnalyticsPath("/")).toBe("/");
    expect(publicAnalyticsPath("/destinations/page/2/")).toBe("/destinations/page/2");
    expect(publicAnalyticsPath("/account/plans")).toBe("/account/plans");
    expect(publicAnalyticsPath("/points/tochal/")).toBe("/points/tochal");
    expect(publicAnalyticsPath("/routes/tochal-darband?token=private")).toBeNull();
    expect(publicAnalyticsPath("/admin/analytics")).toBeNull();
    expect(publicAnalyticsPath("/login")).toBeNull();
  });

  it("removes email, phone, and credential-like values from a title", () => {
    expect(sanitizeAnalyticsTitle("قله user@example.com تلفن 09123456789 token=secret"))
      .toBe("قله تلفن");
  });

  it("sends one view per public route transition, waits for the matching title, and ignores query-only state", () => {
    const sent: Array<{ path: string; title: string; generation: number }> = [];
    const tracker = createPageViewCoordinator((page) => sent.push(page));

    // React's child layout effect can publish the SSR title before the router
    // effect reports its first location.
    tracker.titleReady("/", "هواچ | پیش‌بینی هوای کوهستان و مسیرها");
    tracker.navigate("/");
    tracker.navigate("/"); // StrictMode/effect replay
    tracker.titleReady("/", "هواچ | پیش‌بینی هوای کوهستان و مسیرها");

    tracker.navigate("/destinations");
    expect(sent).toHaveLength(1); // waits until the matching title exists
    tracker.titleReady("/destinations", "مقصدهای اصلی هواچ");
    tracker.navigate("/destinations/"); // trailing slash is the same page
    tracker.titleReady("/destinations", "مقصدهای اصلی هواچ"); // query/filter state update

    tracker.navigate("/points/tochal");
    tracker.titleReady("/points/tochal", "آب‌وهوای قلهٔ توچال | هواچ");
    tracker.navigate("/routes/tochal-darband");
    tracker.titleReady("/routes/tochal-darband", "مسیر دربند تا توچال | هواچ");
    tracker.navigate("/points/tochal"); // browser Back
    tracker.titleReady("/points/tochal", "آب‌وهوای قلهٔ توچال | هواچ");

    expect(sent.map(({ path, title }) => [path, title])).toEqual([
      ["/", "هواچ | پیش‌بینی هوای کوهستان و مسیرها"],
      ["/destinations", "مقصدهای اصلی هواچ"],
      ["/points/tochal", "آب‌وهوای قلهٔ توچال | هواچ"],
      ["/routes/tochal-darband", "مسیر دربند تا توچال | هواچ"],
      ["/points/tochal", "آب‌وهوای قلهٔ توچال | هواچ"],
    ]);
  });

  it("does not send a generic loading title for a detail page", () => {
    const sent: Array<{ path: string; title: string; generation: number }> = [];
    const tracker = createPageViewCoordinator((page) => sent.push(page));
    tracker.navigate("/points/tochal");
    expect(sent).toHaveLength(0);
    tracker.titleReady("/points/tochal", "آب‌وهوای قلهٔ توچال | هواچ");
    expect(sent).toHaveLength(1);
  });

  it("tracks direct entry, SPA navigation, query-only changes, and Back once", () => {
    const sent: Array<{ path: string; title: string; generation: number }> = [];
    const coordinator = createPageViewCoordinator((page) => sent.push(page));
    const titleFor = (path: string) => ({
      "/": "خانه | هواچ",
      "/destinations": "فهرست مقصدها | هواچ",
      "/points/tochal": "آب‌وهوای قلهٔ توچال | هواچ",
      "/routes/tochal-darband": "مسیر دربند تا توچال | هواچ",
    })[path] ?? "صفحه | هواچ";

    function Harness() {
      const location = useLocation();
      const navigate = useNavigate();
      useLayoutEffect(() => {
        document.title = titleFor(location.pathname);
        coordinator.titleReady(location.pathname, document.title);
      }, [location.pathname]);
      return (
        <>
          <RoutePageViewTracker onPathname={coordinator.navigate} />
          <button onClick={() => navigate("/destinations")}>destinations</button>
          <button onClick={() => navigate("?date=2030-01-01&period=night")}>change filter</button>
          <button onClick={() => navigate("/points/tochal")}>point</button>
          <button onClick={() => navigate("/routes/tochal-darband")}>route</button>
          <button onClick={() => navigate(-1)}>back</button>
          <button onClick={() => navigate(1)}>forward</button>
        </>
      );
    }

    render(
      <StrictMode>
        <MemoryRouter initialEntries={["/?date=2030-01-01&token=private"]}>
          <Harness />
        </MemoryRouter>
      </StrictMode>,
    );
    fireEvent.click(screen.getByRole("button", { name: "destinations" }));
    fireEvent.click(screen.getByRole("button", { name: "change filter" }));
    fireEvent.click(screen.getByRole("button", { name: "point" }));
    fireEvent.click(screen.getByRole("button", { name: "route" }));
    fireEvent.click(screen.getByRole("button", { name: "back" }));
    fireEvent.click(screen.getByRole("button", { name: "forward" }));

    expect(sent.map(({ path, title }) => [path, title])).toEqual([
      ["/", "خانه | هواچ"],
      ["/destinations", "فهرست مقصدها | هواچ"],
      ["/points/tochal", "آب‌وهوای قلهٔ توچال | هواچ"],
      ["/routes/tochal-darband", "مسیر دربند تا توچال | هواچ"],
      ["/points/tochal", "آب‌وهوای قلهٔ توچال | هواچ"],
      ["/routes/tochal-darband", "مسیر دربند تا توچال | هواچ"],
    ]);
  });

  it("clears the queued GA commands when the Google script is blocked", () => {
    window.dataLayer = [["config", "G-B9F7GYQ0X8"], ["event", "page_view"]];
    window.gtag = () => undefined;
    window.__hawatchGa4State = "loading";

    expect(() => handleGa4ScriptFailure()).not.toThrow();
    expect(window.__hawatchGa4State).toBe("failed");
    expect(window.dataLayer).toEqual([]);

    delete window.dataLayer;
    delete window.gtag;
    delete window.__hawatchGa4State;
  });
});
