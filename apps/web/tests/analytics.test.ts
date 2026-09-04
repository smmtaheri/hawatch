import { afterEach, describe, expect, it, vi } from "vitest";
import { trackPageView } from "../src/api/client";

describe("internal analytics", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("sends a first-party point navigation with an anonymous visitor token", () => {
    const fetchMock = vi.fn<typeof fetch>(() => Promise.resolve(new Response(null, { status: 201 })));
    vi.stubGlobal("fetch", fetchMock);

    trackPageView("point", "tochal", "navigation-0123456789");

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, options] = fetchMock.mock.calls[0]!;
    expect(String(url)).toContain("/api/v1/analytics/pageview/");
    const body = JSON.parse(String(options?.body));
    expect(body).toMatchObject({ page_type: "point", slug: "tochal", navigation_id: "navigation-0123456789" });
    expect(body.visitor_id).toMatch(/^[A-Za-z0-9_-]{16,128}$/);
    expect(window.localStorage.getItem("hawatch.analytics.visitor")).toBe(body.visitor_id);
  });

  it("reuses the first-party visitor token across navigations", () => {
    const fetchMock = vi.fn<typeof fetch>(() => Promise.resolve(new Response(null, { status: 201 })));
    vi.stubGlobal("fetch", fetchMock);

    trackPageView("point", "tochal", "navigation-0123456789");
    trackPageView("route", "tochal-darband", "navigation-9876543210");

    const first = JSON.parse(String(fetchMock.mock.calls[0]![1]?.body));
    const second = JSON.parse(String(fetchMock.mock.calls[1]![1]?.body));
    expect(second.visitor_id).toBe(first.visitor_id);
    expect(second.page_type).toBe("route");
  });

  it("swallows network failures so tracking cannot break navigation", () => {
    vi.stubGlobal("fetch", vi.fn<typeof fetch>(() => Promise.reject(new Error("offline"))));
    expect(() => trackPageView("point", "tochal")).not.toThrow();
  });
});
