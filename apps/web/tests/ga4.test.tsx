import { StrictMode, useLayoutEffect } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, useLocation, useNavigate } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { RoutePageViewTracker } from "../src/app/RoutePageViewTracker";
import {
  createPageViewCoordinator,
  createInitialPageContext,
  analyticsPageLocation,
  ga4ConfigOptions,
  handleGa4ScriptFailure,
  publicAnalyticsPath,
  sanitizeAnalyticsReferrer,
  sanitizeAnalyticsTitle,
  sendGa4PageView,
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

  it("keeps only safe, standard UTM values on the initial public URL", () => {
    expect(analyticsPageLocation(
      "https://hawatch.ir",
      "/points/tochal/",
      "?utm_source=tracking_test&utm_medium=social&utm_campaign=autumn&date=2026-11-02&token=secret&utm_term=user%40example.com&utm_content=09123456789&utm_id=token%3Dsecret",
    )).toBe("https://hawatch.ir/points/tochal?utm_source=tracking_test&utm_medium=social&utm_campaign=autumn");
    expect(analyticsPageLocation("https://hawatch.ir", "/admin/private", "?utm_source=tracking_test"))
      .toBe("https://hawatch.ir/");
  });

  it("reduces external referrers to their origin and same-site referrers to a clean public path", () => {
    expect(sanitizeAnalyticsReferrer("https://search.example/results?q=private#section", "https://hawatch.ir"))
      .toBe("https://search.example/");
    expect(sanitizeAnalyticsReferrer("https://hawatch.ir/points/tochal?token=secret#private", "https://hawatch.ir"))
      .toBe("https://hawatch.ir/points/tochal");
    expect(sanitizeAnalyticsReferrer("javascript:alert(1)", "https://hawatch.ir")).toBe("");
  });

  it("uses the landing UTM/referrer once, then clean internal URLs and virtual referrers", () => {
    const initialPage = createInitialPageContext(
      "https://hawatch.ir",
      "/points/tochal",
      "?utm_source=tracking_test&utm_medium=campaign&date=2026-11-02",
      "https://search.example/query?q=private",
    );
    const sent: Array<{ path: string; title: string; generation: number; pageLocation: string; pageReferrer: string }> = [];
    const coordinator = createPageViewCoordinator((page) => sent.push(page), {
      origin: "https://hawatch.ir",
      initialPage,
    });

    coordinator.navigate("/points/tochal", "?utm_source=tracking_test&utm_medium=campaign&date=2026-11-02");
    coordinator.titleReady("/points/tochal", "آب‌وهوای توچال | هواچ");
    coordinator.navigate("/points/tochal", "?date=2026-11-03"); // planner-only query update
    coordinator.navigate("/routes/tochal-darband", "?date=2026-11-03");
    coordinator.titleReady("/routes/tochal-darband", "مسیر دربند تا توچال | هواچ");

    expect(sent).toHaveLength(2);
    expect(sent[0]).toMatchObject({
      pageLocation: "https://hawatch.ir/points/tochal?utm_source=tracking_test&utm_medium=campaign",
      pageReferrer: "https://search.example/",
    });
    expect(sent[1]).toMatchObject({
      pageLocation: "https://hawatch.ir/routes/tochal-darband",
      pageReferrer: "https://hawatch.ir/points/tochal",
    });
  });

  it("uses the production-tested GA commands with page location/referrer and no automatic view", () => {
    const commands: unknown[][] = [];
    const gtag = (...args: unknown[]) => commands.push(args);
    const page = {
      path: "/points/tochal",
      title: "توچال user@example.com | هواچ",
      generation: 1,
      pageLocation: "https://hawatch.ir/points/tochal?utm_source=tracking_test",
      pageReferrer: "https://search.example/",
    };

    sendGa4PageView(gtag, "G-B9F7GYQ0X8", page);

    expect(commands).toEqual([
      ["config", "G-B9F7GYQ0X8", ga4ConfigOptions(page.pageLocation, page.pageReferrer)],
      ["event", "page_view", {
        page_title: "توچال | هواچ",
        page_location: page.pageLocation,
        page_referrer: page.pageReferrer,
      }],
    ]);
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
          <RoutePageViewTracker onLocation={coordinator.navigate} />
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
