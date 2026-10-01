import { beforeEach, afterEach, describe, it, expect, vi } from "vitest";
import {
  clearDayCache,
  dayCacheKey,
  fetchDayCache,
  readDayCache,
  expireDayCache,
} from "../src/lib/dayCache";
import fixture from "./fixtures/point-day.json";
import type { PointDayBundle, ApiMeta, ForecastAccess } from "../src/types";
const payload = () =>
  JSON.parse(JSON.stringify(fixture)) as PointDayBundle & {
    meta: ApiMeta;
    forecast_access: ForecastAccess;
  };
beforeEach(() => clearDayCache());
afterEach(() => vi.useRealTimers());
describe("private complete-day cache", () => {
  it("never keeps a paid day beyond its actual membership expiry", async () => {
    vi.useFakeTimers();
    const data = payload();
    data.cache_expires_at = new Date(
      Date.parse(data.meta.current_local_time) + 1000,
    ).toISOString();
    const key = dayCacheKey("point", "tochal");
    await fetchDayCache(key, async () => data, "point", "tochal");
    vi.advanceTimersByTime(1001);
    expect(readDayCache(key)).toBeNull();
  });

  it("shares concurrent requests and aliases the server-resolved date", async () => {
    const data = payload();
    const key = dayCacheKey("point", "tochal");
    const load = vi.fn(async () => data);
    const [a, b] = await Promise.all([
      fetchDayCache(key, load, "point", "tochal"),
      fetchDayCache(key, load, "point", "tochal"),
    ]);
    expect(load).toHaveBeenCalledTimes(1);
    expect(a).toBe(b);
    expect(
      readDayCache(dayCacheKey("point", "tochal", data.meta.selected_date)),
    ).toBe(data);
  });
  it("clears all date aliases when explicitly refreshing a day", async () => {
    const data = payload();
    const key = dayCacheKey("point", "tochal");
    await fetchDayCache(key, async () => data, "point", "tochal");
    expireDayCache(key);
    expect(
      readDayCache(dayCacheKey("point", "tochal", data.meta.selected_date)),
    ).toBeNull();
  });
  it("discards a late cached response from an earlier login state", async () => {
    const key = dayCacheKey("point", "tochal");
    let finish!: (data: PointDayBundle) => void;
    const old = fetchDayCache(
      key,
      () => new Promise<PointDayBundle>((resolve) => (finish = resolve)),
      "point",
      "tochal",
    );
    window.dispatchEvent(new Event("hawatch-auth-changed"));
    finish(payload());
    await old;
    expect(readDayCache(key)).toBeNull();
    expect(
      readDayCache(dayCacheKey("point", "tochal", fixture.meta.selected_date)),
    ).toBeNull();
  });
  it("expires cached days within five minutes", async () => {
    vi.useFakeTimers();
    const key = dayCacheKey("point", "tochal");
    await fetchDayCache(key, async () => payload(), "point", "tochal");
    vi.advanceTimersByTime(300001);
    expect(readDayCache(key)).toBeNull();
  });
  it("expires at the next Tehran hour to keep period flags current", async () => {
    vi.useFakeTimers();
    const data = payload();
    data.meta.current_local_time = "2026-10-01T08:59:58+03:30";
    data.forecast.meta = data.meta;
    const key = dayCacheKey("point", "tochal");
    await fetchDayCache(key, async () => data, "point", "tochal");
    vi.advanceTimersByTime(2001);
    expect(readDayCache(key)).toBeNull();
  });
  it("invalidates earlier days when the provider update time changes", async () => {
    const old = payload();
    const first = dayCacheKey("point", "tochal");
    await fetchDayCache(first, async () => old, "point", "tochal");
    const next = payload();
    next.meta.last_generated_time = "2026-10-02T08:00:00+03:30";
    next.meta.selected_date = "2026-10-02";
    next.forecast.meta = next.meta;
    await fetchDayCache(
      dayCacheKey("point", "tochal", "2026-10-02"),
      async () => next,
      "point",
      "tochal",
    );
    expect(readDayCache(first)).toBeNull();
  });
  it("invalidates earlier days when runtime account access changes", async () => {
    const key = dayCacheKey("point", "tochal");
    await fetchDayCache(key, async () => payload(), "point", "tochal");
    const data = payload();
    data.forecast_access.viewer = "member";
    await fetchDayCache(
      dayCacheKey("point", "other"),
      async () => data,
      "point",
      "other",
    );
    expect(readDayCache(key)).toBeNull();
  });
  it("does not cache an API rejection and allows a retry", async () => {
    const key = dayCacheKey("point", "tochal");
    await expect(
      fetchDayCache(
        key,
        () => Promise.reject(new Error("failed")),
        "point",
        "tochal",
      ),
    ).rejects.toThrow();
    expect(readDayCache(key)).toBeNull();
    await expect(
      fetchDayCache(key, async () => payload(), "point", "tochal"),
    ).resolves.toBeTruthy();
  });
});
